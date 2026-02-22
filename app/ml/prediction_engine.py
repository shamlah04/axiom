"""
app/ml/prediction_engine.py
────────────────────────────
ML-backed profit prediction engine for Phase 1.

Strategy:
  1. If a trained model is available in the registry → use it.
  2. If not (cold start / no training data yet) → fall back to the
     deterministic formula engine (no service interruption).

This module REPLACES app/services/prediction_engine.py as the entry
point for job prediction.  The old engine is retained and called as
the fallback — zero refactoring of existing routes required.

Output contract (PredictionOutput) is identical to the existing engine
so that /api/v1/jobs stays unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.ml.features import JobFeatureInput, build_feature_vector, FEATURE_NAMES
from app.ml.model_registry import registry
from app.models.models import RiskLevel, JobRecommendation

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output contract — mirrors existing PredictionOutput
# ---------------------------------------------------------------------------

@dataclass
class MLPredictionOutput:
    # Core prediction
    predicted_net_profit: float
    predicted_total_cost: float
    margin_pct: float
    risk_level: RiskLevel
    recommendation: JobRecommendation
    # Explainability
    feature_importances: dict[str, float]   # feature_name → importance score
    explanation: str
    # Metadata
    model_version: Optional[str]
    used_ml_model: bool                     # False = deterministic fallback


# ---------------------------------------------------------------------------
# Risk / recommendation thresholds
# ---------------------------------------------------------------------------

def _score_risk(margin_pct: float, fuel_ratio: float) -> tuple[RiskLevel, JobRecommendation]:
    if margin_pct < 5.0:
        return RiskLevel.high, JobRecommendation.reject
    if margin_pct < 15.0 or fuel_ratio > 0.50:
        return RiskLevel.medium, JobRecommendation.review
    return RiskLevel.low, JobRecommendation.accept


def _build_explanation(
    margin_pct: float,
    risk: RiskLevel,
    feature_importances: dict[str, float],
    used_ml: bool,
) -> str:
    top = sorted(feature_importances.items(), key=lambda x: -x[1])[:3]
    top_str = ", ".join(f"{k} ({v:.1%})" for k, v in top)
    engine_tag = "ML model" if used_ml else "rule-based engine (no trained model yet)"
    return (
        f"Prediction via {engine_tag}. "
        f"Estimated margin: {margin_pct:.1f}%. "
        f"Risk level: {risk.value}. "
        f"Top cost drivers: {top_str}."
    )


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class MLPredictionEngine:
    """
    Wraps the ML registry.  Falls back to deterministic calculation
    transparently when no model is trained yet.
    """

    def predict(
        self,
        feature_input: JobFeatureInput,
        offered_rate: float,
    ) -> MLPredictionOutput:
        """
        Args:
            feature_input:  Structured input (truck + driver + job fields).
            offered_rate:   What the customer pays (EUR).

        Returns:
            MLPredictionOutput with full explainability.
        """
        if registry.is_loaded():
            return self._ml_predict(feature_input, offered_rate)
        else:
            return self._deterministic_predict(feature_input, offered_rate)

    # ------------------------------------------------------------------
    # ML path
    # ------------------------------------------------------------------

    def _ml_predict(
        self,
        feature_input: JobFeatureInput,
        offered_rate: float,
    ) -> MLPredictionOutput:
        model, scaler, meta = registry.get_active()

        X_raw = build_feature_vector(feature_input)
        X_scaled = scaler.transform(X_raw)

        predicted_net_profit = float(model.predict(X_scaled)[0])
        predicted_total_cost = offered_rate - predicted_net_profit
        margin_pct = (predicted_net_profit / offered_rate * 100.0) if offered_rate > 0 else 0.0

        # Feature importances from tree-based model
        importances = self._get_feature_importances(model)

        # Fuel cost ratio for risk bump
        fuel_cost_raw = float(X_raw[0, FEATURE_NAMES.index("fuel_cost_raw")])
        fuel_ratio = fuel_cost_raw / offered_rate if offered_rate > 0 else 0.0

        risk, rec = _score_risk(margin_pct, fuel_ratio)
        explanation = _build_explanation(margin_pct, risk, importances, used_ml=True)

        return MLPredictionOutput(
            predicted_net_profit=predicted_net_profit,
            predicted_total_cost=predicted_total_cost,
            margin_pct=margin_pct,
            risk_level=risk,
            recommendation=rec,
            feature_importances=importances,
            explanation=explanation,
            model_version=meta.version,
            used_ml_model=True,
        )

    # ------------------------------------------------------------------
    # Deterministic fallback path
    # ------------------------------------------------------------------

    def _deterministic_predict(
        self,
        feature_input: JobFeatureInput,
        offered_rate: float,
    ) -> MLPredictionOutput:
        """
        Replicates the formula from the original prediction_engine.py so
        this engine is a drop-in replacement even before training.
        """
        fi = feature_input
        d = fi.distance_km
        dur = fi.estimated_duration_hours

        fuel_cost = (d / 100.0) * fi.fuel_consumption_per_100km * fi.fuel_price_per_unit
        driver_cost = fi.hourly_rate * dur + fi.monthly_fixed_cost / (22 * 8)
        maintenance_cost = d * fi.maintenance_cost_per_km
        avg_monthly_km = 350.0 * 22
        fixed_allocation = (
            (fi.insurance_monthly + fi.leasing_monthly) / avg_monthly_km * d
        )
        total_cost = fuel_cost + driver_cost + maintenance_cost + fi.toll_costs + fixed_allocation + fi.other_costs
        net_profit = offered_rate - total_cost
        margin_pct = (net_profit / offered_rate * 100.0) if offered_rate > 0 else 0.0

        fuel_ratio = fuel_cost / offered_rate if offered_rate > 0 else 0.0
        risk, rec = _score_risk(margin_pct, fuel_ratio)

        # Build pseudo importances for deterministic path
        importances = {
            "fuel_cost_raw": fuel_cost / total_cost if total_cost > 0 else 0.0,
            "driver_cost_raw": driver_cost / total_cost if total_cost > 0 else 0.0,
            "maintenance_cost_per_km": maintenance_cost / total_cost if total_cost > 0 else 0.0,
        }
        explanation = _build_explanation(margin_pct, risk, importances, used_ml=False)

        return MLPredictionOutput(
            predicted_net_profit=net_profit,
            predicted_total_cost=total_cost,
            margin_pct=margin_pct,
            risk_level=risk,
            recommendation=rec,
            feature_importances=importances,
            explanation=explanation,
            model_version=None,
            used_ml_model=False,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_feature_importances(self, model) -> dict[str, float]:
        """Extract normalized feature importances from sklearn tree models."""
        try:
            raw = model.feature_importances_
            total = raw.sum()
            if total == 0:
                return {name: 0.0 for name in FEATURE_NAMES}
            normalized = raw / total
            return {name: float(v) for name, v in zip(FEATURE_NAMES, normalized)}
        except AttributeError:
            # Model doesn't expose feature_importances_ (e.g. linear)
            return {name: 1.0 / len(FEATURE_NAMES) for name in FEATURE_NAMES}


# Module-level singleton
ml_engine = MLPredictionEngine()
