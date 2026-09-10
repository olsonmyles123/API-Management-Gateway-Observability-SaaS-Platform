import pytest
import time
from app.core.rate_limiter import rate_limiter
import httpx
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_lua_sliding_window_rate_limiter_logic():
    identifier = "tenant_test:key_test"
    max_requests = 3
    window_seconds = 2

    # Request 1
    allowed, remaining, retry_after = await rate_limiter.check_rate_limit(
        identifier, max_requests=max_requests, window_seconds=window_seconds
    )
    assert allowed is True
    assert remaining == 2

    # Request 2
    allowed, remaining, retry_after = await rate_limiter.check_rate_limit(
        identifier, max_requests=max_requests, window_seconds=window_seconds
    )
    assert allowed is True
    assert remaining == 1

    # Request 3
    allowed, remaining, retry_after = await rate_limiter.check_rate_limit(
        identifier, max_requests=max_requests, window_seconds=window_seconds
    )
    assert allowed is True
    assert remaining == 0

    # Request 4 (Exceeds limit)
    allowed, remaining, retry_after = await rate_limiter.check_rate_limit(
        identifier, max_requests=max_requests, window_seconds=window_seconds
    )
    assert allowed is False
    assert remaining == 0
    assert retry_after >= 1


@pytest.mark.asyncio
async def test_gateway_enforces_http_429_on_rate_limit(async_client):
    # Create tenant with tight rate limit (2 req/min)
    t_resp = await async_client.post(
        "/admin/tenants",
        json={
            "name": "Throttled Tenant",
            "slug": "throttle-test",
            "upstream_url": "https://httpbin.org",
            "rate_limit_rpm": 2,
        },
    )
    tenant_id = t_resp.json()["id"]

    # Issue Key
    k_resp = await async_client.post(
        "/admin/keys",
        json={"tenant_id": tenant_id, "name": "Key1"},
    )
    raw_key = k_resp.json()["raw_key"]

    mock_resp = httpx.Response(
        status_code=200,
        json={"message": "ok"},
        request=httpx.Request("GET", "https://httpbin.org/get"),
    )

    with patch("app.core.http_client._http_client") as mock_client:
        mock_client.request = AsyncMock(return_value=mock_resp)
        mock_client.is_closed = False

        headers = {"X-API-Key": raw_key}

        # 1st request -> 200
        r1 = await async_client.get("/get", headers=headers)
        assert r1.status_code == 200
        assert r1.headers.get("X-RateLimit-Limit") == "2"
        assert r1.headers.get("X-RateLimit-Remaining") == "1"

        # 2nd request -> 200
        r2 = await async_client.get("/get", headers=headers)
        assert r2.status_code == 200
        assert r2.headers.get("X-RateLimit-Remaining") == "0"

        # 3rd request -> 429 Too Many Requests
        r3 = await async_client.get("/get", headers=headers)
        assert r3.status_code == 429
        assert r3.headers.get("X-RateLimit-Remaining") == "0"
        assert "Retry-After" in r3.headers
        data = r3.json()
        assert data["error"] == "Too Many Requests"
        assert "retry_after_seconds" in data
