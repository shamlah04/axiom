from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.ml.model_registry import registry
from app.models.models import User
from app.repositories.ml_repository import PredictionLogRepository, MLModelVersionRepository

router = APIRouter(prefix="/ml", tags=["ML Health"])


@router.get("/status")
async def get_ml_status():
    """
    Returns the current ML model registry state.
    No auth required — useful for infrastructure health checks.
    """
    if not registry.is_loaded():
        return {
            "status": "fallback",
            "message": "No trained model loaded — using deterministic engine.",
            "model_version": None,
        }

    meta = registry.get_metadata()
    return {
        "status": "active",
        "model_version": meta.version,
        "training_samples": meta.training_samples,
        "train_r2": meta.train_r2,
        "train_rmse": meta.train_rmse,
        "feature_count": len(meta.feature_names),
        "created_at": meta.created_at,
        "description": meta.description,
    }


@router.get("/accuracy")
async def get_prediction_accuracy(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Returns prediction accuracy metrics for the current fleet.
    Only includes jobs where actuals have been recorded.
    """
    log_repo = PredictionLogRepository(db)
    summary = await log_repo.get_accuracy_summary(fleet_id=current_user.fleet_id)
    return {
        "fleet_id": str(current_user.fleet_id),
        **summary,
        "interpretation": _interpret_accuracy(summary),
    }


@router.get("/versions")
async def list_model_versions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Lists all trained ML model versions with their metrics.
    """
    version_repo = MLModelVersionRepository(db)
    versions = await version_repo.list_all()
    return [
        {
            "version": v.version,
            "is_active": v.is_active,
            "training_samples": v.training_samples,
            "train_r2": v.train_r2,
            "train_rmse": v.train_rmse,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ]


def _interpret_accuracy(summary: dict) -> str:
    n = summary.get("n_resolved_predictions", 0)
    if n == 0:
        return "No resolved predictions yet. Record job actuals to enable accuracy tracking."
    mae = summary.get("mae_eur", 0)
    avg_err_pct = abs(summary.get("avg_error_pct", 0))
    if avg_err_pct < 5:
        return f"Excellent accuracy across {n} jobs. Average error < 5%."
    if avg_err_pct < 15:
        return f"Good accuracy across {n} jobs. Average error ~{avg_err_pct:.1f}%."
    return f"Model drift detected across {n} jobs. Consider retraining. Average error {avg_err_pct:.1f}%."
