import logging
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import generate_api_key, mask_api_key, get_current_active_user
from app.core.redis import set_cached_key_metadata, invalidate_key_metadata
from app.models.tenant import Tenant
from app.models.api_key import ApiKey
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyInfo,
    ApiKeyListResponse,
)

from app.models.user import User

logger = logging.getLogger("control.keys")
router = APIRouter(
    prefix="/admin/keys",
    tags=["Control Plane - API Keys"],
)


@router.post(
    "",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue API Key",
    description="Generates a raw API key, stores only its SHA-256 digest in the database, and immediately caches it in Redis.",
)
async def create_api_key(
    payload: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify tenant exists, is active, and belongs to current_user
    stmt = select(Tenant).where(
        (Tenant.id == payload.tenant_id)
        & (Tenant.is_active == True)
        & (Tenant.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{payload.tenant_id}' not found or inactive.",
        )

    # Generate raw key, prefix, and SHA-256 hash
    raw_key, key_prefix, key_hash = generate_api_key(prefix="ak_live_")

    # Expiry calculation if requested
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=payload.expires_in_days
        )

    # 1. Store SHA-256 hash & raw full key in PostgreSQL
    api_key_obj = ApiKey(
        tenant_id=tenant.id,
        name=payload.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        full_key=raw_key,
        rate_limit_override_rpm=payload.rate_limit_override_rpm,
        is_active=True,
        expires_at=expires_at,
    )
    db.add(api_key_obj)
    await db.commit()
    await db.refresh(api_key_obj)

    # 2. Immediately load metadata into Redis Cache (Zero DB queries on live proxy requests)
    effective_rate_limit = (
        api_key_obj.rate_limit_override_rpm
        if api_key_obj.rate_limit_override_rpm
        else tenant.rate_limit_rpm
    )

    metadata = {
        "key_id": api_key_obj.id,
        "key_hash": key_hash,
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "upstream_url": tenant.upstream_url.rstrip("/"),
        "rate_limit_rpm": effective_rate_limit,
        "burst_limit": tenant.burst_limit,
        "is_active": True,
    }
    await set_cached_key_metadata(key_hash, metadata)

    logger.info(
        f"Issued API key '{api_key_obj.id}' for tenant '{tenant.slug}' (SHA-256: {key_hash[:12]}...)"
    )

    return ApiKeyCreatedResponse(
        id=api_key_obj.id,
        tenant_id=api_key_obj.tenant_id,
        name=api_key_obj.name,
        key_prefix=api_key_obj.key_prefix,
        raw_key=raw_key,
        rate_limit_override_rpm=api_key_obj.rate_limit_override_rpm,
        is_active=api_key_obj.is_active,
        created_at=api_key_obj.created_at.isoformat() if api_key_obj.created_at else None,
    )


@router.get(
    "",
    response_model=ApiKeyListResponse,
    summary="List API Keys",
    description="Retrieves API keys for a tenant with masked key values.",
)
async def list_api_keys(
    tenant_id: Optional[str] = Query(None, description="Filter by Tenant ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Fetch user's tenant IDs
    user_tenant_stmt = select(Tenant.id).where(
        Tenant.user_id == current_user.id
    )
    t_res = await db.execute(user_tenant_stmt)
    user_tenant_ids = t_res.scalars().all()

    if not user_tenant_ids:
        return {"total": 0, "keys": []}

    stmt = select(ApiKey).where(ApiKey.tenant_id.in_(user_tenant_ids)).order_by(ApiKey.created_at.desc())
    if tenant_id:
        if tenant_id in user_tenant_ids:
            stmt = stmt.where(ApiKey.tenant_id == tenant_id)
        else:
            return {"total": 0, "keys": []}

    result = await db.execute(stmt)
    keys = result.scalars().all()

    key_infos = [
        ApiKeyInfo(
            id=k.id,
            tenant_id=k.tenant_id,
            name=k.name,
            key_prefix=k.key_prefix,
            masked_key=mask_api_key(k.key_prefix),
            full_key=k.full_key,
            rate_limit_override_rpm=k.rate_limit_override_rpm,
            is_active=k.is_active,
            created_at=k.created_at.isoformat() if k.created_at else None,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        )
        for k in keys
    ]

    return {"total": len(key_infos), "keys": key_infos}


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API Key",
    description="Deletes or deactivates API key and actively invalidates the Redis cache to drop live access.",
)
async def revoke_api_key(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user_tenant_stmt = select(Tenant.id).where(
        Tenant.user_id == current_user.id
    )
    t_res = await db.execute(user_tenant_stmt)
    user_tenant_ids = t_res.scalars().all()

    stmt = select(ApiKey).where(
        (ApiKey.id == id) & (ApiKey.tenant_id.in_(user_tenant_ids))
    )
    result = await db.execute(stmt)
    api_key_obj = result.scalar_one_or_none()
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API Key '{id}' not found.",
        )

    key_hash = api_key_obj.key_hash

    # 1. Delete from PostgreSQL Database
    await db.delete(api_key_obj)
    await db.commit()

    # 2. Actively invalidate in Redis Cache (Instant revocation)
    await invalidate_key_metadata(key_hash)

    logger.info(f"Revoked API key '{id}' and evicted hash {key_hash[:12]} from Redis cache.")
    return None
