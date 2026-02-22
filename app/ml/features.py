"""
app/ml/features.py
──────────────────
Feature engineering layer for the Axiom ML prediction pipeline.

Transforms raw job + truck + driver inputs into a normalized feature
vector suitable for scikit-learn regression models.

Design contract:
  - Input:  JobFeatureInput  (pure dataclass, no ORM)
  - Output: np.ndarray of shape (1, N_FEATURES)
  - FEATURE_NAMES must stay in sync with the array column order.
    Adding new features = new model version.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

# ---------------------------------------------------------------------------
# Feature names — must match column order in build_feature_vector()
# ---------------------------------------------------------------------------
FEATURE_NAMES: list[str] = [
    # Route
    "distance_km",
    "estimated_duration_hours",
    "km_per_hour",                   # derived: distance / duration
    # Economics
    "offered_rate",
    "rate_per_km",                   # derived: offered_rate / distance_km
    "toll_costs",
    "toll_ratio",                    # derived: toll_costs / offered_rate
    "other_costs",
    # Fuel
    "fuel_price_per_unit",
    "fuel_consumption_per_100km",
    "fuel_cost_raw",                 # derived: distance/100 * consumption * price
    "fuel_cost_ratio",               # derived: fuel_cost_raw / offered_rate
    # Truck fixed costs
    "maintenance_cost_per_km",
    "insurance_monthly",
    "leasing_monthly",
    "fixed_cost_per_km",             # derived: (insurance+leasing) / (22*avg_daily_km)
    # Driver
    "hourly_rate",
    "monthly_fixed_cost",
    "driver_cost_raw",               # derived: hourly_rate * duration
    # Fuel type (one-hot: diesel, electric, hybrid, petrol)
    "fuel_type_diesel",
    "fuel_type_electric",
    "fuel_type_hybrid",
    "fuel_type_petrol",
]

N_FEATURES = len(FEATURE_NAMES)

# Average km per working day assumption for fixed cost amortization
_AVG_DAILY_KM = 350.0
_WORKING_DAYS = 22


@dataclass
class JobFeatureInput:
    """Pure domain object — no ORM dependency."""
    # Route
    distance_km: float
    estimated_duration_hours: float
    # Economics
    offered_rate: float
    toll_costs: float
    other_costs: float
    fuel_price_per_unit: float
    # Truck
    fuel_consumption_per_100km: float
    maintenance_cost_per_km: float
    insurance_monthly: float
    leasing_monthly: float
    fuel_type: str                   # "diesel" | "electric" | "hybrid" | "petrol"
    # Driver
    hourly_rate: float
    monthly_fixed_cost: float


def build_feature_vector(inp: JobFeatureInput) -> np.ndarray:
    """
    Returns a (1, N_FEATURES) float64 array.

    All derived features are computed here to keep the model inputs
    interpretable and to avoid leaking target values.
    """
    d = inp.distance_km
    dur = inp.estimated_duration_hours
    rate = inp.offered_rate

    # Derived — route
    km_per_hour = d / dur if dur > 0 else 0.0

    # Derived — economics
    rate_per_km = rate / d if d > 0 else 0.0
    toll_ratio = inp.toll_costs / rate if rate > 0 else 0.0

    # Derived — fuel
    fuel_cost_raw = (d / 100.0) * inp.fuel_consumption_per_100km * inp.fuel_price_per_unit
    fuel_cost_ratio = fuel_cost_raw / rate if rate > 0 else 0.0

    # Derived — truck fixed costs
    avg_monthly_km = _AVG_DAILY_KM * _WORKING_DAYS
    fixed_monthly = inp.insurance_monthly + inp.leasing_monthly
    fixed_cost_per_km = fixed_monthly / avg_monthly_km if avg_monthly_km > 0 else 0.0

    # Derived — driver
    driver_cost_raw = inp.hourly_rate * dur

    # One-hot fuel type
    ft = inp.fuel_type.lower() if inp.fuel_type else "diesel"
    fuel_type_diesel   = 1.0 if ft == "diesel"   else 0.0
    fuel_type_electric = 1.0 if ft == "electric" else 0.0
    fuel_type_hybrid   = 1.0 if ft == "hybrid"   else 0.0
    fuel_type_petrol   = 1.0 if ft == "petrol"   else 0.0

    vector = [
        d,
        dur,
        km_per_hour,
        rate,
        rate_per_km,
        inp.toll_costs,
        toll_ratio,
        inp.other_costs,
        inp.fuel_price_per_unit,
        inp.fuel_consumption_per_100km,
        fuel_cost_raw,
        fuel_cost_ratio,
        inp.maintenance_cost_per_km,
        inp.insurance_monthly,
        inp.leasing_monthly,
        fixed_cost_per_km,
        inp.hourly_rate,
        inp.monthly_fixed_cost,
        driver_cost_raw,
        fuel_type_diesel,
        fuel_type_electric,
        fuel_type_hybrid,
        fuel_type_petrol,
    ]

    assert len(vector) == N_FEATURES, (
        f"Feature count mismatch: got {len(vector)}, expected {N_FEATURES}"
    )

    return np.array(vector, dtype=np.float64).reshape(1, -1)
