"""
app/api/v1/endpoints/intelligence.py  [Phase 3 update — tier gating added]
──────────────────────────────────────────────────────────────────────────
Only change vs Phase 2: all intelligence routes now require tier2+.
Added `dependencies=[Depends(enforce_intelligence_tier)]` to each route.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.core.tier_limits import enforce_intelligence_tier   # ← Phase 3 addition
from app.models.models import User
from app.repositories.intelligence_repository import IntelligenceRepository
from app.repositories.ml_repository import PredictionLogRepository
from app.schemas.intelligence import (
    BenchmarkResponse,
    TrendResponse,
    AnomalyReportResponse,
    FleetMetricsSchema,
    IndustryContextSchema,
    TrendDataPointSchema,
    AnomalySchema,
)
from app.services.benchmarking import BenchmarkingService
from app.services.trends import TrendDetectionService
from app.services.anomaly import AnomalyDetectionService

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


def get_intelligence_repo(db: AsyncSession = Depends(get_db)) -> IntelligenceRepository:
    return IntelligenceRepository(db)


def get_log_repo(db: AsyncSession = Depends(get_db)) -> PredictionLogRepository:
    return PredictionLogRepository(db)


@router.get(
    "/benchmark",
    response_model=BenchmarkResponse,
    dependencies=[Depends(enforce_intelligence_tier)],    # ← PHASE 3
)
async def get_benchmark(
    current_user: User = Depends(get_current_fleet_user),
    repo: IntelligenceRepository = Depends(get_intelligence_repo),
):
    """
    Fleet performance vs anonymized industry peers. Requires tier2+.
    """
    service = BenchmarkingService(repo)
    result = await service.get_benchmark(current_user.fleet_id)
    return _benchmark_to_response(result)


@router.get(
    "/trends",
    response_model=TrendResponse,
    dependencies=[Depends(enforce_intelligence_tier)],    # ← PHASE 3
)
async def get_trends(
    weeks: int = Query(default=12, ge=4, le=52),
    current_user: User = Depends(get_current_fleet_user),
    repo: IntelligenceRepository = Depends(get_intelligence_repo),
):
    """
    Profitability trend signal. Requires tier2+.
    """
    service = TrendDetectionService(repo)
    result = await service.detect(current_user.fleet_id, weeks=weeks)
    return _trend_to_response(result)


@router.get(
    "/anomalies",
    response_model=AnomalyReportResponse,
    dependencies=[Depends(enforce_intelligence_tier)],    # ← PHASE 3
)
async def get_anomalies(
    days: int = Query(default=30, ge=7, le=90),
    current_user: User = Depends(get_current_fleet_user),
    repo: IntelligenceRepository = Depends(get_intelligence_repo),
    log_repo: PredictionLogRepository = Depends(get_log_repo),
):
    """
    Z-score anomaly detection. Requires tier2+.
    """
    service = AnomalyDetectionService(repo, log_repo)
    result = await service.scan_recent(current_user.fleet_id, days=days)
    return _anomaly_to_response(result)


@router.get(
    "/summary",
    dependencies=[Depends(enforce_intelligence_tier)],    # ← PHASE 3
)
async def get_intelligence_summary(
    current_user: User = Depends(get_current_fleet_user),
    repo: IntelligenceRepository = Depends(get_intelligence_repo),
    log_repo: PredictionLogRepository = Depends(get_log_repo),
):
    """
    Combined benchmark + trend + anomaly summary. Requires tier2+.
    """
    import asyncio
    bench_service   = BenchmarkingService(repo)
    trend_service   = TrendDetectionService(repo)
    anomaly_service = AnomalyDetectionService(repo, log_repo)

    benchmark, trend, anomalies = await asyncio.gather(
        bench_service.get_benchmark(current_user.fleet_id),
        trend_service.detect(current_user.fleet_id, weeks=8),
        anomaly_service.scan_recent(current_user.fleet_id, days=30),
    )

    return {
        "benchmark": {
            "fleet_percentile": benchmark.fleet_percentile,
            "avg_margin_pct": benchmark.fleet_metrics.avg_margin_pct,
            "margin_vs_industry": benchmark.margin_vs_industry,
            "insufficient_data": benchmark.insufficient_data,
            "top_insight": benchmark.insights[0] if benchmark.insights else None,
        },
        "trend": {
            "trend": trend.trend,
            "slope_pct_per_week": trend.slope_pct_per_week,
            "confidence": trend.confidence,
            "alert": trend.alert,
            "alert_message": trend.alert_message,
            "summary": trend.summary,
        },
        "anomalies": {
            "n_anomalies": anomalies.n_anomalies,
            "high_severity": sum(1 for a in anomalies.anomalies if a.severity == "high"),
            "insufficient_baseline": anomalies.insufficient_baseline,
            "summary": anomalies.summary,
            "top_anomaly": _top_anomaly(anomalies.anomalies),
        },
    }


# ── Response converters ───────────────────────────────────────────────────

def _benchmark_to_response(r) -> BenchmarkResponse:
    return BenchmarkResponse(
        fleet_metrics=FleetMetricsSchema(**asdict(r.fleet_metrics)),
        industry_context=IndustryContextSchema(**asdict(r.industry_context)) if r.industry_context else None,
        fleet_percentile=r.fleet_percentile,
        margin_vs_industry=r.margin_vs_industry,
        rate_vs_industry=r.rate_vs_industry,
        cost_vs_industry=r.cost_vs_industry,
        insights=r.insights,
        insufficient_data=r.insufficient_data,
    )


def _trend_to_response(r) -> TrendResponse:
    return TrendResponse(
        trend=r.trend,
        slope_pct_per_week=r.slope_pct_per_week,
        r2=r.r2,
        confidence=r.confidence,
        alert=r.alert,
        alert_message=r.alert_message,
        weeks_analyzed=r.weeks_analyzed,
        data_points=[TrendDataPointSchema(**asdict(dp)) for dp in r.data_points],
        summary=r.summary,
    )


def _anomaly_to_response(r) -> AnomalyReportResponse:
    return AnomalyReportResponse(
        fleet_id=r.fleet_id,
        days_scanned=r.days_scanned,
        n_jobs_scanned=r.n_jobs_scanned,
        n_anomalies=r.n_anomalies,
        anomalies=[AnomalySchema(**asdict(a)) for a in r.anomalies],
        baseline_jobs_count=r.baseline_jobs_count,
        insufficient_baseline=r.insufficient_baseline,
        summary=r.summary,
    )


def _top_anomaly(anomalies) -> dict | None:
    if not anomalies:
        return None
    a = anomalies[0]
    return {
        "job_id": a.job_id,
        "anomaly_type": a.anomaly_type,
        "severity": a.severity,
        "description": a.description,
    }
