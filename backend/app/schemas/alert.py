import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field, field_validator
from app.core.validator import validate_safe_url


class AlertRuleCreate(BaseModel):
    tenant_id: str = Field(..., example="uuid-string")
    name: str = Field(..., min_length=2, max_length=255, example="P95 Latency Spike")
    metric_type: str = Field(..., pattern="^(p95_latency|error_rate|req_count)$", example="p95_latency")
    threshold: float = Field(..., gt=0, example=500.0)  # 500 ms or 5.0 %
    window_minutes: Optional[int] = Field(5, ge=1, le=60, example=5)
    webhook_url: str = Field(..., example="https://webhook.site/sample")

    @field_validator("webhook_url")
    @classmethod
    def check_webhook_url(cls, v: str) -> str:
        # Webhooks must be public HTTPS/HTTP endpoints and never loopback or cloud metadata
        return validate_safe_url(v, allow_localhost=False)


class AlertRuleResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    metric_type: str
    threshold: float
    window_minutes: int
    webhook_url: str
    is_active: bool
    created_at: Optional[Union[datetime.datetime, str]] = None

    class Config:
        from_attributes = True


class AlertRuleListResponse(BaseModel):
    total: int
    rules: List[AlertRuleResponse]


class AlertHistoryResponse(BaseModel):
    id: str
    rule_id: str
    tenant_id: str
    metric_type: str
    triggered_value: float
    threshold: float
    status: str
    payload: Optional[str] = None
    triggered_at: Optional[Union[datetime.datetime, str]] = None

    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    event: str = "alert.triggered"
    rule_id: str
    tenant_id: str
    rule_name: str
    metric_type: str
    current_value: float
    threshold: float
    window_minutes: int
    timestamp: str
    severity: str = "critical"
