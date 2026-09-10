import logging
import httpx
from typing import Optional
from app.config import settings

logger = logging.getLogger("gateway.http_client")

_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """
    Returns a shared, persistent httpx.AsyncClient connection pool.
    Reuses keep-alive TCP connections across all proxied client requests to eliminate handshake overhead.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        limits = httpx.Limits(
            max_keepalive_connections=settings.MAX_KEEPALIVE_CONNECTIONS,
            max_connections=settings.MAX_CONNECTIONS,
            keepalive_expiry=30.0,
        )
        timeout = httpx.Timeout(
            timeout=settings.PROXY_TIMEOUT_SECONDS,
            connect=5.0,
            read=settings.PROXY_TIMEOUT_SECONDS,
            write=10.0,
            pool=5.0,
        )
        _http_client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            follow_redirects=False,
            http2=True,
        )
        logger.info("Initialized persistent AsyncClient TCP connection pool for Gateway Data Plane")
    return _http_client


async def close_http_client():
    """Closes the shared HTTP client connection pool on server shutdown."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
        logger.info("Closed AsyncClient TCP connection pool")
