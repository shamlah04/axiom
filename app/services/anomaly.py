"""
app/services/anomaly.py
────────────────────────
Z-score based anomaly detection for fleet jobs.

Two anomaly types:
  1. margin_outlier  — job margin is > Z_THRESHOLD std devs from fleet mean
                       Works on predicted margin (available immediately)
  2. cost_spike      — job's actual cost >> predicted cost
                       Only available after actuals are recorded
                       Uses prediction_logs.profit_error

Why Z-score instead of Isolation Forest / ML?
  - Works on small datasets (even 20 jobs)
  - Fully interpretable ("this job is 2.8 std devs below your avg margin")
  - No training required, no model version to manage
  - Upgrade path: swap in sklearn IsolationForest in Phase 4 when N > 500

Design:
  AnomalyDetectionService operates on two data sources:
    - jobs table (margin_pct, total_cost) → margin outliers
    - prediction_logs table (profit_error) → cost spikes (post-actuals)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from app.repositories.intelligence_repository import IntelligenceRepository
from app.repositories.ml_repository import PredictionLogRepository

# Detection thresholds
Z_THRESHOLD_MARGIN = 2.0     # |z| > 2.0 = anomalous margin
Z_THRESHOLD_COST   = 2.5     # |z| > 2.5 = cost spike (stricter, since actuals are ground truth)
MIN_JOBS_FOR_BASELINE = 10   # need at least 10 jobs to build a meaningful baseline


@dataclass
class Anomaly:
    job_id: str
    anomaly_type: str           # "margin_outlier" | "cost_spike" | "unusually_profitable"
    severity: str               # "high" | "medium"
    z_score: float
    actual_value: float         # the metric that triggered detection
    fleet_mean: float           # fleet baseline for context
    fleet_stddev: float
    description: str
    origin: Optional[str]
    destination: Optional[str]
    created_at: str


@dataclass
class AnomalyReport:
    fleet_id: str
    days_scanned: int
    n_jobs_scanned: int
    n_anomalies: int
    anomalies: list[Anomaly]
    baseline_jobs_count: int    # how many jobs the baseline was built from
    insufficient_baseline: bool
    summary: str


class AnomalyDetectionService:
    """
    Scans recent fleet jobs for statistical outliers.
    Called by GET /api/v1/intelligence/anomalies
    """

    def __init__(
        self,
        repo: IntelligenceRepository,
        log_repo: PredictionLogRepository,
    ):
        self.repo = repo
        self.log_repo = log_repo

    async def scan_recent(
        self,
        fleet_id: uuid.UUID,
        days: int = 30,
    ) -> AnomalyReport:

        # 1. Get fleet baseline statistics
        stats = await self.repo.fleet_margin_stats(fleet_id)
        n_baseline = stats["n"]

        # 2. Get recent jobs
        recent_jobs = await self.repo.recent_jobs_with_stats(fleet_id, days=days)

        if n_baseline < MIN_JOBS_FOR_BASELINE:
            return AnomalyReport(
                fleet_id=str(fleet_id),
                days_scanned=days,
                n_jobs_scanned=len(recent_jobs),
                n_anomalies=0,
                anomalies=[],
                baseline_jobs_count=n_baseline,
                insufficient_baseline=True,
                summary=(
                    f"Baseline too small ({n_baseline} jobs). "
                    f"Need at least {MIN_JOBS_FOR_BASELINE} accepted/completed jobs "
                    f"before anomaly detection is reliable."
                ),
            )

        anomalies: list[Anomaly] = []

        mean_m  = stats["mean_margin"]
        std_m   = stats["stddev_margin"]
        mean_c  = stats["mean_total_cost"]
        std_c   = stats["stddev_total_cost"]

        for job in recent_jobs:
            # ── Margin outlier detection ─────────────────────────────────
            if job["margin_pct"] is not None and std_m > 0:
                z_margin = (job["margin_pct"] - mean_m) / std_m

                if abs(z_margin) > Z_THRESHOLD_MARGIN:
                    if z_margin < 0:
                        anomaly_type = "margin_outlier"
                        severity = "high" if abs(z_margin) > 3.0 else "medium"
                        description = (
                            f"Margin of {job['margin_pct']:.1f}% is {abs(z_margin):.1f} std devs "
                            f"below your fleet average ({mean_m:.1f}%). "
                            f"Review cost inputs or rate negotiation for this route."
                        )
                    else:
                        anomaly_type = "unusually_profitable"
                        severity = "medium"
                        description = (
                            f"Margin of {job['margin_pct']:.1f}% is {z_margin:.1f} std devs "
                            f"above your fleet average ({mean_m:.1f}%). "
                            f"This route may be an opportunity to replicate."
                        )

                    anomalies.append(Anomaly(
                        job_id=job["job_id"],
                        anomaly_type=anomaly_type,
                        severity=severity,
                        z_score=round(z_margin, 2),
                        actual_value=job["margin_pct"],
                        fleet_mean=round(mean_m, 2),
                        fleet_stddev=round(std_m, 2),
                        description=description,
                        origin=job.get("origin"),
                        destination=job.get("destination"),
                        created_at=job["created_at"],
                    ))

            # ── Cost spike detection (only when actuals available) ───────
            if job["total_cost"] is not None and std_c > 0:
                z_cost = (job["total_cost"] - mean_c) / std_c

                if z_cost > Z_THRESHOLD_COST:
                    anomalies.append(Anomaly(
                        job_id=job["job_id"],
                        anomaly_type="cost_spike",
                        severity="high" if z_cost > 3.5 else "medium",
                        z_score=round(z_cost, 2),
                        actual_value=round(job["total_cost"], 2),
                        fleet_mean=round(mean_c, 2),
                        fleet_stddev=round(std_c, 2),
                        description=(
                            f"Total cost of €{job['total_cost']:.0f} is {z_cost:.1f} std devs above "
                            f"your fleet average (€{mean_c:.0f}). "
                            f"Investigate unexpected fuel, toll, or maintenance costs."
                        ),
                        origin=job.get("origin"),
                        destination=job.get("destination"),
                        created_at=job["created_at"],
                    ))

        # Deduplicate: if same job triggered both margin + cost, keep highest severity
        anomalies = self._deduplicate(anomalies)

        n = len(anomalies)
        high_count = sum(1 for a in anomalies if a.severity == "high")

        summary = (
            f"Scanned {len(recent_jobs)} jobs over the last {days} days. "
            f"Found {n} anomal{'y' if n == 1 else 'ies'}"
            + (f" ({high_count} high severity)." if high_count else ".")
        )

        return AnomalyReport(
            fleet_id=str(fleet_id),
            days_scanned=days,
            n_jobs_scanned=len(recent_jobs),
            n_anomalies=n,
            anomalies=anomalies,
            baseline_jobs_count=n_baseline,
            insufficient_baseline=False,
            summary=summary,
        )

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(anomalies: list[Anomaly]) -> list[Anomaly]:
        """
        If the same job appears more than once (e.g. both margin_outlier and cost_spike),
        keep all entries — they are different anomaly types and both informative.
        Sort by severity (high first) then by abs(z_score).
        """
        return sorted(
            anomalies,
            key=lambda a: (0 if a.severity == "high" else 1, -abs(a.z_score))
        )
