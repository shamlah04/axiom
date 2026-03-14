"""
app/main.py
────────────
Production-hardened FastAPI application.

Changes from Phase 4:
  • Security headers middleware (CSP, HSTS, X-Frame-Options, etc.)
  • Rate limiting via slowapi (10 req/s global, 5/min on auth endpoints)
  • CORS restricted to APP_BASE_URL in production; wildcard in dev only
  • /health endpoint extended with DB connectivity check
"""
import logging
import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.limiter import limiter
from app.api.v1.router import api_router
from app.api.v1.endpoints.billing import webhook_router
from app.core.startup import lifespan

log = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Axiom — Fleet Intelligence API",
    description="AI-driven decision intelligence for small and micro fleet operators.",
    version="5.0.0",
    docs_url="/docs" if settings.DEBUG else None,   # hide docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
# In production, restrict to your actual frontend origin.
# In dev (DEBUG=true or APP_BASE_URL=localhost), allow all.
_is_local = "localhost" in settings.APP_BASE_URL or "127.0.0.1" in settings.APP_BASE_URL

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if (_is_local or settings.DEBUG) else [settings.APP_BASE_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ── Security headers middleware ───────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """
    Adds OWASP-recommended security headers to every response.
    Stripe webhooks need raw body — we don't touch that here, just headers.
    """
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    # Standard security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

    # HSTS — only on HTTPS (Railway/production)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    # Content-Security-Policy — allow Stripe JS and our own origin
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://js.stripe.com; "
        "frame-src https://js.stripe.com; "
        "connect-src 'self' https://api.stripe.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:;"
    )

    # Server timing (useful for debugging, no security risk)
    response.headers["Server-Timing"] = f"total;dur={duration_ms:.1f}"

    # Never expose the server software
    response.headers["Server"] = "Axiom"

    return response

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(webhook_router)   # /webhooks/stripe — no prefix

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", include_in_schema=False)
@limiter.exempt
async def health(request: Request):
    """
    Railway / Docker health probe.
    Returns 200 when the app is up and the DB is reachable.
    Returns 503 if the DB connection fails.
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text

    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as exc:
        log.error(f"[Health] DB check failed: {exc}")

    payload = {
        "status": "ok" if db_ok else "degraded",
        "version": "5.0.0",
        "db": "ok" if db_ok else "unreachable",
    }
    return JSONResponse(
        content=payload,
        status_code=200 if db_ok else 503,
    )
