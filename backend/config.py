from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, read from environment variables (and a local .env file).

    Unknown variables in .env (e.g. leftovers from removed features) are ignored.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Key the backend spends on demo traffic. Optional: without it BYOK still works
    # and the demo path answers 503 instead of crashing.
    backend_gemini_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_timeout_seconds: float = Field(default=60, gt=0)

    # Demo caps. The device cap is a fairness limit (device ids are client-generated and
    # forgeable); the per-IP and global daily caps are what actually bound abuse and spend.
    demo_request_limit: int = Field(default=10, ge=1)         # per device, for its lifetime
    demo_ip_daily_limit: int = Field(default=30, ge=1)       # per client IP, per UTC day
    demo_global_daily_limit: int = Field(default=300, ge=1)  # whole demo, per UTC day

    # Only enable behind a reverse proxy you control that appends the real client IP to
    # X-Forwarded-For (the last entry is trusted). Off by default: a directly exposed
    # server must not believe a header the client can set.
    trust_forwarded_for: bool = False

    database_url: str = "sqlite:///./askoverlay.db"
    log_level: str = "INFO"

    @field_validator("backend_gemini_key", mode="before")
    @classmethod
    def blank_key_is_none(cls, value):
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
