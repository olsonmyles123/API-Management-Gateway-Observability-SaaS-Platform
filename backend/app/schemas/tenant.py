import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field, field_validator
from app.core.validator import validate_safe_url


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, example="Acme Corp")
    slug: str = Field(..., min_length=2, max_length=100, example="acme-corp")
    upstream_url: str = Field(..., example="https://httpbin.org")
    plan_tier: Optional[str] = Field("free", example="free")  # free, pro, enterprise
    rate_limit_rpm: Optional[int] = Field(60, ge=1, le=100000, example=60)
    burst_limit: Optional[int] = Field(10, ge=1, le=1000, example=10)

    @field_validator("upstream_url")
    @classmethod
    def check_upstream_url(cls, v: str) -> str:
        return validate_safe_url(v, allow_localhost=True)


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    upstream_url: Optional[str] = None
    plan_tier: Optional[str] = None
    rate_limit_rpm: Optional[int] = None
    burst_limit: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("upstream_url")
    @classmethod
    def check_upstream_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_safe_url(v, allow_localhost=True)
        return v


class TenantResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: str
    slug: str
    upstream_url: str
    plan_tier: str
    rate_limit_rpm: int
    burst_limit: int
    is_active: bool
    created_at: Optional[Union[datetime.datetime, str]] = None
    updated_at: Optional[Union[datetime.datetime, str]] = None

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    total: int
    tenants: List[TenantResponse]
