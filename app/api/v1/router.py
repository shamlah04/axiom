"""
API v1 router — aggregates all endpoint sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, fleets, trucks, drivers, jobs, dashboard, scenarios, ml_health, intelligence
from app.api.v1.endpoints.team import team_router, fleet_router as team_billing_router
from app.api.v1.endpoints.billing import router as billing_api_router

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(fleets.router)
api_router.include_router(trucks.router)
api_router.include_router(drivers.router)
api_router.include_router(jobs.router)
api_router.include_router(dashboard.router)
api_router.include_router(scenarios.router)
api_router.include_router(ml_health.router)
api_router.include_router(intelligence.router)

# Phase 3: Team + Billing (Direct)
api_router.include_router(team_router)
api_router.include_router(team_billing_router)

# Phase 4: Billing API (Checkout + Audit)
api_router.include_router(billing_api_router)
