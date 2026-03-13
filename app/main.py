from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.api.v1.endpoints.billing import webhook_router
from app.core.startup import lifespan

app = FastAPI(
    title="Axiom — Fleet Intelligence API",
    description="AI-driven decision intelligence for small and micro fleet operators.",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────
if settings.DEBUG or settings.TESTING:
    # Allow all local origins in dev for mobile/PWA testing on local WiFi
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # Wildcard (*) cannot be used with credentials: True
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production: restrict to your actual frontend domain
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.APP_BASE_URL],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
# ────────────────────────────────────────────────────────────────────────────

# API v1 Hub (prefixed)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Phase 4: Stripe Webhook (Root level, no prefix, unauthenticated)
app.include_router(webhook_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.0.0"}
