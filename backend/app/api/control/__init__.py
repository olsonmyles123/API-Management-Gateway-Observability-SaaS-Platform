from app.api.control.tenants import router as tenants_router
from app.api.control.keys import router as keys_router
from app.api.control.metrics import router as metrics_router
from app.api.control.alerts import router as alerts_router
from app.api.control.auth import router as auth_router

__all__ = ["tenants_router", "keys_router", "metrics_router", "alerts_router", "auth_router"]
