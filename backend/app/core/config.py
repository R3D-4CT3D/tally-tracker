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

    @property
    def docs_enabled(self) -> bool:
        return self.env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
