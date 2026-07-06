from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.accounts import router as accounts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.balance_snapshots import router as balance_snapshots_router
from app.api.v1.bills import router as bills_router
from app.api.v1.board import router as board_router
from app.api.v1.categories import router as categories_router
from app.api.v1.debts import router as debts_router
from app.api.v1.goals import router as goals_router
from app.api.v1.health import router as health_router
from app.api.v1.household import router as household_router
from app.api.v1.import_profiles import router as import_profiles_router
from app.api.v1.imports import router as imports_router
from app.api.v1.invites import router as invites_router
from app.api.v1.monthly_close import router as monthly_close_router
from app.api.v1.rules import router as rules_router
from app.api.v1.setup import router as setup_router
from app.api.v1.transactions import router as transactions_router
from app.core.config import APP_NAME, get_settings
from app.core.limiter import limiter

settings = get_settings()

app = FastAPI(
    title=APP_NAME,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

app.include_router(health_router, prefix="/api/v1")
app.include_router(setup_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(invites_router, prefix="/api/v1")
app.include_router(household_router, prefix="/api/v1")
app.include_router(accounts_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(import_profiles_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(debts_router, prefix="/api/v1")
app.include_router(bills_router, prefix="/api/v1")
app.include_router(goals_router, prefix="/api/v1")
app.include_router(balance_snapshots_router, prefix="/api/v1")
app.include_router(board_router, prefix="/api/v1")
app.include_router(monthly_close_router, prefix="/api/v1")
