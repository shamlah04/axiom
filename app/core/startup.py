import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.ml.model_registry import registry

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    loaded = registry.load_latest()
    if loaded:
        meta = registry.get_metadata()
        log.info(
            "✅ ML model loaded — version=%s  train_r2=%.4f  samples=%d",
            meta.version, meta.train_r2, meta.training_samples,
        )
    else:
        log.warning(
            "⚠️  No trained ML model found — using deterministic fallback engine. "
            "Run: python scripts/train_model.py"
        )

    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────
    log.info("Axiom shutting down.")
