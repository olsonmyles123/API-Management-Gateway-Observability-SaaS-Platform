import pytest
from app.core.security import generate_api_key, hash_api_key, mask_api_key


def test_api_key_generation_and_hashing():
    raw_key, key_prefix, key_hash = generate_api_key()
    assert raw_key.startswith("ak_live_")
    assert key_prefix == raw_key[:12]
    assert len(key_hash) == 64  # SHA-256 is 64 hex characters
    assert hash_api_key(raw_key) == key_hash
    assert mask_api_key(key_prefix) == f"{key_prefix}...****"


@pytest.mark.asyncio
async def test_auth_rejections_on_gateway(async_client):
    # 1. Missing API Key header
    resp = await async_client.get("/users/123")
    assert resp.status_code == 401
    data = resp.json()
    assert "detail" in data
    assert "Missing X-API-Key" in data["detail"]

    # 2. Invalid API Key
    resp = await async_client.get("/users/123", headers={"X-API-Key": "ak_live_invalidkey12345"})
    assert resp.status_code == 401
    data = resp.json()
    assert "Invalid, inactive, or revoked" in data["detail"]


@pytest.mark.asyncio
async def test_key_creation_stores_only_sha256(async_client):
    # Create tenant
    t_resp = await async_client.post(
        "/admin/tenants",
        json={
            "name": "Security Test Tenant",
            "slug": "sec-test",
            "upstream_url": "https://httpbin.org",
            "plan_tier": "free",
        },
    )
    assert t_resp.status_code == 201
    tenant_id = t_resp.json()["id"]

    # Issue Key
    k_resp = await async_client.post(
        "/admin/keys",
        json={
            "tenant_id": tenant_id,
            "name": "Production Key",
        },
    )
    assert k_resp.status_code == 201
    key_data = k_resp.json()
    raw_key = key_data["raw_key"]
    assert raw_key.startswith("ak_live_")
    assert "warning" in key_data

    # Verify list keys does NOT leak raw key
    list_resp = await async_client.get(f"/admin/keys?tenant_id={tenant_id}")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 1
    key_info = list_data["keys"][0]
    assert "raw_key" not in key_info
    assert key_info["masked_key"].endswith("...****")
