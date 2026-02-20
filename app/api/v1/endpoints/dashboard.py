"""
Dashboard endpoint: KPI summary for the fleet.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.models.models import User
from app.repositories.repositories import JobRepository
from app.schemas.schemas import DashboardKPI

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardKPI)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = JobRepository(db)
    kpis = await repo.kpi_summary(current_user.fleet_id)
    return DashboardKPI(**kpis)
