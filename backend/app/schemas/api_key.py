import datetime
from typing import Optional, List, Union
from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    tenant_id: str = Field(..., example="uuid-string")
    name: str = Field("Default Key", min_length=1, max_length=255, example="Backend Production Key")
    rate_limit_override_rpm: Optional[int] = Field(None, ge=1, le=100000, example=120)
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650, example=365)


class ApiKeyCreatedResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    key_prefix: str
    raw_key: str  # Plaintext key returned only once
    rate_limit_override_rpm: Optional[int] = None
    is_active: bool
    created_at: Optional[Union[datetime.datetime, str]] = None
    warning: str = "Please save this raw key securely now. It will NEVER be shown again."

    class Config:
        from_attributes = True


class ApiKeyInfo(BaseModel):
    id: str
    tenant_id: str
    name: str
    key_prefix: str
    masked_key: str
    rate_limit_override_rpm: Optional[int] = None
    is_active: bool
    created_at: Optional[Union[datetime.datetime, str]] = None
    last_used_at: Optional[Union[datetime.datetime, str]] = None

    class Config:
        from_attributes = True


class ApiKeyListResponse(BaseModel):
    total: int
    keys: List[ApiKeyInfo]
