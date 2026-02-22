"""
app/schemas/intelligence.py
────────────────────────────
Pydantic response schemas for the Phase 2 intelligence endpoints.
Kept separate from schemas.py to avoid growing it further.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


# ── Benchmarking ──────────────────────────────────────────────────────────

class FleetMetricsSchema(BaseModel):
    job_count: int
    avg_margin_pct: float
    avg_net_profit: float
    avg_rate_per_km: float
    avg_cost_per_km: float
    total_revenue: float
    total_profit: float
    fleet_size_bucket: str
    truck_count: int


class IndustryContextSchema(BaseModel):
    n_fleets: int
    fleet_size_bucket: str
    industry_avg_margin_pct: float
    p25_margin_pct: float
    p50_margin_pct: float
    p75_margin_pct: float
    p90_margin_pct: float
    industry_avg_rate_per_km: float
    industry_avg_cost_per_km: float


class BenchmarkResponse(BaseModel):
    fleet_metrics: FleetMetricsSchema
    industry_context: Optional[IndustryContextSchema]
    fleet_percentile: Optional[int]
    margin_vs_industry: Optional[float]
    rate_vs_industry: Optional[float]
    cost_vs_industry: Optional[float]
    insights: list[str]
    insufficient_data: bool


# ── Trends ────────────────────────────────────────────────────────────────

class TrendDataPointSchema(BaseModel):
    week_start: Optional[str]
    avg_margin_pct: float
    job_count: int
    weekly_revenue: float


class TrendResponse(BaseModel):
    trend: str                            # "improving" | "flat" | "declining" | "unknown"
    slope_pct_per_week: Optional[float]
    r2: Optional[float]
    confidence: str                       # "high" | "medium" | "low" | "insufficient_data"
    alert: bool
    alert_message: Optional[str]
    weeks_analyzed: int
    data_points: list[TrendDataPointSchema]
    summary: str


# ── Anomalies ─────────────────────────────────────────────────────────────

class AnomalySchema(BaseModel):
    job_id: str
    anomaly_type: str
    severity: str
    z_score: float
    actual_value: float
    fleet_mean: float
    fleet_stddev: float
    description: str
    origin: Optional[str]
    destination: Optional[str]
    created_at: str


class AnomalyReportResponse(BaseModel):
    fleet_id: str
    days_scanned: int
    n_jobs_scanned: int
    n_anomalies: int
    anomalies: list[AnomalySchema]
    baseline_jobs_count: int
    insufficient_baseline: bool
    summary: str
