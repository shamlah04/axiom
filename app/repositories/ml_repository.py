from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_models import PredictionLog, MLModelVersion


class PredictionLogRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log: PredictionLog) -> PredictionLog:
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_by_job_id(self, job_id: uuid.UUID) -> Optional[PredictionLog]:
        result = await self.db.execute(
            select(PredictionLog).where(PredictionLog.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def update_actuals(
        self,
        job_id: uuid.UUID,
        actual_net_profit: float,
        actual_total_cost: float,
        offered_rate: float,
    ) -> Optional[PredictionLog]:
        log = await self.get_by_job_id(job_id)
        if not log:
            return None

        actual_margin_pct = (actual_net_profit / offered_rate * 100.0) if offered_rate > 0 else 0.0
        error = actual_net_profit - log.predicted_net_profit
        error_pct = (error / abs(actual_net_profit) * 100.0) if actual_net_profit != 0 else 0.0

        log.actual_net_profit = actual_net_profit
        log.actual_total_cost = actual_total_cost
        log.actual_margin_pct = actual_margin_pct
        log.profit_error = error
        log.profit_error_pct = error_pct
        log.abs_profit_error = abs(error)

        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_accuracy_summary(self, fleet_id: Optional[uuid.UUID] = None) -> dict:
        """
        Aggregate prediction accuracy across all resolved predictions.
        Optionally scoped to a fleet (fleet_id=None → global, for retraining assessment).
        """
        filters = [PredictionLog.actual_net_profit.isnot(None)]
        if fleet_id:
            filters.append(PredictionLog.fleet_id == fleet_id)

        result = await self.db.execute(
            select(
                func.count(PredictionLog.id).label("n"),
                func.avg(PredictionLog.abs_profit_error).label("mae"),
                func.avg(
                    PredictionLog.profit_error * PredictionLog.profit_error
                ).label("mse"),
                func.avg(PredictionLog.profit_error_pct).label("avg_error_pct"),
                func.avg(PredictionLog.predicted_margin_pct).label("avg_predicted_margin"),
                func.avg(PredictionLog.actual_margin_pct).label("avg_actual_margin"),
            ).where(and_(*filters))
        )
        row = result.one()
        n = row.n or 0
        mse = float(row.mse or 0)
        return {
            "n_resolved_predictions": n,
            "mae_eur": round(float(row.mae or 0), 2),
            "rmse_eur": round(mse ** 0.5, 2),
            "avg_error_pct": round(float(row.avg_error_pct or 0), 2),
            "avg_predicted_margin_pct": round(float(row.avg_predicted_margin or 0), 2),
            "avg_actual_margin_pct": round(float(row.avg_actual_margin or 0), 2),
        }


class MLModelVersionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, mv: MLModelVersion) -> MLModelVersion:
        self.db.add(mv)
        await self.db.commit()
        await self.db.refresh(mv)
        return mv

    async def get_active(self) -> Optional[MLModelVersion]:
        result = await self.db.execute(
            select(MLModelVersion).where(MLModelVersion.is_active == True).limit(1)
        )
        return result.scalar_one_or_none()

    async def set_active(self, version: str) -> Optional[MLModelVersion]:
        # NOTE: For Phase 1 we scan all versions; consider pagination/filtered update if N > 1000.
        # Deactivate all
        all_result = await self.db.execute(select(MLModelVersion))
        for mv in all_result.scalars().all():
            mv.is_active = False
        # Activate target
        target = await self.db.execute(
            select(MLModelVersion).where(MLModelVersion.version == version)
        )
        mv = target.scalar_one_or_none()
        if mv:
            mv.is_active = True
        await self.db.commit()
        return mv

    async def list_all(self) -> list[MLModelVersion]:
        result = await self.db.execute(
            select(MLModelVersion).order_by(MLModelVersion.created_at.desc())
        )
        return list(result.scalars().all())
