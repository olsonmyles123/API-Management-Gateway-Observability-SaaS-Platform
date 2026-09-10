import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token, get_current_active_user
from app.core.rate_limiter import rate_limiter
from app.config import settings
from app.models.user import User
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    AuthTokenResponse,
)

logger = logging.getLogger("control.auth")
router = APIRouter(prefix="/admin/auth", tags=["Control Plane - Authentication"])


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Admin User",
    description="Registers a new administrator user with bcrypt password hashing and issues a signed JWT token.",
)
async def register(
    payload: UserRegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Brute-force rate limiting: 10 attempts per minute per IP
    client_ip = request.client.host if request.client else "unknown"
    allowed, remaining, retry_after = await rate_limiter.check_rate_limit(
        identifier=f"auth_rate:{client_ip}",
        max_requests=10,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Please wait {retry_after} seconds before retrying.",
        )

    # Check if user with email already exists
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    existing_user = res.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{payload.email}' already exists.",
        )

    # Hash password securely with bcrypt
    hashed = hash_password(payload.password)

    user = User(
        email=payload.email,
        hashed_password=hashed,
        full_name=payload.full_name,
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Issue JWT Token
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    # Set secure HttpOnly cookie for XSS protection
    is_secure = (settings.ENVIRONMENT == "production")
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=86400,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict(),
    }


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="User Login",
    description="Authenticates credentials and returns a secure JWT access token.",
)
async def login(
    payload: UserLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Brute-force rate limiting: 10 attempts per minute per IP
    client_ip = request.client.host if request.client else "unknown"
    allowed, remaining, retry_after = await rate_limiter.check_rate_limit(
        identifier=f"auth_rate:{client_ip}",
        max_requests=10,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please wait {retry_after} seconds before retrying.",
        )

    stmt = select(User).where(User.email == payload.email, User.is_active == True)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Issue JWT
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    # Set secure HttpOnly cookie (protects from malicious script reading)
    is_secure = (settings.ENVIRONMENT == "production")
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=86400,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict(),
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Authenticated User",
    description="Validates current session token and returns user details.",
)
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Check Bearer Header or HttpOnly Cookie
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        )

    user_id = payload["sub"]
    stmt = select(User).where(User.id == user_id, User.is_active == True)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or disabled.",
        )

    return user.to_dict()


@router.post(
    "/logout",
    summary="User Logout",
    description="Clears authentication session cookies.",
)
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}
