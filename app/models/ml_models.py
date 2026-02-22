from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MLModelVersion(Base):
    """
    Tracks every trained model version.

    Written by scripts/train_model.py at the end of each training run.
    The 'is_active' flag marks the currently deployed version.
    """
    __tablename__ = "ml_model_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # "v1", "v2"...
    description: Mapped[str] = mapped_column(String(255), default="GradientBoostingRegressor")
    training_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    train_rmse: Mapped[float] = mapped_column(Float, nullable=False)
    train_r2: Mapped[float] = mapped_column(Float, nullable=False)
    test_rmse: Mapped[float] = mapped_column(Float, nullable=True)
    test_r2: Mapped[float] = mapped_column(Float, nullable=True)
    feature_names: Mapped[dict] = mapped_column(JSONB, nullable=False)   # list of feature names
    model_path: Mapped[str] = mapped_column(String(512), nullable=False)  # filesystem path
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    prediction_logs: Mapped[list["PredictionLog"]] = relationship(
        back_populates="model_version",
        cascade="all, delete-orphan",
    )


class PredictionLog(Base):
    """
    Per-job prediction audit log.

    Created when a job is predicted.
    Updated (actual_* fields) when job actuals are recorded via PATCH /jobs/{id}/actual.

    This table drives:
      - Error tracking (predicted vs actual)
      - Model drift detection (Phase 4)
      - Retraining dataset quality assessment
    """
    __tablename__ = "prediction_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    fleet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)  # denormalized for fast queries

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ml_model_versions.id"), nullable=True
    )
    used_ml_model: Mapped[bool] = mapped_column(Boolean, default=False)

    # Prediction snapshot
    predicted_net_profit: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_margin_pct: Mapped[float] = mapped_column(Float, nullable=False)

    # Feature snapshot (JSON) — allows replay and debugging
    features_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Feature importances at prediction time
    feature_importances: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Actuals (filled in when job completes)
    actual_net_profit: Mapped[float] = mapped_column(Float, nullable=True)
    actual_total_cost: Mapped[float] = mapped_column(Float, nullable=True)
    actual_margin_pct: Mapped[float] = mapped_column(Float, nullable=True)

    # Error metrics (computed when actuals arrive)
    profit_error: Mapped[float] = mapped_column(Float, nullable=True)       # actual - predicted
    profit_error_pct: Mapped[float] = mapped_column(Float, nullable=True)   # error / |actual| * 100
    abs_profit_error: Mapped[float] = mapped_column(Float, nullable=True)   # |actual - predicted|

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_prediction_logs_job_id", "job_id"),
        Index("ix_prediction_logs_fleet_id", "fleet_id"),
        Index("ix_prediction_logs_model_version_id", "model_version_id"),
    )

    model_version: Mapped["MLModelVersion"] = relationship(back_populates="prediction_logs")
