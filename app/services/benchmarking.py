"""
app/services/benchmarking.py
─────────────────────────────
Cross-fleet anonymized benchmarking service.

Answers: "How does my fleet's margin/cost/revenue compare to similar fleets?"

Privacy design:
  - Fleet identities are never surfaced — only bucket-level aggregates
  - Minimum fleet threshold (3) before percentile data is returned
  - Percentile computed on per-fleet averages (not raw jobs) → no individual
    job data crosses tenant boundaries

Output:
  BenchmarkResult — the fleet's metrics + industry context + percentile rank
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from app.repositories.intelligence_repository import IntelligenceRepository


@dataclass
class FleetMetrics:
    job_count: int
    avg_margin_pct: float
    avg_net_profit: float
    avg_rate_per_km: float
    avg_cost_per_km: float
    total_revenue: float
    total_profit: float
    fleet_size_bucket: str
    truck_count: int


@dataclass
class IndustryContext:
    n_fleets: int
    fleet_size_bucket: str
    industry_avg_margin_pct: float
    p25_margin_pct: float
    p50_margin_pct: float
    p75_margin_pct: float
    p90_margin_pct: float
    industry_avg_rate_per_km: float
    industry_avg_cost_per_km: float


@dataclass
class BenchmarkResult:
    fleet_metrics: FleetMetrics
    industry_context: Optional[IndustryContext]
    fleet_percentile: Optional[int]       # 0-100, where fleet sits vs industry
    margin_vs_industry: Optional[float]   # fleet_avg - industry_avg
    rate_vs_industry: Optional[float]
    cost_vs_industry: Optional[float]
    insights: list[str]                   # human-readable callouts
    insufficient_data: bool               # True if < MIN_FLEETS for benchmark


class BenchmarkingService:
    """
    Computes fleet-vs-industry benchmark report.
    Called by GET /api/v1/intelligence/benchmark
    """

    def __init__(self, repo: IntelligenceRepository):
        self.repo = repo

    async def get_benchmark(self, fleet_id: uuid.UUID) -> BenchmarkResult:
        # 1. Get this fleet's performance
        perf = await self.repo.fleet_performance_summary(fleet_id)
        truck_count = await self.repo.get_fleet_truck_count(fleet_id)
        bucket = IntelligenceRepository.fleet_size_to_bucket(truck_count)

        fleet_metrics = FleetMetrics(
            job_count=perf["job_count"],
            avg_margin_pct=perf["avg_margin_pct"],
            avg_net_profit=perf["avg_net_profit"],
            avg_rate_per_km=perf["avg_rate_per_km"],
            avg_cost_per_km=perf["avg_cost_per_km"],
            total_revenue=perf["total_revenue"],
            total_profit=perf["total_profit"],
            fleet_size_bucket=bucket,
            truck_count=truck_count,
        )

        if fleet_metrics.job_count == 0:
            return BenchmarkResult(
                fleet_metrics=fleet_metrics,
                industry_context=None,
                fleet_percentile=None,
                margin_vs_industry=None,
                rate_vs_industry=None,
                cost_vs_industry=None,
                insights=["No accepted jobs yet. Submit and accept jobs to see benchmark data."],
                insufficient_data=True,
            )

        # 2. Get industry percentiles for this fleet's bucket
        industry_raw = await self.repo.industry_percentiles(bucket)

        if industry_raw is None:
            return BenchmarkResult(
                fleet_metrics=fleet_metrics,
                industry_context=None,
                fleet_percentile=None,
                margin_vs_industry=None,
                rate_vs_industry=None,
                cost_vs_industry=None,
                insights=[
                    f"Not enough {bucket} fleets in the dataset for anonymous benchmarking yet. "
                    "Check back as more fleets join Axiom."
                ],
                insufficient_data=True,
            )

        industry = IndustryContext(**industry_raw)

        # 3. Compute fleet percentile rank
        percentile = self._estimate_percentile(
            fleet_metrics.avg_margin_pct, industry
        )

        # 4. Deltas
        margin_delta = round(fleet_metrics.avg_margin_pct - industry.industry_avg_margin_pct, 2)
        rate_delta = round(fleet_metrics.avg_rate_per_km - industry.industry_avg_rate_per_km, 3)
        cost_delta = round(fleet_metrics.avg_cost_per_km - industry.industry_avg_cost_per_km, 3)

        # 5. Generate insights
        insights = self._generate_insights(fleet_metrics, industry, percentile, margin_delta)

        return BenchmarkResult(
            fleet_metrics=fleet_metrics,
            industry_context=industry,
            fleet_percentile=percentile,
            margin_vs_industry=margin_delta,
            rate_vs_industry=rate_delta,
            cost_vs_industry=cost_delta,
            insights=insights,
            insufficient_data=False,
        )

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_percentile(fleet_margin: float, industry: IndustryContext) -> int:
        """
        Interpolates fleet's percentile rank from industry quartile breakpoints.
        Simple linear interpolation between known percentile points.
        """
        p = [
            (0,   industry.p25_margin_pct - 20),   # synthetic p0 = p25 - 2 stddev approx
            (25,  industry.p25_margin_pct),
            (50,  industry.p50_margin_pct),
            (75,  industry.p75_margin_pct),
            (90,  industry.p90_margin_pct),
            (100, industry.p90_margin_pct + 20),   # synthetic p100
        ]

        for i in range(len(p) - 1):
            pct_lo, val_lo = p[i]
            pct_hi, val_hi = p[i + 1]
            if val_lo <= fleet_margin <= val_hi:
                if val_hi == val_lo:
                    return pct_lo
                frac = (fleet_margin - val_lo) / (val_hi - val_lo)
                return min(100, max(0, int(pct_lo + frac * (pct_hi - pct_lo))))

        return 100 if fleet_margin > p[-1][1] else 0

    @staticmethod
    def _generate_insights(
        fleet: FleetMetrics,
        industry: IndustryContext,
        percentile: int,
        margin_delta: float,
    ) -> list[str]:
        insights = []

        if percentile >= 75:
            insights.append(
                f"Top-quartile performer: your avg margin of {fleet.avg_margin_pct:.1f}% "
                f"beats {percentile}% of similar {fleet.fleet_size_bucket} fleets."
            )
        elif percentile >= 50:
            insights.append(
                f"Above median: {fleet.avg_margin_pct:.1f}% margin vs "
                f"industry median of {industry.p50_margin_pct:.1f}%."
            )
        elif percentile >= 25:
            insights.append(
                f"Below median: margin of {fleet.avg_margin_pct:.1f}% is in the "
                f"2nd quartile. Industry median is {industry.p50_margin_pct:.1f}%."
            )
        else:
            insights.append(
                f"Bottom-quartile: {fleet.avg_margin_pct:.1f}% margin. "
                f"Top quartile starts at {industry.p75_margin_pct:.1f}%. "
                f"Review pricing or cost controls."
            )

        if fleet.avg_cost_per_km > industry.industry_avg_cost_per_km * 1.10:
            insights.append(
                f"Cost per km ({fleet.avg_cost_per_km:.3f} EUR) is 10%+ above industry avg "
                f"({industry.industry_avg_cost_per_km:.3f} EUR). Check maintenance and fuel contracts."
            )

        if fleet.avg_rate_per_km < industry.industry_avg_rate_per_km * 0.90:
            insights.append(
                f"Revenue per km ({fleet.avg_rate_per_km:.3f} EUR) is 10%+ below peers. "
                f"Consider revising minimum rate thresholds."
            )

        return insights
