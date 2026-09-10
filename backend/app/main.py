import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.database import init_db
from app.core.redis import get_redis_client, close_redis_client
from app.core.http_client import get_http_client, close_http_client
from app.core.clickhouse import get_clickhouse_client
from app.api.control import tenants_router, keys_router, metrics_router, alerts_router, auth_router
from app.api.gateway import gateway_router
from app.workers.telemetry_worker import telemetry_worker
from app.workers.alert_worker import alert_worker

# Configure Logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gateway.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    
    # 1. Initialize DB schema (PostgreSQL / SQLite)
    await init_db()

    # 2. Connect Redis and pre-warm pool
    await get_redis_client()

    # 3. Connect ClickHouse OLAP engine
    get_clickhouse_client()

    # 4. Initialize persistent TCP client pool
    await get_http_client()

    yield

    # --- SHUTDOWN ---
    logger.info("Gracefully shutting down services...")
    await close_http_client()
    await close_redis_client()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Production API Management & Observability SaaS",
    description=(
        "High-performance API Gateway (Data Plane) and Control Plane platform "
        "featuring sub-millisecond rate limits, SHA-256 cryptographic auth, "
        "Redis streams telemetry, and ClickHouse OLAP analytics."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# 1. Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)


# Health Check
@app.get("/health", tags=["System Health"], summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# 1. Mount Control Plane Administrative Routers
app.include_router(auth_router)
app.include_router(tenants_router)
app.include_router(keys_router)
app.include_router(metrics_router)
app.include_router(alerts_router)

# 2. Mount Data Plane Wildcard Proxy Router (Must be last so admin routes take priority)
app.include_router(gateway_router)
