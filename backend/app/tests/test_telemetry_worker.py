import pytest
import time
from app.core.clickhouse import insert_telemetry_batch, get_telemetry_metrics
from app.core.redis import push_telemetry_stream, get_redis_client
from app.config import settings


import uuid


@pytest.mark.asyncio
async def test_clickhouse_telemetry_percentile_calculations():
    tenant_id = f"test_tenant_olap_{uuid.uuid4().hex[:8]}"

    # Insert 10 synthetic telemetry records with varying latencies
    # latencies: 10, 20, 30, 40, 50, 60, 70, 80, 90, 500 ms (1 error 500)
    now = time.time()
    batch = []
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 500.0]
    for i, lat in enumerate(latencies):
        status = 500 if i == 9 else 200
        batch.append({
            "timestamp": now,
            "tenant_id": tenant_id,
            "key_id": "key_1",
            "method": "GET",
            "route": f"/api/item/{i}",
            "status_code": status,
            "latency_ms": lat,
            "client_ip": "127.0.0.1",
            "request_size_bytes": 100,
            "response_size_bytes": 1000,
            "user_agent": "pytest",
            "error_message": "Internal error" if status == 500 else "",
        })

    success = await insert_telemetry_batch(batch)
    assert success is True

    # Query metrics
    metrics = get_telemetry_metrics(tenant_id=tenant_id, time_window_seconds=300)
    assert metrics["total_requests"] == 10
    assert metrics["error_count"] == 1
    assert metrics["error_rate_pct"] == 10.0
    assert metrics["status_breakdown"]["2xx"] == 9
    assert metrics["status_breakdown"]["5xx"] == 1
    assert metrics["bandwidth_bytes"]["request_bytes"] == 1000
    assert metrics["bandwidth_bytes"]["response_bytes"] == 10000

    # Check percentiles
    percentiles = metrics["latency_percentiles_ms"]
    assert percentiles["p50"] > 0
    assert percentiles["p95"] >= 90.0
    assert percentiles["max"] == 500.0


@pytest.mark.asyncio
async def test_redis_stream_push():
    event = {
        "timestamp": time.time(),
        "tenant_id": "tenant_stream_test",
        "key_id": "key_stream_test",
        "method": "POST",
        "route": "/checkout",
        "status_code": 201,
        "latency_ms": 14.5,
        "client_ip": "10.0.0.1",
        "request_size_bytes": 512,
        "response_size_bytes": 1024,
        "user_agent": "Mozilla/5.0",
        "error_message": "",
    }
    msg_id = await push_telemetry_stream(event)
    assert msg_id is not None

    r = await get_redis_client()
    stream_len = await r.xlen(settings.REDIS_STREAM_KEY)
    assert stream_len >= 1
