from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()


async def cache_login_email(request: Request) -> None:
    """Route-level dependency, resolved by FastAPI before the (slowapi-wrapped)
    endpoint function is invoked. slowapi's key_func must be synchronous — it
    does not await a coroutine passed to it — so the email can't be read
    directly inside the key_func itself. Stashing it on request.state here
    lets the sync key_func below read it later in the same request.
    """
    try:
        body = await request.json()
        request.state.login_email = str(body.get("email", "")).strip().lower()
    except Exception:
        request.state.login_email = ""


def login_rate_limit_key(request: Request) -> str:
    email = getattr(request.state, "login_email", "")
    return f"{get_remote_address(request)}:{email}"


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.rate_limit_storage_uri,
)
