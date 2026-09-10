import pytest
import time
import httpx
from unittest.mock import AsyncMock, patch
from app.workers.alert_worker import alert_worker
from app.core.clickhouse import insert_telemetry_batch


@pytest.mark.asyncio
async def test_alert_rule_creation_and_threshold_evaluation(async_client):
    # 1. Create Tenant
    t_resp = await async_client.post(
        "/admin/tenants",
        json={
            "name": "Alerting Tenant",
            "slug": "alert-tenant",
            "upstream_url": "https://api.target.com",
        },
    )
    tenant_id = t_resp.json()["id"]

    # 2. Create Alert Rule (P95 latency > 200ms)
    rule_resp = await async_client.post(
        "/admin/alerts",
        json={
            "tenant_id": tenant_id,
            "name": "High P95 Latency Alert",
            "metric_type": "p95_latency",
            "threshold": 200.0,
            "window_minutes": 5,
            "webhook_url": "https://webhook.site/test-alert",
        },
    )
    assert rule_resp.status_code == 201
    rule_id = rule_resp.json()["id"]

    # 3. Simulate high latency logs in ClickHouse
    now = time.time()
    batch = [
        {
            "timestamp": now,
            "tenant_id": tenant_id,
            "key_id": "k1",
            "method": "GET",
            "route": "/slow-query",
            "status_code": 200,
            "latency_ms": 350.0,  # Exceeds 200ms threshold
            "client_ip": "127.0.0.1",
            "request_size_bytes": 100,
            "response_size_bytes": 500,
            "user_agent": "pytest",
            "error_message": "",
        }
    ]
    await insert_telemetry_batch(batch)

    # 4. Trigger alert worker evaluation with mocked webhook
    mock_webhook_resp = httpx.Response(status_code=200, request=httpx.Request("POST", "https://webhook.site/test-alert"))

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_webhook_resp

        await alert_worker.evaluate_all_rules()

        # Verify webhook was dispatched
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://webhook.site/test-alert"
        payload = call_args[1]["json"]
        assert payload["event"] == "alert.triggered"
        assert payload["metric_type"] == "p95_latency"
        assert payload["current_value"] >= 350.0

    # 5. Verify Alert History recorded
    history_resp = await async_client.get(f"/admin/alerts/history?tenant_id={tenant_id}")
    assert history_resp.status_code == 200
    history_list = history_resp.json()
    assert len(history_list) >= 1
    assert history_list[0]["rule_id"] == rule_id
    assert history_list[0]["status"] == "sent"
