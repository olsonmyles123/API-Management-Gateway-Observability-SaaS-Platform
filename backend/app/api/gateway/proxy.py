import asyncio
import time
import logging
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import hash_api_key
from app.core.redis import (
    get_cached_key_metadata,
    set_cached_key_metadata,
    push_telemetry_stream,
)
from app.core.rate_limiter import rate_limiter
from app.core.http_client import get_http_client
from app.core.database import async_session_factory
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.config import settings

logger = logging.getLogger("gateway.proxy")
router = APIRouter(tags=["Data Plane Gateway"])

# Hop-by-hop headers that should not be forwarded
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


async def _resolve_key_metadata(api_key_raw: str) -> Optional[dict]:
    """
    Validates API key and resolves tenant & rate limit metadata.
    First checks Redis cache for sub-millisecond response.
    Falls back to PostgreSQL database on cache miss and backfills Redis.
    """
    key_hash = hash_api_key(api_key_raw)
    if not key_hash:
        return None

    # 1. Fast path: Redis In-Memory Cache
    cached = await get_cached_key_metadata(key_hash)
    if cached is not None:
        return cached

    # 2. Cache miss: PostgreSQL Database Lookup
    async with async_session_factory() as session:
        stmt = (
            select(ApiKey)
            .options(selectinload(ApiKey.tenant))
            .where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
        )
        result = await session.execute(stmt)
        api_key_obj = result.scalar_one_or_none()

        if not api_key_obj or not api_key_obj.tenant or not api_key_obj.tenant.is_active:
            return None

        tenant = api_key_obj.tenant
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

        # Backfill Redis cache
        await set_cached_key_metadata(key_hash, metadata)
        return metadata


