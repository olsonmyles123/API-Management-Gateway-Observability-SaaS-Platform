import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, description="User Email")
    password: str = Field(..., min_length=8, max_length=128, description="Password (8-128 characters)")
    full_name: Optional[str] = Field(None, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", clean):
            raise ValueError("Please provide a valid email address.")
        return clean


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[str] = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
