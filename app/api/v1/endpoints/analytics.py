"""
app/api/v1/endpoints/analytics.py

Dashboard KPIs + three analytics endpoints:
  GET /dashboard                  — summary KPIs (existing)
  GET /dashboard/trends           — monthly profit trends
  GET /dashboard/routes           — most profitable routes
  GET /dashboard/fuel-volatility  — fuel price vs margin correlation

POST /scenarios/simulate          — what-if simulation (existing)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.models.models import User
from app.repositories.repositories import JobRepository
from app.repositories.analytics import AnalyticsRepository
from app.schemas.schemas import (
    DashboardSummary,
    ScenarioInput,
    ScenarioResult,
    MonthlyTrend,
    TopRoute,
    FuelVolatilityMonth,
)
from app.services.scenario_simulator import scenario_simulator

router = APIRouter(tags=["Dashboard & Analytics"])


# ------------------------------------------------------------------
# Existing: summary KPIs
# ------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """Fleet-level KPI summary."""
    repo = JobRepository(db)
    data = await repo.dashboard_summary(current_user.fleet_id)
    return DashboardSummary(**data)


# ------------------------------------------------------------------
# New: monthly profit trends
# ------------------------------------------------------------------

@router.get("/dashboard/trends", response_model=list[MonthlyTrend])
async def get_monthly_trends(
    months: int = Query(default=6, ge=1, le=24, description="How many months back to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Monthly profit trends for the last N months.
    Use this to chart revenue, cost, and margin over time.
    """
    repo = AnalyticsRepository(db)
    rows = await repo.monthly_trends(current_user.fleet_id, months=months)
    return [MonthlyTrend(**r) for r in rows]


# ------------------------------------------------------------------
# New: most profitable routes
# ------------------------------------------------------------------

@router.get("/dashboard/routes", response_model=list[TopRoute])
async def get_top_routes(
    limit: int = Query(default=10, ge=1, le=50, description="Max routes to return"),
    min_jobs: int = Query(default=2, ge=1, description="Minimum jobs on route to be included"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Most profitable routes ranked by average margin %.
    Only includes routes with at least `min_jobs` completed/accepted jobs
    to avoid single-run outliers distorting the ranking.
    """
    repo = AnalyticsRepository(db)
    rows = await repo.top_routes(current_user.fleet_id, limit=limit, min_jobs=min_jobs)
    return [TopRoute(**r) for r in rows]


# ------------------------------------------------------------------
# New: fuel volatility impact
# ------------------------------------------------------------------

@router.get("/dashboard/fuel-volatility", response_model=list[FuelVolatilityMonth])
async def get_fuel_volatility(
    months: int = Query(default=6, ge=1, le=24, description="How many months back to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Monthly fuel price trends vs margin.
    Shows how fuel price volatility correlates with margin erosion.
    Use this to decide whether to hedge fuel costs or adjust minimum rates.
    """
    repo = AnalyticsRepository(db)
    rows = await repo.fuel_volatility(current_user.fleet_id, months=months)
    return [FuelVolatilityMonth(**r) for r in rows]


# ------------------------------------------------------------------
# Existing: scenario simulator
# ------------------------------------------------------------------

@router.post("/scenarios/simulate", response_model=ScenarioResult)
async def simulate_scenario(
    payload: ScenarioInput,
    current_user: User = Depends(get_current_fleet_user),
):
    """What-if simulation. Pure computation, no DB write."""
    return scenario_simulator.simulate(payload)
