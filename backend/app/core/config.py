from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_NAME = "Tally"


class Settings(BaseSettings):
    """Central 12-factor config. Every environment difference flows through here —
    no code should branch on "self-hosted vs hosted" beyond these documented flags.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "production"] = "dev"
    instance_mode: Literal["self_hosted", "hosted"] = "self_hosted"
    allow_signup: bool = False

    database_url: str = "postgresql+asyncpg://tally:tally@localhost:5432/tally"
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str = "dev-only-insecure-secret-change-me"

    # Separate Redis db index from sessions (db 0) so rate-limit counters and
    # session data are independently flushable/inspectable.
    rate_limit_storage_uri: str = "redis://localhost:6379/1"

    session_idle_days: int = 30
    session_absolute_days: int = 90
    invite_expiry_days: int = 7

    import_max_file_bytes: int = 5 * 1024 * 1024
    import_max_rows: int = 10_000
    import_session_ttl_seconds: int = 1800
    import_undo_window_hours: int = 24
    import_rate_limit: str = "20/hour"
    regex_match_timeout_seconds: float = 0.05
    fuzzy_match_threshold: float = 0.6

    @property
    def docs_enabled(self) -> bool:
        return self.env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
