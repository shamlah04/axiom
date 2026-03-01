"""
Repository layer — data access objects for all entities.
All repos accept an AsyncSession and return ORM models.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, Fleet, Truck, Driver, Job, RiskLevel, JobRecommendation


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _commit_refresh(self, obj):
        await self.db.commit()
        await self.db.refresh(obj)
        return obj


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserRepository(BaseRepository):
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str, full_name: str) -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name, role="viewer")
        self.db.add(user)
        return await self._commit_refresh(user)

    async def set_fleet(self, user: User, fleet_id: uuid.UUID, role: str = "owner") -> User:
        user.fleet_id = fleet_id
        user.role = role
        return await self._commit_refresh(user)

    async def get_fleet_owner(self, fleet_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .where(User.fleet_id == fleet_id, User.role == "owner")
            .limit(1)
        )
        return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Fleet
# ---------------------------------------------------------------------------

class FleetRepository(BaseRepository):
    async def create(self, name: str, country: str, subscription_tier, trial_ends_at=None) -> Fleet:
        fleet = Fleet(name=name, country=country, subscription_tier=subscription_tier, trial_ends_at=trial_ends_at)
        self.db.add(fleet)
        return await self._commit_refresh(fleet)

    async def get(self, fleet_id: uuid.UUID) -> Optional[Fleet]:
        result = await self.db.execute(select(Fleet).where(Fleet.id == fleet_id))
        return result.scalar_one_or_none()

    async def get_trial_expiring_in(self, days: int) -> list[Fleet]:
        """Find tier1 fleets whose trial ends within 'days' from now."""
        from datetime import timedelta
        now = datetime.now()
        threshold = now + timedelta(days=days)
        result = await self.db.execute(
            select(Fleet).where(
                Fleet.subscription_tier == "tier1",
                Fleet.trial_ends_at > now,
                Fleet.trial_ends_at <= threshold
            )
        )
        return list(result.scalars().all())

    async def get_expired_trials(self) -> list[Fleet]:
        """Find tier1 fleets where trial has already ended."""
        now = datetime.now()
        result = await self.db.execute(
            select(Fleet).where(
                Fleet.subscription_tier == "tier1",
                Fleet.trial_ends_at < now
            )
        )
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Truck
# ---------------------------------------------------------------------------

class TruckRepository(BaseRepository):
    async def create(self, fleet_id: uuid.UUID, **kwargs) -> Truck:
        truck = Truck(fleet_id=fleet_id, **kwargs)
        self.db.add(truck)
        return await self._commit_refresh(truck)

    async def get(self, truck_id: uuid.UUID, fleet_id: uuid.UUID) -> Optional[Truck]:
        result = await self.db.execute(
            select(Truck).where(Truck.id == truck_id, Truck.fleet_id == fleet_id)
        )
        return result.scalar_one_or_none()

    async def list_by_fleet(self, fleet_id: uuid.UUID) -> list[Truck]:
        result = await self.db.execute(
            select(Truck).where(Truck.fleet_id == fleet_id).order_by(Truck.created_at)
        )
        return list(result.scalars().all())

    async def update(self, truck: Truck, data: dict) -> Truck:
        for key, value in data.items():
            if value is not None:
                setattr(truck, key, value)
        return await self._commit_refresh(truck)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

class DriverRepository(BaseRepository):
    async def create(self, fleet_id: uuid.UUID, **kwargs) -> Driver:
        driver = Driver(fleet_id=fleet_id, **kwargs)
        self.db.add(driver)
        return await self._commit_refresh(driver)

    async def get(self, driver_id: uuid.UUID, fleet_id: uuid.UUID) -> Optional[Driver]:
        result = await self.db.execute(
            select(Driver).where(Driver.id == driver_id, Driver.fleet_id == fleet_id)
        )
        return result.scalar_one_or_none()

    async def list_by_fleet(self, fleet_id: uuid.UUID) -> list[Driver]:
        result = await self.db.execute(
            select(Driver).where(Driver.fleet_id == fleet_id).order_by(Driver.created_at)
        )
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class JobRepository(BaseRepository):
    async def create(self, **kwargs) -> Job:
        job = Job(**kwargs)
        self.db.add(job)
        return await self._commit_refresh(job)

    async def get(self, job_id: uuid.UUID, fleet_id: uuid.UUID) -> Optional[Job]:
        result = await self.db.execute(
            select(Job).where(Job.id == job_id, Job.fleet_id == fleet_id)
        )
        return result.scalar_one_or_none()

    async def list_by_fleet(
        self, fleet_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Job]:
        result = await self.db.execute(
            select(Job)
            .where(Job.fleet_id == fleet_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, job: Job, data: dict) -> Job:
        for key, value in data.items():
            setattr(job, key, value)
        return await self._commit_refresh(job)

    async def update_status(self, job_id: uuid.UUID, fleet_id: uuid.UUID, status: str) -> Optional[Job]:
        job = await self.get(job_id, fleet_id)
        if not job:
            return None
        job.status = status
        return await self._commit_refresh(job)

    async def update_actual(
        self, job_id: uuid.UUID, fleet_id: uuid.UUID, actual_revenue: float, actual_cost: float
    ) -> Optional[Job]:
        job = await self.get(job_id, fleet_id)
        if not job:
            return None
        job.actual_revenue = actual_revenue
        job.actual_cost = actual_cost
        job.status = "completed"
        return await self._commit_refresh(job)

    async def kpi_summary(self, fleet_id: uuid.UUID) -> dict:
        """Aggregate KPI metrics for the dashboard."""
        result = await self.db.execute(
            select(
                func.count(Job.id).label("total_jobs"),
                func.sum(
                    func.cast(Job.status == "accepted", type_=None)
                ).label("accepted_jobs"),
                func.sum(
                    func.cast(Job.status == "rejected", type_=None)
                ).label("rejected_jobs"),
                func.sum(
                    func.cast(Job.status == "completed", type_=None)
                ).label("completed_jobs"),
                func.avg(Job.margin_pct).label("avg_margin_pct"),
                func.sum(Job.offered_rate).label("total_revenue"),
                func.sum(Job.net_profit).label("total_profit"),
            ).where(Job.fleet_id == fleet_id)
        )
        row = result.one()
        return {
            "total_jobs": row.total_jobs or 0,
            "accepted_jobs": int(row.accepted_jobs or 0),
            "rejected_jobs": int(row.rejected_jobs or 0),
            "completed_jobs": int(row.completed_jobs or 0),
            "avg_margin_pct": round(float(row.avg_margin_pct), 2) if row.avg_margin_pct else None,
            "total_revenue": round(float(row.total_revenue), 2) if row.total_revenue else None,
            "total_profit": round(float(row.total_profit), 2) if row.total_profit else None,
        }
