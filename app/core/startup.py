import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.ml.model_registry import registry

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    log.info("🚀 Starting application lifespan...")
    
    # 1. ML Loading
    log.info("📦 Loading ML model...")
    loaded = registry.load_latest()
    if loaded:
        meta = registry.get_metadata()
        log.info(
            "✅ ML model loaded — version=%s  train_r2=%.4f  samples=%d",
            meta.version, meta.train_r2, meta.training_samples,
        )
    else:
        log.warning(
            "⚠️  No trained ML model found — using deterministic fallback engine."
        )

    # 2. Scheduler
    log.info("⏰ Setting up scheduler...")
    from app.services.scheduler import setup_scheduler, scheduler
    setup_scheduler()
    log.info("⏰ Scheduler setup complete.")
    
    if settings.SCHEDULER_ENABLED and not scheduler.running:
        log.info("⏰ Starting scheduler...")
        scheduler.start()
        log.info("🚀 APScheduler started.")

    log.info("✅ Startup complete — ready to serve.")
    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────
    if scheduler.running:
        scheduler.shutdown()
        log.info("🛑 APScheduler shut down.")
    log.info("Axiom shutting down.")
