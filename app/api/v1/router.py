"""
API v1 router — aggregates all endpoint sub-routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, fleets, trucks, drivers, jobs, dashboard, scenarios, ml_health

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(fleets.router)
api_router.include_router(trucks.router)
api_router.include_router(drivers.router)
api_router.include_router(jobs.router)
api_router.include_router(dashboard.router)
api_router.include_router(scenarios.router)
api_router.include_router(ml_health.router)
