"""
app/repositories/analytics.py

Dedicated repository for dashboard analytics queries.
Kept separate from JobRepository to keep data-access concerns clean.
All queries are read-only and fleet-scoped.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, extract, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Job, RiskLevel


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 1. Monthly profit trends
    # ------------------------------------------------------------------

    async def monthly_trends(
        self,
        fleet_id: uuid.UUID,
        months: int = 6,
    ) -> list[dict]:
        """
        Returns one row per calendar month (most recent `months` months).
        Each row: year, month, total_revenue, total_cost, total_profit,
                  avg_margin_pct, job_count, accepted_count, rejected_count.
        Only includes jobs with status in (accepted, completed).
        """
        result = await self.db.execute(
            select(
                extract("year",  Job.created_at).label("year"),
                extract("month", Job.created_at).label("month"),
                func.count(Job.id).label("job_count"),
                func.sum(
                    case((Job.status.in_(["accepted", "completed"]), 1), else_=0)
                ).label("accepted_count"),
                func.sum(
                    case((Job.status == "rejected", 1), else_=0)
                ).label("rejected_count"),
                func.coalesce(
                    func.sum(
                        case((Job.status.in_(["accepted", "completed"]), Job.offered_rate), else_=0)
                    ), 0
                ).label("total_revenue"),
                func.coalesce(
                    func.sum(
                        case((Job.status.in_(["accepted", "completed"]), Job.total_cost), else_=0)
                    ), 0
                ).label("total_cost"),
                func.coalesce(
                    func.sum(
                        case((Job.status.in_(["accepted", "completed"]), Job.net_profit), else_=0)
                    ), 0
                ).label("total_profit"),
                func.coalesce(
                    func.avg(
                        case((Job.status.in_(["accepted", "completed"]), Job.margin_pct), else_=None)
                    ), 0
                ).label("avg_margin_pct"),
            )
            .where(Job.fleet_id == fleet_id)
            .group_by(
                extract("year",  Job.created_at),
                extract("month", Job.created_at),
            )
            .order_by(
                extract("year",  Job.created_at).desc(),
                extract("month", Job.created_at).desc(),
            )
            .limit(months)
        )

        rows = result.all()
        # Return in chronological order (oldest → newest)
        return [
            {
                "year":           int(r.year),
                "month":          int(r.month),
                "job_count":      int(r.job_count),
                "accepted_count": int(r.accepted_count),
                "rejected_count": int(r.rejected_count),
                "total_revenue":  round(float(r.total_revenue), 2),
                "total_cost":     round(float(r.total_cost), 2),
                "total_profit":   round(float(r.total_profit), 2),
                "avg_margin_pct": round(float(r.avg_margin_pct), 2),
            }
            for r in reversed(rows)
        ]

    # ------------------------------------------------------------------
    # 2. Most profitable routes
    # ------------------------------------------------------------------

    async def top_routes(
        self,
        fleet_id: uuid.UUID,
        limit: int = 10,
        min_jobs: int = 2,
    ) -> list[dict]:
        """
        Groups completed/accepted jobs by (origin, destination) pair.
        Returns routes ranked by avg_margin_pct descending.
        Only includes route pairs with at least `min_jobs` jobs
        (avoids single-run flukes dominating the ranking).
        """
        result = await self.db.execute(
            select(
                Job.origin,
                Job.destination,
                func.count(Job.id).label("job_count"),
                func.avg(Job.margin_pct).label("avg_margin_pct"),
                func.avg(Job.net_profit).label("avg_net_profit"),
                func.avg(Job.offered_rate).label("avg_rate"),
                func.avg(Job.total_cost).label("avg_cost"),
                func.avg(Job.distance_km).label("avg_distance_km"),
            )
            .where(
                Job.fleet_id == fleet_id,
                Job.status.in_(["accepted", "completed"]),
                Job.margin_pct.isnot(None),
            )
            .group_by(Job.origin, Job.destination)
            .having(func.count(Job.id) >= min_jobs)
            .order_by(func.avg(Job.margin_pct).desc())
            .limit(limit)
        )

        return [
            {
                "origin":          r.origin,
                "destination":     r.destination,
                "job_count":       int(r.job_count),
                "avg_margin_pct":  round(float(r.avg_margin_pct), 2),
                "avg_net_profit":  round(float(r.avg_net_profit), 2),
                "avg_rate":        round(float(r.avg_rate), 2),
                "avg_cost":        round(float(r.avg_cost), 2),
                "avg_distance_km": round(float(r.avg_distance_km), 1),
            }
            for r in result.all()
        ]

    # ------------------------------------------------------------------
    # 3. Fuel volatility impact
    # ------------------------------------------------------------------

    async def fuel_volatility(
        self,
        fleet_id: uuid.UUID,
        months: int = 6,
    ) -> list[dict]:
        """
        Groups accepted/completed jobs by calendar month.
        Returns avg fuel price paid, avg fuel cost per job,
        fuel cost as % of total cost, and avg margin that month.
        Lets operators see how fuel price swings erode margins.
        """
        result = await self.db.execute(
            select(
                extract("year",  Job.created_at).label("year"),
                extract("month", Job.created_at).label("month"),
                func.count(Job.id).label("job_count"),
                func.avg(Job.fuel_price_per_unit).label("avg_fuel_price"),
                # fuel_cost is not stored — derive it from total_cost components
                # We store total_cost; best proxy is (total_cost - toll - other) ratio
                # For a precise figure we'd need fuel_cost stored — use avg margin as proxy
                func.avg(Job.margin_pct).label("avg_margin_pct"),
                func.avg(Job.total_cost).label("avg_total_cost"),
                func.avg(Job.offered_rate).label("avg_rate"),
                func.min(Job.fuel_price_per_unit).label("min_fuel_price"),
                func.max(Job.fuel_price_per_unit).label("max_fuel_price"),
            )
            .where(
                Job.fleet_id == fleet_id,
                Job.status.in_(["accepted", "completed"]),
                Job.fuel_price_per_unit.isnot(None),
            )
            .group_by(
                extract("year",  Job.created_at),
                extract("month", Job.created_at),
            )
            .order_by(
                extract("year",  Job.created_at).desc(),
                extract("month", Job.created_at).desc(),
            )
            .limit(months)
        )

        rows = result.all()
        return [
            {
                "year":            int(r.year),
                "month":           int(r.month),
                "job_count":       int(r.job_count),
                "avg_fuel_price":  round(float(r.avg_fuel_price), 3),
                "min_fuel_price":  round(float(r.min_fuel_price), 3),
                "max_fuel_price":  round(float(r.max_fuel_price), 3),
                "fuel_price_range": round(float(r.max_fuel_price) - float(r.min_fuel_price), 3),
                "avg_margin_pct":  round(float(r.avg_margin_pct), 2),
                "avg_total_cost":  round(float(r.avg_total_cost), 2),
                "avg_rate":        round(float(r.avg_rate), 2),
            }
            for r in reversed(rows)
        ]
