import pytest
import httpx
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_wildcard_proxy_get_and_post_forwarding(async_client):
    # 1. Setup tenant & key
    t_resp = await async_client.post(
        "/admin/tenants",
        json={
            "name": "Proxy Tenant",
            "slug": "proxy-test",
            "upstream_url": "https://api.upstream.io",
            "rate_limit_rpm": 100,
        },
    )
    tenant_id = t_resp.json()["id"]

    k_resp = await async_client.post(
        "/admin/keys",
        json={"tenant_id": tenant_id, "name": "Proxy Key"},
    )
    raw_key = k_resp.json()["raw_key"]

    headers = {"X-API-Key": raw_key, "User-Agent": "CustomAgent/1.0"}

    # Mock HTTP client
    mock_get_resp = httpx.Response(
        status_code=200,
        json={"data": "hello from upstream", "received_query": "foo=bar"},
        headers={"Content-Type": "application/json", "X-Custom-Header": "UpstreamValue"},
        request=httpx.Request("GET", "https://api.upstream.io/v1/users?foo=bar"),
    )

    with patch("app.core.http_client._http_client") as mock_client:
        mock_client.request = AsyncMock(return_value=mock_get_resp)
        mock_client.is_closed = False

        # GET request with query params
        resp = await async_client.get("/v1/users?foo=bar", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == "hello from upstream"
        assert resp.headers.get("X-Custom-Header") == "UpstreamValue"
        assert "X-Gateway-Latency-Ms" in resp.headers
        assert resp.headers.get("X-RateLimit-Limit") == "100"

        # Verify proxy passed the correct URL to upstream client
        call_args = mock_client.request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "https://api.upstream.io/v1/users?foo=bar"


@pytest.mark.asyncio
async def test_wildcard_proxy_post_payload_forwarding(async_client):
    t_resp = await async_client.post(
        "/admin/tenants",
        json={
            "name": "Payload Tenant",
            "slug": "payload-test",
            "upstream_url": "https://api.upstream.io",
            "rate_limit_rpm": 100,
        },
    )
    tenant_id = t_resp.json()["id"]

    k_resp = await async_client.post(
        "/admin/keys",
        json={"tenant_id": tenant_id, "name": "Payload Key"},
    )
    raw_key = k_resp.json()["raw_key"]

    mock_post_resp = httpx.Response(
        status_code=201,
        json={"created": True, "id": "user_99"},
        headers={"Content-Type": "application/json"},
        request=httpx.Request("POST", "https://api.upstream.io/v1/items"),
    )

    with patch("app.core.http_client._http_client") as mock_client:
        mock_client.request = AsyncMock(return_value=mock_post_resp)
        mock_client.is_closed = False

        payload = {"name": "Widget X", "price": 49.99}
        resp = await async_client.post(
            "/v1/items",
            headers={"X-API-Key": raw_key},
            json=payload,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["created"] is True

        call_args = mock_client.request.call_args
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["url"] == "https://api.upstream.io/v1/items"
        assert b"Widget X" in call_args[1]["content"]


@pytest.mark.asyncio
async def test_wildcard_proxy_upstream_error_502(async_client):
    t_resp = await async_client.post(
        "/admin/tenants",
        json={
            "name": "Faulty Upstream Tenant",
            "slug": "faulty-test",
            "upstream_url": "https://unreachable.upstream.internal",
            "rate_limit_rpm": 100,
        },
    )
    tenant_id = t_resp.json()["id"]
    k_resp = await async_client.post("/admin/keys", json={"tenant_id": tenant_id, "name": "Key"})
    raw_key = k_resp.json()["raw_key"]

    with patch("app.core.http_client._http_client") as mock_client:
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.is_closed = False

        resp = await async_client.get("/some/endpoint", headers={"X-API-Key": raw_key})
        assert resp.status_code == 502
        data = resp.json()
        assert data["error"] == "Bad Gateway"
