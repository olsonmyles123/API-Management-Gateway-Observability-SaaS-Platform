import pytest
import httpx
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_tenant_crud_control_plane(async_client):
    # 1. Create Tenant
    resp = await async_client.post(
        "/admin/tenants",
        json={
            "name": "Acme Global",
            "slug": "acme-global",
            "upstream_url": "https://api.acme.com",
            "plan_tier": "pro",
        },
    )
    assert resp.status_code == 201
    tenant = resp.json()
    assert tenant["slug"] == "acme-global"
    assert tenant["rate_limit_rpm"] == 1000
    tenant_id = tenant["id"]

    # 2. Get Tenant
    get_resp = await async_client.get(f"/admin/tenants/{tenant_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Acme Global"

    # 3. Update Tenant
    put_resp = await async_client.put(
        f"/admin/tenants/{tenant_id}",
        json={"rate_limit_rpm": 2500, "upstream_url": "https://newapi.acme.com"},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["rate_limit_rpm"] == 2500
    assert put_resp.json()["upstream_url"] == "https://newapi.acme.com"

    # 4. List Tenants
    list_resp = await async_client.get("/admin/tenants")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_key_revocation_and_instant_cache_invalidation(async_client):
    # 1. Create Tenant and Key
    t_resp = await async_client.post(
        "/admin/tenants",
        json={
            "name": "Revoke Test Corp",
            "slug": "revoke-corp",
            "upstream_url": "https://api.upstream.org",
        },
    )
    tenant_id = t_resp.json()["id"]

    k_resp = await async_client.post(
        "/admin/keys",
        json={"tenant_id": tenant_id, "name": "Key to Revoke"},
    )
    key_id = k_resp.json()["id"]
    raw_key = k_resp.json()["raw_key"]

    mock_resp = httpx.Response(
        status_code=200,
        json={"status": "live"},
        request=httpx.Request("GET", "https://api.upstream.org/v1/data"),
    )

    with patch("app.core.http_client._http_client") as mock_client:
        mock_client.request = AsyncMock(return_value=mock_resp)
        mock_client.is_closed = False

        # Key works initially on proxied path /v1/data
        r1 = await async_client.get("/v1/data", headers={"X-API-Key": raw_key})
        assert r1.status_code == 200

        # 2. Revoke Key via Control Plane
        del_resp = await async_client.delete(f"/admin/keys/{key_id}")
        assert del_resp.status_code == 204

        # 3. Key must immediately fail on Gateway with 401 (Cache invalidated)
        r2 = await async_client.get("/v1/data", headers={"X-API-Key": raw_key})
        assert r2.status_code == 401
        assert "Invalid, inactive, or revoked" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_metrics_control_plane_endpoint(async_client):
    metrics_resp = await async_client.get("/admin/metrics?time_window_seconds=3600")
    assert metrics_resp.status_code == 200
    data = metrics_resp.json()
    assert "total_requests" in data
    assert "error_rate_pct" in data
    assert "latency_percentiles_ms" in data
    assert "p50" in data["latency_percentiles_ms"]
    assert "p95" in data["latency_percentiles_ms"]
    assert "p99" in data["latency_percentiles_ms"]
    assert "bandwidth_bytes" in data


@pytest.mark.asyncio
async def test_unauthenticated_admin_access_rejected(async_client):
    """Verifies that requests without authentication are rejected with 401."""
    from app.main import app
    from app.core.security import get_current_active_user

    # Remove the test override to test actual unauthenticated access
    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]

    try:
        r1 = await async_client.get("/admin/tenants")
        assert r1.status_code == 401
        assert "Authentication credentials were not provided" in r1.json()["detail"]

        r2 = await async_client.get("/admin/keys")
        assert r2.status_code == 401

        r3 = await async_client.get("/admin/metrics")
        assert r3.status_code == 401

        r4 = await async_client.get("/admin/alerts")
        assert r4.status_code == 401
    finally:
        # Restore mock admin user for subsequent tests
        from app.models.user import User
        mock_admin = User(
            id="test-admin-uuid-1234",
            email="admin@enterprise.local",
            hashed_password="hashed_pw_test",
            full_name="Admin Test",
            role="admin",
            is_active=True,
        )
        app.dependency_overrides[get_current_active_user] = lambda: mock_admin


@pytest.mark.asyncio
async def test_ssrf_upstream_and_webhook_validation(async_client):
    """Verifies that SSRF target URLs (metadata, blocked ports) are rejected."""
    # 1. Cloud metadata IP must be rejected
    r1 = await async_client.post(
        "/admin/tenants",
        json={
            "name": "SSRF Attack",
            "slug": "ssrf-metadata",
            "upstream_url": "http://169.254.169.254/latest/meta-data/",
        },
    )
    assert r1.status_code == 422

    # 2. Blocked internal Redis port must be rejected
    r2 = await async_client.post(
        "/admin/tenants",
        json={
            "name": "SSRF Attack Port",
            "slug": "ssrf-port",
            "upstream_url": "http://example.com:6379",
        },
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_clickhouse_sql_injection_defense(async_client):
    """Verifies that SQL injection attempts in route_filter are sanitized without error."""
    resp = await async_client.get("/admin/metrics?route='%20OR%201=1%20--")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data


@pytest.mark.asyncio
async def test_security_headers_present(async_client):
    """Verifies that required HTTP security headers are injected on responses."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
