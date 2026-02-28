"""
Application configuration via pydantic-settings.
All values are read from environment variables (or .env file).
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    PROJECT_NAME: str = "Fleet Cognitive Intelligence Platform"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str  # e.g. postgresql+asyncpg://user:pass@localhost/db

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Email (Phase 4)
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str = "Axiom <noreply@axiom.fleet>"
    APP_BASE_URL: str = "http://localhost:3000"

    # Stripe (Phase 4)
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_TIER2: str | None = None
    STRIPE_PRICE_TIER3: str | None = None

    # Scheduler (Phase 5)
    SCHEDULER_ENABLED: bool = True
    TRIAL_WARNING_DAYS: int = 3

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v


settings = Settings()
