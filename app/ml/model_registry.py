"""
app/ml/model_registry.py
────────────────────────
Handles serialization, versioning, and hot-loading of trained ML models.

Storage layout (local filesystem, swap for S3 in production):
  models/
    v1/
      model.joblib       ← trained GradientBoostingRegressor (profit prediction)
      scaler.joblib      ← StandardScaler fitted on training data
      metadata.json      ← version, feature names, training stats, created_at

The registry loads the latest active model at startup and caches it in
memory.  Retraining writes a new version directory without touching the
running instance — a reload endpoint swaps it in.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
from sklearn.base import BaseEstimator
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_NAMES

log = logging.getLogger(__name__)

# Default storage directory — override via ML_MODELS_DIR env var
DEFAULT_MODELS_DIR = Path(os.getenv("ML_MODELS_DIR", "models"))


@dataclass
class ModelMetadata:
    version: str
    feature_names: list[str]
    training_samples: int
    train_rmse: float
    train_r2: float
    created_at: str
    test_rmse: Optional[float] = None
    test_r2: Optional[float] = None
    description: str = "GradientBoostingRegressor — net_profit prediction"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ModelMetadata":
        return cls(**d)


class MLModelRegistry:
    """
    Singleton-style registry loaded at application startup.

    Usage:
        registry = MLModelRegistry()
        model, scaler, meta = registry.load_latest()
        X = build_feature_vector(inp)
        prediction = model.predict(scaler.transform(X))[0]
    """

    def __init__(self, models_dir: Path = DEFAULT_MODELS_DIR):
        self.models_dir = models_dir
        self._model: Optional[BaseEstimator] = None
        self._scaler: Optional[StandardScaler] = None
        self._meta: Optional[ModelMetadata] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_loaded(self) -> bool:
        return self._model is not None

    def get_active(self) -> tuple[BaseEstimator, StandardScaler, ModelMetadata]:
        if not self.is_loaded():
            raise RuntimeError(
                "No ML model loaded. Run the training script first: "
                "python scripts/train_model.py"
            )
        return self._model, self._scaler, self._meta

    def load_latest(self) -> bool:
        """
        Discovers and loads the highest-versioned model directory.
        Returns True if successfully loaded, False if no models exist yet.
        """
        version_dir = self._find_latest_version_dir()
        if version_dir is None:
            log.warning("No trained model found in %s — falling back to deterministic engine.", self.models_dir)
            return False

        try:
            self._model = joblib.load(version_dir / "model.joblib")
            self._scaler = joblib.load(version_dir / "scaler.joblib")
            with open(version_dir / "metadata.json") as f:
                self._meta = ModelMetadata.from_dict(json.load(f))
            log.info("Loaded ML model version=%s from %s", self._meta.version, version_dir)
            return True
        except Exception as exc:
            log.error("Failed to load model from %s: %s", version_dir, exc)
            return False

    def save(
        self,
        model: BaseEstimator,
        scaler: StandardScaler,
        metadata: ModelMetadata,
    ) -> Path:
        """Persists a newly trained model to a versioned directory."""
        version_dir = self.models_dir / metadata.version
        version_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(model, version_dir / "model.joblib")
        joblib.dump(scaler, version_dir / "scaler.joblib")
        with open(version_dir / "metadata.json", "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Hot-swap the active model
        self._model = model
        self._scaler = scaler
        self._meta = metadata

        log.info("Saved and activated model version=%s", metadata.version)
        return version_dir

    def get_metadata(self) -> Optional[ModelMetadata]:
        return self._meta

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_latest_version_dir(self) -> Optional[Path]:
        if not self.models_dir.exists():
            return None
        candidates = [
            d for d in self.models_dir.iterdir()
            if d.is_dir() and (d / "model.joblib").exists()
        ]
        if not candidates:
            return None
        # Sort by directory name (e.g. "v1", "v2", "v10") numerically
        def _version_key(p: Path) -> int:
            name = p.name.lstrip("v")
            return int(name) if name.isdigit() else 0

        return sorted(candidates, key=_version_key)[-1]


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
registry = MLModelRegistry()
