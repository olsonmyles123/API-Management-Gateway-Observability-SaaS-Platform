import logging
from typing import Optional
from fastapi import APIRouter, Query, Depends
from app.core.clickhouse import get_telemetry_metrics
from app.core.security import get_current_active_user
from app.schemas.metrics import MetricsResponse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger("control.metrics")
router = APIRouter(
    prefix="/admin/metrics",
    tags=["Control Plane - Observability"],
)


@router.get(
    "",
    response_model=MetricsResponse,
    summary="Get High-Cardinality Performance Metrics",
    description="Queries ClickHouse OLAP engine to aggregate total requests, error rates, bandwidth, and latency percentiles (P50, P95, P99).",
)
async def get_metrics(
    tenant_id: Optional[str] = Query(None, description="Filter metrics by Tenant UUID"),
    time_window_seconds: int = Query(3600, ge=10, le=2592000, description="Time window in seconds (default: 1 hour)"),
    route: Optional[str] = Query(None, description="Filter metrics by specific API route"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Retrieve tenant IDs belonging to current user (strict isolation)
    user_tenant_stmt = select(Tenant.id).where(
        Tenant.user_id == current_user.id
    )
    t_res = await db.execute(user_tenant_stmt)
    user_tenant_ids = t_res.scalars().all()

    if not user_tenant_ids:
        return {
            "total_requests": 0,
            "error_count": 0,
            "error_rate_pct": 0.0,
            "status_breakdown": {"2xx": 0, "4xx": 0, "5xx": 0},
            "latency_percentiles_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0},
            "bandwidth_bytes": {"request_bytes": 0, "response_bytes": 0, "total_bytes": 0},
            "routes_breakdown": [],
            "time_window_seconds": time_window_seconds,
        }

    target_tenant_id = None
    if tenant_id:
        if tenant_id in user_tenant_ids:
            target_tenant_id = tenant_id
        else:
            return {
                "total_requests": 0,
                "error_count": 0,
                "error_rate_pct": 0.0,
                "status_breakdown": {"2xx": 0, "4xx": 0, "5xx": 0},
                "latency_percentiles_ms": {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0},
                "bandwidth_bytes": {"request_bytes": 0, "response_bytes": 0, "total_bytes": 0},
                "routes_breakdown": [],
                "time_window_seconds": time_window_seconds,
            }

    data = get_telemetry_metrics(
        tenant_id=target_tenant_id,
        time_window_seconds=time_window_seconds,
        route_filter=route,
        tenant_ids=user_tenant_ids if not target_tenant_id else None,
    )
    return data
