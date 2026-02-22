"""
app/services/trends.py
──────────────────────
Profitability trend detection service.

Algorithm:
  1. Fetch weekly avg_margin_pct series (last N weeks)
  2. Run ordinary least squares on (week_index → margin) to get slope
  3. Classify: declining / flat / improving based on slope threshold
  4. Emit alert if slope is persistently negative

Why OLS instead of ML?
  Trend detection on weekly aggregates is a statistics problem, not a
  prediction problem. OLS gives an interpretable slope with a confidence
  signal (R²). No dependencies beyond numpy.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.repositories.intelligence_repository import IntelligenceRepository, MIN_JOBS_FOR_TREND

# Slope thresholds (% margin change per week)
SLOPE_DECLINING  = -0.3   # < -0.3%/week for multiple weeks → declining
SLOPE_IMPROVING  =  0.3   # >  0.3%/week → improving
MIN_WEEKS_FOR_SIGNAL = 4  # need at least 4 data points for a meaningful slope
MIN_R2_FOR_CONFIDENCE = 0.35  # R² threshold: above this = "high" confidence


@dataclass
class TrendDataPoint:
    week_start: str
    avg_margin_pct: float
    job_count: int
    weekly_revenue: float


@dataclass
class TrendResult:
    trend: str                          # "improving" | "flat" | "declining"
    slope_pct_per_week: Optional[float] # OLS slope (margin change per week)
    r2: Optional[float]                 # goodness of fit (0-1)
    confidence: str                     # "high" | "medium" | "low" | "insufficient_data"
    alert: bool                         # True if actionable signal detected
    alert_message: Optional[str]
    weeks_analyzed: int
    data_points: list[TrendDataPoint]
    summary: str


class TrendDetectionService:
    """
    Computes profitability trend for a fleet over the last N weeks.
    Called by GET /api/v1/intelligence/trends
    """

    def __init__(self, repo: IntelligenceRepository):
        self.repo = repo

    async def detect(
        self,
        fleet_id: uuid.UUID,
        weeks: int = 12,
    ) -> TrendResult:

        raw = await self.repo.weekly_margin_series(fleet_id, weeks=weeks)

        # Filter weeks with too few jobs to be meaningful
        filtered = [r for r in raw if r["job_count"] >= MIN_JOBS_FOR_TREND]

        data_points = [
            TrendDataPoint(
                week_start=r["week_start"],
                avg_margin_pct=r["avg_margin_pct"],
                job_count=r["job_count"],
                weekly_revenue=r["weekly_revenue"],
            )
            for r in filtered
        ]

        if len(data_points) < MIN_WEEKS_FOR_SIGNAL:
            return TrendResult(
                trend="unknown",
                slope_pct_per_week=None,
                r2=None,
                confidence="insufficient_data",
                alert=False,
                alert_message=None,
                weeks_analyzed=len(data_points),
                data_points=data_points,
                summary=(
                    f"Only {len(data_points)} weeks with enough jobs — need at least "
                    f"{MIN_WEEKS_FOR_SIGNAL} for a reliable trend signal."
                ),
            )

        # OLS
        y = np.array([d.avg_margin_pct for d in data_points])
        x = np.arange(len(y), dtype=float)

        slope, intercept = np.polyfit(x, y, 1)
        y_pred = slope * x + intercept
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        slope = round(float(slope), 3)
        r2 = round(r2, 3)

        # Classify
        if slope < SLOPE_DECLINING:
            trend = "declining"
        elif slope > SLOPE_IMPROVING:
            trend = "improving"
        else:
            trend = "flat"

        # Confidence
        if r2 >= MIN_R2_FOR_CONFIDENCE and len(data_points) >= 8:
            confidence = "high"
        elif r2 >= 0.15 or len(data_points) >= MIN_WEEKS_FOR_SIGNAL:
            confidence = "medium"
        else:
            confidence = "low"

        # Alert logic
        alert = False
        alert_message = None
        latest_margin = data_points[-1].avg_margin_pct if data_points else 0.0

        if trend == "declining" and confidence in ("high", "medium"):
            alert = True
            alert_message = (
                f"Margin declining at {abs(slope):.2f}%/week. "
                f"Current avg: {latest_margin:.1f}%. "
                "Review job acceptance criteria or cost structure."
            )
        elif trend == "improving" and confidence == "high":
            alert_message = f"Strong margin improvement: +{slope:.2f}%/week over {len(data_points)} weeks."

        # Summary
        direction_word = {"improving": "improving ↑", "declining": "declining ↓", "flat": "stable →"}.get(trend, "unknown")
        summary = (
            f"Profitability trend: {direction_word}. "
            f"Slope: {slope:+.2f}%/week over {len(data_points)} weeks (R²={r2:.2f})."
        )

        return TrendResult(
            trend=trend,
            slope_pct_per_week=slope,
            r2=r2,
            confidence=confidence,
            alert=alert,
            alert_message=alert_message,
            weeks_analyzed=len(data_points),
            data_points=data_points,
            summary=summary,
        )
