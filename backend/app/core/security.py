import hashlib
import secrets
import datetime
from typing import Tuple, Optional, Dict, Any
import jwt
import bcrypt
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.database import get_db
from app.models.user import User

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    try:
        plain_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[datetime.timedelta] = None) -> str:
    """
    Creates a cryptographically signed JWT token.
    Claims include subject (user_id), email, role, and expiration timestamp.
    """
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
    })
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and cryptographically validates a JWT token.
    Returns payload dictionary or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.PyJWTError:
        return None


async def get_current_active_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates JWT token from Bearer header or HttpOnly cookie.
    Ensures user exists and is active.
    Raises 401 Unauthorized if missing, expired, or inactive.
    """
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Bearer token or session required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    stmt = select(User).where(User.id == user_id, User.is_active == True)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account does not exist or has been disabled.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def generate_api_key(prefix: str = "ak_live_") -> Tuple[str, str, str]:
    """
    Generates a cryptographically secure random API key.
    
    Returns:
        (raw_key, key_prefix, key_hash)
        - raw_key: Returned once to the client upon creation.
        - key_prefix: First 8 characters (e.g., 'ak_live_') for identification/masking.
        - key_hash: SHA-256 hex digest stored in the database.
    """
    random_part = secrets.token_urlsafe(32)
    raw_key = f"{prefix}{random_part}"
    key_prefix = raw_key[:12]
    key_hash = hash_api_key(raw_key)
    return raw_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    """
    Calculates the SHA-256 hex digest of an API key.
    Raw keys are never stored in PostgreSQL or log files.
    """
    if not raw_key:
        return ""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


def mask_api_key(prefix: str) -> str:
    """
    Formats an API key for safe administrative display (e.g. 'ak_live_ab12...****').
    """
    if not prefix:
        return "ak_****"
    return f"{prefix}...****"

