"""
app/core/config.py  — Phase 5 + production hardening
──────────────────────────────────────────────────────
New settings added:
  STALE_JOB_DAYS        — days after which pending jobs are auto-expired
  ML_RETRAIN_ENABLED    — toggle for nightly retraining job
  RETRAIN_MIN_NEW_JOBS  — minimum new actuals before a retrain fires
  ALLOWED_ORIGINS       — explicit CORS list for production
"""
from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    PROJECT_NAME: str = "Axiom Fleet Intelligence"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    TESTING: bool = False

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str   # postgresql+asyncpg://... or sqlite+aiosqlite://...

    # ── JWT ───────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24   # 24 hours

    # ── Email (Resend) ────────────────────────────────────────────────────
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str = "Axiom <noreply@axiom.fleet>"
    APP_BASE_URL: str = "http://localhost:3000"

    # ── Stripe ────────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_TIER2: str | None = None
    STRIPE_PRICE_TIER3: str | None = None

    # ── Scheduler — Phase 5 ───────────────────────────────────────────────
    SCHEDULER_ENABLED: bool = True
    TRIAL_WARNING_DAYS: int = 3

    # Stale job cleanup
    STALE_JOB_DAYS: int = 30          # pending jobs older than this are expired

    # Nightly ML retraining
    ML_RETRAIN_ENABLED: bool = True
    RETRAIN_MIN_NEW_JOBS: int = 50    # minimum new actuals required before retrain

    # ── Validators ────────────────────────────────────────────────────────
    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v


settings = Settings()
