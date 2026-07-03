from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.core.config import APP_NAME, get_settings

settings = get_settings()

app = FastAPI(
    title=APP_NAME,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.include_router(health_router, prefix="/api/v1")
