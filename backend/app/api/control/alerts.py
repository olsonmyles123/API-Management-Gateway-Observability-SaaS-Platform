import logging
import httpx
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.tenant import Tenant
from app.models.alert import AlertRule, AlertHistory
from app.schemas.alert import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleListResponse,
    AlertHistoryResponse,
)

from app.models.user import User

logger = logging.getLogger("control.alerts")
router = APIRouter(
    prefix="/admin/alerts",
    tags=["Control Plane - Alerts"],
)


@router.post(
    "",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Alert Rule",
    description="Registers an automated threshold monitoring rule (e.g., P95 latency > 500ms or Error Rate > 5%).",
)
async def create_alert_rule(
    payload: AlertRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify tenant exists and belongs to current_user
    stmt = select(Tenant).where(
        (Tenant.id == payload.tenant_id)
        & (Tenant.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{payload.tenant_id}' not found.",
        )

    rule = AlertRule(
        tenant_id=payload.tenant_id,
        name=payload.name,
        metric_type=payload.metric_type,
        threshold=payload.threshold,
        window_minutes=payload.window_minutes or 5,
        webhook_url=str(payload.webhook_url),
        is_active=True,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get(
    "",
    response_model=AlertRuleListResponse,
    summary="List Alert Rules",
    description="Retrieves registered alert rules for the authenticated user.",
)
async def list_alert_rules(
    tenant_id: Optional[str] = Query(None, description="Filter by Tenant UUID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user_tenant_stmt = select(Tenant.id).where(
        Tenant.user_id == current_user.id
    )
    t_res = await db.execute(user_tenant_stmt)
    user_tenant_ids = t_res.scalars().all()

    if not user_tenant_ids:
        return {"total": 0, "rules": []}

    stmt = select(AlertRule).where(AlertRule.tenant_id.in_(user_tenant_ids)).order_by(AlertRule.created_at.desc())
    if tenant_id:
        if tenant_id in user_tenant_ids:
            stmt = stmt.where(AlertRule.tenant_id == tenant_id)
        else:
            return {"total": 0, "rules": []}

    result = await db.execute(stmt)
    rules = result.scalars().all()
    return {"total": len(rules), "rules": rules}


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Alert Rule",
    description="Removes an alert rule and stops automated threshold monitoring for it.",
)
async def delete_alert_rule(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user_tenant_stmt = select(Tenant.id).where(
        Tenant.user_id == current_user.id
    )
    t_res = await db.execute(user_tenant_stmt)
    user_tenant_ids = t_res.scalars().all()

    stmt = select(AlertRule).where(
        (AlertRule.id == id) & (AlertRule.tenant_id.in_(user_tenant_ids))
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert Rule '{id}' not found.",
        )

    await db.delete(rule)
    await db.commit()
    return None


@router.get(
    "/history",
    response_model=List[AlertHistoryResponse],
    summary="Get Triggered Alert History",
    description="Retrieves historical alerts dispatched to external webhooks.",
)
async def get_alert_history(
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user_tenant_stmt = select(Tenant.id).where(
        Tenant.user_id == current_user.id
    )
    t_res = await db.execute(user_tenant_stmt)
    user_tenant_ids = t_res.scalars().all()

    if not user_tenant_ids:
        return []

    stmt = (
        select(AlertHistory)
        .where(AlertHistory.tenant_id.in_(user_tenant_ids))
        .order_by(AlertHistory.triggered_at.desc())
        .limit(limit)
    )
    if tenant_id:
        if tenant_id in user_tenant_ids:
            stmt = stmt.where(AlertHistory.tenant_id == tenant_id)
        else:
            return []

    result = await db.execute(stmt)
    history = result.scalars().all()
    return history


@router.post(
    "/{id}/test",
    summary="Test Webhook Dispatcher",
    description="Dispatches a test payload to the configured webhook URL.",
)
async def test_alert_rule(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user_tenant_stmt = select(Tenant.id).where(
        Tenant.user_id == current_user.id
    )
    t_res = await db.execute(user_tenant_stmt)
    user_tenant_ids = t_res.scalars().all()

    stmt = select(AlertRule).where(
        (AlertRule.id == id) & (AlertRule.tenant_id.in_(user_tenant_ids))
    )
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert Rule '{id}' not found.",
        )

    test_payload = {
        "event": "alert.test",
        "rule_id": rule.id,
        "tenant_id": rule.tenant_id,
        "rule_name": rule.name,
        "metric_type": rule.metric_type,
        "test_value": rule.threshold + 10.0,
        "threshold": rule.threshold,
        "window_minutes": rule.window_minutes,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "message": "This is a test notification from the API Management Alert Engine.",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(rule.webhook_url, json=test_payload)
            status_str = f"Delivered (HTTP {resp.status_code})"
    except Exception as e:
        status_str = f"Failed: {str(e)}"

    return {
        "rule_id": rule.id,
        "webhook_url": rule.webhook_url,
        "dispatch_status": status_str,
        "payload": test_payload,
    }