MAX_BODY_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit to prevent Out-Of-Memory DoS


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    summary="Wildcard Reverse Proxy (Data Plane)",
    description="Intercepts, authenticates, rate-limits, and proxies all HTTP traffic to tenant upstream APIs.",
)
async def wildcard_proxy(request: Request, path: str):
    start_time = time.perf_counter()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    method = request.method

    # 0. Pass-through & path sanitization
    if path.startswith("admin") or path.startswith("/admin") or path.startswith("health") or path.startswith("docs") or path.startswith("openapi.json"):
        raise HTTPException(status_code=404, detail="Not Found")

    # Reject null bytes or directory traversal attempts
    if "\x00" in path or "/../" in f"/{path}/" or path.startswith("../") or path.endswith("/.."):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Bad Request", "detail": "Invalid path traversal characters in request."},
        )

    # Enforce request body size limits before reading full payload
    content_length_header = request.headers.get("content-length")
    if content_length_header:
        try:
            content_length = int(content_length_header)
            if content_length > MAX_BODY_SIZE_BYTES:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "error": "Payload Too Large",
                        "detail": f"Request body exceeds maximum allowed size of {MAX_BODY_SIZE_BYTES // (1024 * 1024)}MB.",
                    },
                )
        except ValueError:
            pass

    route = f"/{path}" if not path.startswith("/") else path
    query_params = str(request.url.query)

    # 1. Cryptographic Authentication
    api_key_header = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not api_key_header:
        # Check Authorization: Bearer <key> fallback
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            api_key_header = auth_header[7:].strip()

    if not api_key_header:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Unauthorized",
                "detail": "Missing X-API-Key header or Bearer token.",
            },
        )

    # Resolve Key Metadata from Redis Cache / PostgreSQL
    key_meta = await _resolve_key_metadata(api_key_header)
    if not key_meta or not key_meta.get("is_active"):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Unauthorized",
                "detail": "Invalid, inactive, or revoked API key.",
            },
        )

    tenant_id = key_meta["tenant_id"]
    key_id = key_meta["key_id"]
    rate_limit_rpm = key_meta.get("rate_limit_rpm", 60)
    upstream_base = key_meta["upstream_url"]

    # 2. Sliding-Window Rate Limiting (Atomic Redis Lua on ZSET)
    rate_limit_id = f"{tenant_id}:{key_meta['key_hash']}"
    allowed, remaining, retry_after = await rate_limiter.check_rate_limit(
        identifier=rate_limit_id,
        max_requests=rate_limit_rpm,
        window_seconds=60,
    )

    if not allowed:
        latency_ms = (time.perf_counter() - start_time) * 1000
        # Fire-and-forget telemetry event for rate-limited request
        telemetry_event = {
            "timestamp": time.time(),
            "tenant_id": tenant_id,
            "key_id": key_id,
            "method": method,
            "route": route,
            "status_code": 429,
            "latency_ms": round(latency_ms, 2),
            "client_ip": client_ip,
            "request_size_bytes": int(request.headers.get("content-length", 0) or 0),
            "response_size_bytes": 0,
            "user_agent": user_agent,
            "error_message": "Rate limit exceeded",
        }
        asyncio.create_task(push_telemetry_stream(telemetry_event))

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Too Many Requests",
                "detail": f"Rate limit of {rate_limit_rpm} req/min exceeded. Retry after {retry_after}s.",
                "retry_after_seconds": retry_after,
            },
            headers={
                "X-RateLimit-Limit": str(rate_limit_rpm),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(retry_after),
            },
        )

    # 3. Request Forwarding to Upstream Target
    upstream_target_url = f"{upstream_base}/{path.lstrip('/')}"
    if query_params:
        upstream_target_url = f"{upstream_target_url}?{query_params}"

    # Prepare forwarding headers, stripping internal or hop-by-hop headers
    forward_headers = {}
    for header_name, header_value in request.headers.items():
        lower_name = header_name.lower()
        if lower_name not in HOP_BY_HOP_HEADERS and not lower_name.startswith("x-gateway-"):
            forward_headers[header_name] = header_value

    # Safely attach proxy client headers
    forward_headers["X-Forwarded-For"] = client_ip
    forward_headers["X-Forwarded-Proto"] = request.url.scheme
    forward_headers["X-Real-IP"] = client_ip

    # Read and enforce body payload size
    body = await request.body()
    if len(body) > MAX_BODY_SIZE_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": "Payload Too Large",
                "detail": "Request body exceeds maximum allowed size.",
            },
        )

    req_size = len(body) if body else 0
    http_client = await get_http_client()

    try:
        upstream_response = await http_client.request(
            method=method,
            url=upstream_target_url,
            headers=forward_headers,
            content=body if body else None,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000
        res_body = upstream_response.content
        res_size = len(res_body) if res_body else 0
        status_code = upstream_response.status_code

        # 4. Fire-and-Forget Telemetry Pipeline (Async Redis Streams)
        telemetry_event = {
            "timestamp": time.time(),
            "tenant_id": tenant_id,
            "key_id": key_id,
            "method": method,
            "route": route,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 2),
            "client_ip": client_ip,
            "request_size_bytes": req_size,
            "response_size_bytes": res_size,
            "user_agent": user_agent,
            "error_message": "" if status_code < 400 else f"HTTP {status_code}",
        }
        asyncio.create_task(push_telemetry_stream(telemetry_event))

        # Filter response headers
        response_headers = {}
        for h_name, h_val in upstream_response.headers.items():
            if h_name.lower() not in HOP_BY_HOP_HEADERS:
                response_headers[h_name] = h_val

        # Inject Gateway metadata headers
        response_headers["X-RateLimit-Limit"] = str(rate_limit_rpm)
        response_headers["X-RateLimit-Remaining"] = str(remaining)
        response_headers["X-Gateway-Latency-Ms"] = f"{latency_ms:.2f}"

        return Response(
            content=res_body,
            status_code=status_code,
            headers=response_headers,
            media_type=upstream_response.headers.get("content-type"),
        )

    except Exception as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        error_msg = str(exc)
        logger.error(f"Gateway proxy error to upstream {upstream_target_url}: {error_msg}", exc_info=True)

        # Stream error telemetry (internal message logged to ClickHouse)
        telemetry_event = {
            "timestamp": time.time(),
            "tenant_id": tenant_id,
            "key_id": key_id,
            "method": method,
            "route": route,
            "status_code": 502,
            "latency_ms": round(latency_ms, 2),
            "client_ip": client_ip,
            "request_size_bytes": req_size,
            "response_size_bytes": 0,
            "user_agent": user_agent,
            "error_message": f"Bad Gateway: {error_msg}",
        }
        asyncio.create_task(push_telemetry_stream(telemetry_event))

        # Return sanitized, non-disclosing error response to client
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error": "Bad Gateway",
                "detail": "Failed to reach upstream target API. The service may be temporarily unavailable or unreachable.",
            },
            headers={
                "X-RateLimit-Limit": str(rate_limit_rpm),
                "X-RateLimit-Remaining": str(remaining),
                "X-Gateway-Latency-Ms": f"{latency_ms:.2f}",
            },
        )
