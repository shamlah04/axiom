#!/usr/bin/env python
"""
scripts/train_model.py
──────────────────────
Training pipeline for the Axiom profit prediction ML model.

Usage:
    python scripts/train_model.py [--min-samples 50] [--dry-run]

What it does:
  1. Queries all jobs that have actual_cost + actual_revenue recorded.
  2. Builds the feature matrix (JobFeatureInput → build_feature_vector).
  3. Trains a GradientBoostingRegressor on actual net profit.
  4. Evaluates on a holdout split.
  5. Saves the model via MLModelRegistry (bumps version automatically).
  6. Prints a training report.

Retraining strategy:
  - Trigger manually or via the background scheduler (Phase 4).
  - Minimum sample guard: skips training if < --min-samples jobs available.
  - Model versioning: each run saves to models/vN/ (N auto-incremented).
  - The live engine auto-loads the new version after save().

Requirements:
    pip install scikit-learn joblib numpy psycopg2-binary sqlalchemy
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score

from app.core.config import settings
from app.ml.features import JobFeatureInput, build_feature_vector, FEATURE_NAMES
from app.ml.model_registry import MLModelRegistry, ModelMetadata
from app.models.models import Job, Truck, Driver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

async def load_training_data(session: AsyncSession) -> list[dict]:
    """
    Fetch all completed jobs with actuals + their truck/driver configs.
    Returns a list of dicts ready for feature extraction.
    """
    result = await session.execute(
        select(Job, Truck, Driver)
        .join(Truck, Job.truck_id == Truck.id)
        .join(Driver, Job.driver_id == Driver.id)
        .where(
            and_(
                Job.actual_cost.isnot(None),
                Job.actual_revenue.isnot(None),
                Job.status == "completed",
            )
        )
    )
    rows = result.fetchall()
    log.info("Loaded %d training samples from DB", len(rows))

    records = []
    for job, truck, driver in rows:
        actual_net_profit = job.actual_revenue - job.actual_cost
        records.append({
            "feature_input": JobFeatureInput(
                distance_km=job.distance_km,
                estimated_duration_hours=job.estimated_duration_hours,
                offered_rate=job.offered_rate,
                toll_costs=job.toll_costs,
                other_costs=job.other_costs,
                fuel_price_per_unit=job.fuel_price_per_unit,
                fuel_consumption_per_100km=truck.fuel_consumption_per_100km,
                maintenance_cost_per_km=truck.maintenance_cost_per_km,
                insurance_monthly=truck.insurance_monthly,
                leasing_monthly=truck.leasing_monthly or 0.0,
                fuel_type=truck.fuel_type.value,
                hourly_rate=driver.hourly_rate,
                monthly_fixed_cost=driver.monthly_fixed_cost,
            ),
            "actual_net_profit": actual_net_profit,
            "job_id": str(job.id),
        })

    return records


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(records: list[dict], min_samples: int = 50) -> dict:
    """
    Builds feature matrix, trains GBR, returns training report dict.
    """
    if len(records) < min_samples:
        raise ValueError(
            f"Insufficient training data: {len(records)} samples < minimum {min_samples}. "
            f"Record more job actuals before retraining."
        )

    # Build X, y
    X_list = [build_feature_vector(r["feature_input"]).flatten() for r in records]
    y_list = [r["actual_net_profit"] for r in records]

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.float64)

    log.info("Feature matrix shape: %s", X.shape)
    log.info("Target (net_profit) — mean=%.2f, std=%.2f, min=%.2f, max=%.2f",
             y.mean(), y.std(), y.min(), y.max())

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Model
    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_leaf=5,
        random_state=42,
    )
    model.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred_train = model.predict(X_train_scaled)
    y_pred_test = model.predict(X_test_scaled)

    train_rmse = float(np.sqrt(mean_squared_error(y_train, y_pred_train)))
    test_rmse  = float(np.sqrt(mean_squared_error(y_test, y_pred_test)))
    train_r2   = float(r2_score(y_train, y_pred_train))
    test_r2    = float(r2_score(y_test, y_pred_test))

    # Feature importances
    importances = {
        name: float(imp)
        for name, imp in sorted(
            zip(FEATURE_NAMES, model.feature_importances_),
            key=lambda x: -x[1],
        )
    }

    log.info("Train RMSE=%.2f  R²=%.4f", train_rmse, train_r2)
    log.info("Test  RMSE=%.2f  R²=%.4f", test_rmse, test_r2)
    log.info("Top features: %s", list(importances.items())[:5])

    return {
        "model": model,
        "scaler": scaler,
        "train_rmse": train_rmse,
        "test_rmse": test_rmse,
        "train_r2": train_r2,
        "test_r2": test_r2,
        "n_samples": len(records),
        "importances": importances,
    }


# ---------------------------------------------------------------------------
# Version bump
# ---------------------------------------------------------------------------

def next_version(models_dir: Path) -> str:
    if not models_dir.exists():
        return "v1"
    existing = [
        d.name for d in models_dir.iterdir()
        if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit()
    ]
    if not existing:
        return "v1"
    nums = [int(n[1:]) for n in existing]
    return f"v{max(nums) + 1}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(min_samples: int, dry_run: bool):
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        records = await load_training_data(session)

    if not records:
        log.error("No completed jobs with actuals found. Nothing to train on.")
        sys.exit(1)

    result = train(records, min_samples=min_samples)

    if dry_run:
        log.info("[DRY RUN] Would save model. Test R²=%.4f", result["test_r2"])
        print(json.dumps({k: v for k, v in result.items() if k not in ("model", "scaler")}, indent=2))
        return

    from app.ml.model_registry import DEFAULT_MODELS_DIR
    models_dir = DEFAULT_MODELS_DIR
    version = next_version(models_dir)

    meta = ModelMetadata(
        version=version,
        feature_names=FEATURE_NAMES,
        training_samples=result["n_samples"],
        train_rmse=result["train_rmse"],
        train_r2=result["train_r2"],
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    reg = MLModelRegistry(models_dir)
    saved_path = reg.save(result["model"], result["scaler"], meta)

    print("\n✅ Model trained and saved successfully")
    print(f"   Version:   {version}")
    print(f"   Path:      {saved_path}")
    print(f"   Samples:   {result['n_samples']}")
    print(f"   Train R²:  {result['train_r2']:.4f}")
    print(f"   Test  R²:  {result['test_r2']:.4f}")
    print(f"   Test RMSE: {result['test_rmse']:.2f} EUR")
    print("\nTop 5 feature importances:")
    for name, imp in list(result["importances"].items())[:5]:
        print(f"   {name:<35} {imp:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Axiom profit prediction model")
    parser.add_argument("--min-samples", type=int, default=50,
                        help="Minimum completed jobs required for training (default: 50)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run training but do not save the model")
    args = parser.parse_args()
    asyncio.run(main(args.min_samples, args.dry_run))
