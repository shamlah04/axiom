"""
app/repositories/intelligence_repository.py
─────────────────────────────────────────────
All SQL aggregation queries for the Phase 2 Data Intelligence Layer.

Queries are read-only and always scoped either to:
  - A single fleet  (fleet_id param)        → personal analytics
  - All fleets      (fleet_id=None)          → anonymized cross-fleet aggregation

Privacy contract:
  - Cross-fleet queries NEVER return fleet_id in results
  - Fleet bucketing (by truck count) prevents identification
  - Minimum fleet threshold (MIN_FLEETS_FOR_BENCHMARK = 3) enforced before
    percentile data is returned — avoids single-fleet "benchmarks"
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Float, Integer, func, and_, case, cast, text, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

import numpy as np

from app.models.models import Job, Fleet, Truck

MIN_FLEETS_FOR_BENCHMARK = 3   # minimum distinct fleets before cross-fleet data is returned
MIN_JOBS_FOR_TREND = 5         # minimum jobs per week before slope is meaningful


class IntelligenceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ──────────────────────────────────────────────────────────────────────
    # 1. BENCHMARKING — fleet percentile vs industry
    # ──────────────────────────────────────────────────────────────────────

    async def fleet_performance_summary(self, fleet_id: uuid.UUID) -> dict:
        """Single fleet's aggregate margin, revenue/km, and job count."""
        result = await self.db.execute(
            select(
                func.count(Job.id).label("job_count"),
                func.avg(Job.margin_pct).label("avg_margin_pct"),
                func.avg(Job.net_profit).label("avg_net_profit"),
                func.avg(Job.offered_rate / Job.distance_km).label("avg_rate_per_km"),
                func.avg(Job.total_cost / Job.distance_km).label("avg_cost_per_km"),
                func.sum(Job.offered_rate).label("total_revenue"),
                func.sum(Job.net_profit).label("total_profit"),
            ).where(
                and_(
                    Job.fleet_id == fleet_id,
                    Job.margin_pct.isnot(None),
                    Job.status.in_(["accepted", "completed"]),
                )
            )
        )
        row = result.one()
        return {
            "job_count": row.job_count or 0,
            "avg_margin_pct": round(float(row.avg_margin_pct or 0), 2),
            "avg_net_profit": round(float(row.avg_net_profit or 0), 2),
            "avg_rate_per_km": round(float(row.avg_rate_per_km or 0), 3),
            "avg_cost_per_km": round(float(row.avg_cost_per_km or 0), 3),
            "total_revenue": round(float(row.total_revenue or 0), 2),
            "total_profit": round(float(row.total_profit or 0), 2),
        }

    async def industry_percentiles(self, fleet_size_bucket: str) -> Optional[dict]:
        """
        Computes anonymized industry percentiles for a given fleet size bucket.
        Returns None if fewer than MIN_FLEETS_FOR_BENCHMARK fleets qualify.

        fleet_size_bucket: "small" (1-2 trucks) | "medium" (3-10) | "large" (11+)
        """
        # Subquery: per-fleet averages
        truck_counts = (
            select(
                Truck.fleet_id,
                func.count(Truck.id).label("truck_count"),
            )
            .where(Truck.is_active == True)
            .group_by(Truck.fleet_id)
            .subquery()
        )

        bucket_filter = self._bucket_filter(fleet_size_bucket, truck_counts.c.truck_count)

        per_fleet = (
            select(
                Job.fleet_id,
                func.avg(Job.margin_pct).label("fleet_avg_margin"),
                func.avg(Job.net_profit).label("fleet_avg_profit"),
                func.avg(Job.offered_rate / Job.distance_km).label("fleet_avg_rate_per_km"),
                func.avg(Job.total_cost / Job.distance_km).label("fleet_avg_cost_per_km"),
            )
            .join(truck_counts, Job.fleet_id == truck_counts.c.fleet_id)
            .where(
                and_(
                    Job.margin_pct.isnot(None),
                    Job.status.in_(["accepted", "completed"]),
                    bucket_filter,
                )
            )
            .group_by(Job.fleet_id)
            .subquery()
        )

        # Count qualifying fleets
        count_result = await self.db.execute(
            select(func.count(per_fleet.c.fleet_id))
        )
        n_fleets = count_result.scalar() or 0

        if n_fleets < MIN_FLEETS_FOR_BENCHMARK:
            return None

        # Percentile aggregation (PostgreSQL PERCENTILE_CONT)
        if "sqlite" in str(self.db.bind.dialect.name).lower():
            # Fallback for SQLite tests (though usually unreachable due to MIN_FLEETS gate)
            res = await self.db.execute(select(per_fleet))
            rows = res.fetchall()
            margins = [float(r.fleet_avg_margin) for r in rows]
            rates = [float(r.fleet_avg_rate_per_km) for r in rows]
            costs = [float(r.fleet_avg_cost_per_km) for r in rows]
            
            return {
                "n_fleets": n_fleets,
                "fleet_size_bucket": fleet_size_bucket,
                "industry_avg_margin_pct": round(float(np.mean(margins)), 2),
                "p25_margin_pct": round(float(np.percentile(margins, 25)), 2),
                "p50_margin_pct": round(float(np.percentile(margins, 50)), 2),
                "p75_margin_pct": round(float(np.percentile(margins, 75)), 2),
                "p90_margin_pct": round(float(np.percentile(margins, 90)), 2),
                "industry_avg_rate_per_km": round(float(np.mean(rates)), 3),
                "industry_avg_cost_per_km": round(float(np.mean(costs)), 3),
            }

        result = await self.db.execute(
            select(
                func.count(per_fleet.c.fleet_id).label("n_fleets"),
                func.avg(per_fleet.c.fleet_avg_margin).label("industry_avg_margin"),
                func.percentile_cont(0.25).within_group(
                    per_fleet.c.fleet_avg_margin
                ).label("p25_margin"),
                func.percentile_cont(0.50).within_group(
                    per_fleet.c.fleet_avg_margin
                ).label("p50_margin"),
                func.percentile_cont(0.75).within_group(
                    per_fleet.c.fleet_avg_margin
                ).label("p75_margin"),
                func.percentile_cont(0.90).within_group(
                    per_fleet.c.fleet_avg_margin
                ).label("p90_margin"),
                func.avg(per_fleet.c.fleet_avg_rate_per_km).label("industry_avg_rate_per_km"),
                func.avg(per_fleet.c.fleet_avg_cost_per_km).label("industry_avg_cost_per_km"),
            )
        )
        row = result.one()

        return {
            "n_fleets": n_fleets,
            "fleet_size_bucket": fleet_size_bucket,
            "industry_avg_margin_pct": round(float(row.industry_avg_margin or 0), 2),
            "p25_margin_pct": round(float(row.p25_margin or 0), 2),
            "p50_margin_pct": round(float(row.p50_margin or 0), 2),
            "p75_margin_pct": round(float(row.p75_margin or 0), 2),
            "p90_margin_pct": round(float(row.p90_margin or 0), 2),
            "industry_avg_rate_per_km": round(float(row.industry_avg_rate_per_km or 0), 3),
            "industry_avg_cost_per_km": round(float(row.industry_avg_cost_per_km or 0), 3),
        }

    async def get_fleet_truck_count(self, fleet_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Truck.id)).where(
                and_(Truck.fleet_id == fleet_id, Truck.is_active == True)
            )
        )
        return result.scalar() or 0

    # ──────────────────────────────────────────────────────────────────────
    # 2. WEEKLY TREND DATA
    # ──────────────────────────────────────────────────────────────────────

    async def weekly_margin_series(
        self, fleet_id: uuid.UUID, weeks: int = 12
    ) -> list[dict]:
        """
        Returns weekly avg_margin_pct for the last N weeks.
        Used by TrendDetectionService to compute the slope.
        """
        since = datetime.now(timezone.utc) - timedelta(weeks=weeks)

        if "sqlite" in str(self.db.bind.dialect.name).lower():
            # SQLite doesn't have date_trunc. We'll fetch and group in Python for tests.
            result = await self.db.execute(
                select(Job.created_at, Job.margin_pct, Job.net_profit, Job.offered_rate)
                .where(
                    and_(
                        Job.fleet_id == fleet_id,
                        Job.created_at >= since,
                        Job.margin_pct.isnot(None),
                        Job.status.in_(["accepted", "completed"]),
                    )
                )
            )
            rows = result.fetchall()
            # Group by ISO week
            entries = {}
            for r in rows:
                # Approximate week start by finding Monday
                dt = r.created_at
                monday = dt - timedelta(days=dt.weekday())
                week_start = monday.date().isoformat()
                if week_start not in entries:
                    entries[week_start] = {"count": 0, "margin": [], "profit": [], "revenue": 0.0}
                entries[week_start]["count"] += 1
                entries[week_start]["margin"].append(float(r.margin_pct))
                entries[week_start]["profit"].append(float(r.net_profit))
                entries[week_start]["revenue"] += float(r.offered_rate)
            
            return [
                {
                    "week_start": ws,
                    "job_count": e["count"],
                    "avg_margin_pct": round(float(np.mean(e["margin"])), 2),
                    "avg_net_profit": round(float(np.mean(e["profit"])), 2),
                    "weekly_revenue": round(e["revenue"], 2),
                }
                for ws, e in sorted(entries.items())
            ]

        result = await self.db.execute(
            select(
                func.date_trunc("week", Job.created_at).label("week_start"),
                func.count(Job.id).label("job_count"),
                func.avg(Job.margin_pct).label("avg_margin_pct"),
                func.avg(Job.net_profit).label("avg_net_profit"),
                func.sum(Job.offered_rate).label("weekly_revenue"),
            )
            .where(
                and_(
                    Job.fleet_id == fleet_id,
                    Job.created_at >= since,
                    Job.margin_pct.isnot(None),
                    Job.status.in_(["accepted", "completed"]),
                )
            )
            .group_by(text("week_start"))
            .order_by(text("week_start ASC"))
        )

        return [
            {
                "week_start": row.week_start.isoformat() if row.week_start else None,
                "job_count": row.job_count or 0,
                "avg_margin_pct": round(float(row.avg_margin_pct or 0), 2),
                "avg_net_profit": round(float(row.avg_net_profit or 0), 2),
                "weekly_revenue": round(float(row.weekly_revenue or 0), 2),
            }
            for row in result.fetchall()
        ]

    # ──────────────────────────────────────────────────────────────────────
    # 3. ANOMALY DETECTION DATA
    # ──────────────────────────────────────────────────────────────────────

    async def fleet_margin_stats(self, fleet_id: uuid.UUID) -> dict:
        """
        Fleet-level mean and stddev of margin_pct — used as Z-score baseline.
        """
        if "sqlite" in str(self.db.bind.dialect.name).lower():
            # SQLite doesn't have stddev_pop. Fetch and compute in Python.
            result = await self.db.execute(
                select(Job.margin_pct, Job.total_cost).where(
                    and_(
                        Job.fleet_id == fleet_id,
                        Job.margin_pct.isnot(None),
                        Job.status.in_(["accepted", "completed"]),
                    )
                )
            )
            rows = result.fetchall()
            if not rows:
                return {"mean_margin": 0.0, "stddev_margin": 1.0, "mean_total_cost": 0.0, "stddev_total_cost": 1.0, "n": 0}
            
            margins = [float(r.margin_pct) for r in rows]
            costs = [float(r.total_cost) for r in rows]
            
            return {
                "mean_margin": float(np.mean(margins)),
                "stddev_margin": float(np.std(margins)) or 1.0,
                "mean_total_cost": float(np.mean(costs)),
                "stddev_total_cost": float(np.std(costs)) or 1.0,
                "n": len(rows),
            }

        result = await self.db.execute(
            select(
                func.avg(Job.margin_pct).label("mean_margin"),
                func.stddev_pop(Job.margin_pct).label("stddev_margin"),
                func.avg(Job.total_cost).label("mean_total_cost"),
                func.stddev_pop(Job.total_cost).label("stddev_total_cost"),
                func.count(Job.id).label("n"),
            ).where(
                and_(
                    Job.fleet_id == fleet_id,
                    Job.margin_pct.isnot(None),
                    Job.status.in_(["accepted", "completed"]),
                )
            )
        )
        row = result.one()
        return {
            "mean_margin": float(row.mean_margin or 0),
            "stddev_margin": float(row.stddev_margin or 1),   # default 1 prevents div-by-zero
            "mean_total_cost": float(row.mean_total_cost or 0),
            "stddev_total_cost": float(row.stddev_total_cost or 1),
            "n": row.n or 0,
        }

    async def recent_jobs_with_stats(
        self, fleet_id: uuid.UUID, days: int = 30
    ) -> list[dict]:
        """
        Returns recent jobs with the fields needed for anomaly scoring.
        Does NOT include prediction_logs — anomaly detection uses job-level data only
        so it works even before actuals are recorded.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                Job.id,
                Job.origin,
                Job.destination,
                Job.distance_km,
                Job.offered_rate,
                Job.total_cost,
                Job.net_profit,
                Job.margin_pct,
                Job.risk_level,
                Job.status,
                Job.created_at,
            ).where(
                and_(
                    Job.fleet_id == fleet_id,
                    Job.created_at >= since,
                    Job.margin_pct.isnot(None),
                )
            ).order_by(Job.created_at.desc())
        )

        return [
            {
                "job_id": str(row.id),
                "origin": row.origin,
                "destination": row.destination,
                "distance_km": row.distance_km,
                "offered_rate": row.offered_rate,
                "total_cost": row.total_cost,
                "net_profit": row.net_profit,
                "margin_pct": row.margin_pct,
                "risk_level": row.risk_level.value if row.risk_level else None,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
            }
            for row in result.fetchall()
        ]

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _bucket_filter(bucket: str, truck_count_col):
        if bucket == "small":
            return and_(truck_count_col >= 1, truck_count_col <= 2)
        elif bucket == "medium":
            return and_(truck_count_col >= 3, truck_count_col <= 10)
        else:  # large
            return truck_count_col >= 11

    @staticmethod
    def fleet_size_to_bucket(truck_count: int) -> str:
        if truck_count <= 2:
            return "small"
        elif truck_count <= 10:
            return "medium"
        return "large"
