import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.tenant import Tenant
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
)

from app.models.user import User

logger = logging.getLogger("control.tenants")
router = APIRouter(
    prefix="/admin/tenants",
    tags=["Control Plane - Tenants"],
)


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Tenant",
    description="Registers a new tenant and maps their upstream target API URL.",
)
async def create_tenant(
    payload: TenantCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Check for existing slug
    stmt = select(Tenant).where(Tenant.slug == payload.slug)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with slug '{payload.slug}' already exists.",
        )

    # Set rate limits based on plan tier if not specified
    rate_limit = payload.rate_limit_rpm
    burst = payload.burst_limit
    if payload.plan_tier == "pro" and rate_limit == 60:
        rate_limit = 1000
        burst = 100
    elif payload.plan_tier == "enterprise" and rate_limit == 60:
        rate_limit = 10000
        burst = 500

    tenant = Tenant(
        user_id=current_user.id,
        name=payload.name,
        slug=payload.slug,
        upstream_url=str(payload.upstream_url).rstrip("/"),
        plan_tier=payload.plan_tier or "free",
        rate_limit_rpm=rate_limit,
        burst_limit=burst,
        is_active=True,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get(
    "",
    response_model=TenantListResponse,
    summary="List Tenants",
    description="Retrieves registered tenants for the authenticated user.",
)
async def list_tenants(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tenant).where(Tenant.user_id == current_user.id).order_by(Tenant.created_at.desc())
    result = await db.execute(stmt)
    tenants = result.scalars().all()

    return {
        "total": len(tenants),
        "tenants": tenants,
    }


@router.get(
    "/{id}",
    response_model=TenantResponse,
    summary="Get Tenant Details",
    description="Retrieves a single tenant by UUID or slug.",
)
async def get_tenant(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tenant).where(
        ((Tenant.id == id) | (Tenant.slug == id))
        & (Tenant.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{id}' not found.",
        )
    return tenant


@router.put(
    "/{id}",
    response_model=TenantResponse,
    summary="Update Tenant Configuration",
    description="Updates upstream URL, plan tier, or rate limits.",
)
async def update_tenant(
    id: str,
    payload: TenantUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tenant).where(
        (Tenant.id == id)
        & (Tenant.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{id}' not found.",
        )

    if payload.name is not None:
        tenant.name = payload.name
    if payload.upstream_url is not None:
        tenant.upstream_url = str(payload.upstream_url).rstrip("/")
    if payload.plan_tier is not None:
        tenant.plan_tier = payload.plan_tier
    if payload.rate_limit_rpm is not None:
        tenant.rate_limit_rpm = payload.rate_limit_rpm
    if payload.burst_limit is not None:
        tenant.burst_limit = payload.burst_limit
    if payload.is_active is not None:
        tenant.is_active = payload.is_active

    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Tenant",
    description="Deletes tenant and associated API keys and alert rules.",
)
async def delete_tenant(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tenant).where(
        (Tenant.id == id)
        & (Tenant.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{id}' not found.",
        )

    await db.delete(tenant)
    await db.commit()
    return None
