"""
app/services/scheduler.py  — Phase 5 complete
───────────────────────────────────────────────
Scheduled jobs:

  trial_warning_job     08:00 UTC — warns fleets 3 days before trial ends
  trial_expiry_job      08:05 UTC — marks expired trials in audit log
  stale_jobs_cleanup    02:00 UTC — marks old pending jobs as 'expired'   ← NEW
  nightly_model_retrain 03:00 UTC — retrains ML model if enough new data   ← NEW
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.audit import AuditEventType
from app.repositories.audit_repository import AuditRepository
from app.repositories.repositories import FleetRepository, UserRepository
from app.services.email_service import EmailService

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_email = EmailService()


# ─────────────────────────────────────────────────────────────────────────────
# EXISTING JOB 1 — Trial warning
# ─────────────────────────────────────────────────────────────────────────────

async def trial_warning_job():
    """Sends a warning email to fleets whose trial ends within TRIAL_WARNING_DAYS."""
    log.info("[Scheduler] Starting trial_warning_job")
    async with AsyncSessionLocal() as db:
        fleet_repo = FleetRepository(db)
        user_repo  = UserRepository(db)
        audit_repo = AuditRepository(db)

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        fleets = await fleet_repo.get_trial_expiring_in(settings.TRIAL_WARNING_DAYS)
        for fleet in fleets:
            if await audit_repo.has_event_since(fleet.id, AuditEventType.TRIAL_WARNING_SENT, today_start):
                continue

            owner = await user_repo.get_fleet_owner(fleet.id)
            if not owner:
                log.warning(f"[Scheduler] Fleet {fleet.id} has no owner, skipping warning")
                continue

            days_left = settings.TRIAL_WARNING_DAYS
            if fleet.trial_ends_at:
                exp = fleet.trial_ends_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                days_left = max(0, (exp - datetime.now(timezone.utc)).days + 1)

            log.info(f"[Scheduler] Sending trial warning → {owner.email} ({days_left}d left)")
            result = await _email.send_trial_expiry_warning(
                to_email=owner.email,
                fleet_name=fleet.name,
                days_remaining=days_left,
            )
            if result.get("ok"):
                await audit_repo.log(
                    AuditEventType.TRIAL_WARNING_SENT,
                    fleet_id=fleet.id,
                    metadata={"to": owner.email, "days_remaining": days_left},
                )


# ─────────────────────────────────────────────────────────────────────────────
# EXISTING JOB 2 — Trial expiry
# ─────────────────────────────────────────────────────────────────────────────

async def trial_expiry_job():
    """Logs TRIAL_EXPIRED audit event for fleets whose trial has ended."""
    log.info("[Scheduler] Starting trial_expiry_job")
    async with AsyncSessionLocal() as db:
        fleet_repo = FleetRepository(db)
        audit_repo = AuditRepository(db)

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        fleets = await fleet_repo.get_expired_trials()
        for fleet in fleets:
            if await audit_repo.has_event_since(fleet.id, AuditEventType.TRIAL_EXPIRED, today_start):
                continue

            overdue = 0
            if fleet.trial_ends_at:
                exp = fleet.trial_ends_at
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                overdue = max(0, (datetime.now(timezone.utc) - exp).days)

            log.info(f"[Scheduler] Trial EXPIRED for fleet {fleet.id} ({overdue}d overdue)")
            await audit_repo.log(
                AuditEventType.TRIAL_EXPIRED,
                fleet_id=fleet.id,
                metadata={"days_overdue": overdue},
            )


# ─────────────────────────────────────────────────────────────────────────────
# NEW JOB 3 — Stale job cleanup
# ─────────────────────────────────────────────────────────────────────────────

async def stale_jobs_cleanup():
    """
    Marks jobs still in 'pending' status after STALE_JOB_DAYS days as 'expired'.

    Why: Dispatchers sometimes create jobs speculatively and never accept or reject
    them. Old pending jobs pollute dashboards and skew ML training data.

    Safe: only changes status, never deletes rows. Audit event logged per fleet.
    """
    log.info("[Scheduler] Starting stale_jobs_cleanup")
    cutoff_days = settings.STALE_JOB_DAYS  # default 30

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select, update
        from app.models.models import Job, JobStatus

        cutoff = datetime.now(timezone.utc) - timedelta(days=cutoff_days)

        # Find stale pending jobs
        result = await db.execute(
            select(Job).where(
                Job.status == JobStatus.pending,
                Job.created_at < cutoff,
            )
        )
        stale = result.scalars().all()

        if not stale:
            log.info("[Scheduler] stale_jobs_cleanup: no stale jobs found")
            return

        # Group by fleet for audit
        by_fleet: dict = {}
        for job in stale:
            by_fleet.setdefault(str(job.fleet_id), []).append(job)

        # Mark as expired
        stale_ids = [j.id for j in stale]
        await db.execute(
            update(Job)
            .where(Job.id.in_(stale_ids))
            .values(status=JobStatus.expired)
        )
        await db.commit()

        audit_repo = AuditRepository(db)
        for fleet_id_str, jobs in by_fleet.items():
            import uuid
            fleet_id = uuid.UUID(fleet_id_str)
            await audit_repo.log(
                AuditEventType.STALE_JOBS_EXPIRED,
                fleet_id=fleet_id,
                metadata={
                    "count": len(jobs),
                    "cutoff_days": cutoff_days,
                    "job_ids": [str(j.id) for j in jobs[:10]],  # cap at 10 for brevity
                },
            )
            log.info(
                f"[Scheduler] Expired {len(jobs)} stale job(s) for fleet {fleet_id_str}"
            )

        log.info(f"[Scheduler] stale_jobs_cleanup: {len(stale)} jobs expired across {len(by_fleet)} fleet(s)")


# ─────────────────────────────────────────────────────────────────────────────
# NEW JOB 4 — Nightly ML model retraining
# ─────────────────────────────────────────────────────────────────────────────

async def nightly_model_retrain():
    """
    Triggers ML model retraining if the dataset has grown enough since last training.

    Threshold: RETRAIN_MIN_NEW_JOBS new jobs with actuals since last training run.
    If threshold not met, logs a skip event and returns.

    Why nightly: The prediction engine improves as more actual revenue/cost data
    accumulates. Retraining weekly works fine at launch; nightly ensures the model
    stays fresh as job volume grows.

    Safe: the existing model continues serving predictions during retraining.
    The registry is only updated if the new model has better validation metrics.
    """
    log.info("[Scheduler] Starting nightly_model_retrain")

    if not settings.ML_RETRAIN_ENABLED:
        log.info("[Scheduler] ML retraining disabled (ML_RETRAIN_ENABLED=false)")
        return

    try:
        from app.ml.model_registry import registry
        from app.ml.trainer import train_and_register

        current_meta = registry.get_metadata()
        current_version = current_meta.version if current_meta else "none"
        current_samples = current_meta.training_samples if current_meta else 0

        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, func
            from app.models.ml_models import PredictionLog

            # Count jobs with recorded actuals since last training
            result = await db.execute(
                select(func.count(PredictionLog.id)).where(
                    PredictionLog.actual_revenue.isnot(None)
                )
            )
            total_with_actuals = result.scalar() or 0

        new_since_last = total_with_actuals - current_samples
        log.info(
            f"[Scheduler] ML retrain check — current model: {current_version}, "
            f"samples: {current_samples}, new actuals: {new_since_last}"
        )

        if new_since_last < settings.RETRAIN_MIN_NEW_JOBS:
            log.info(
                f"[Scheduler] Skipping retrain — only {new_since_last} new jobs "
                f"(threshold: {settings.RETRAIN_MIN_NEW_JOBS})"
            )
            return

        # Run retraining in a thread pool to avoid blocking the event loop
        log.info("[Scheduler] Threshold met — starting model retraining...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, train_and_register)

        if result and result.get("ok"):
            new_version = result.get("version", "unknown")
            new_r2 = result.get("test_r2", 0.0)
            log.info(
                f"[Scheduler] ✅ Model retrained — version: {new_version}, "
                f"test_r2: {new_r2:.4f}"
            )
            # Hot-reload the new model without restarting
            registry.load_latest()
        else:
            log.warning(f"[Scheduler] Model retraining failed or produced no improvement: {result}")

    except ImportError:
        log.warning("[Scheduler] ML trainer module not available — skipping retrain")
    except Exception as e:
        log.error(f"[Scheduler] nightly_model_retrain error: {e}", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_scheduler():
    """Registers all jobs with the scheduler. Called from app/core/startup.py."""
    if not settings.SCHEDULER_ENABLED:
        log.info("[Scheduler] Disabled via SCHEDULER_ENABLED=false")
        return

    jobs = [
        # (function, cron_kwargs, job_id, description)
        (trial_warning_job,    {"hour": 8,  "minute": 0},  "trial_warning",    "Trial warning emails @ 08:00 UTC"),
        (trial_expiry_job,     {"hour": 8,  "minute": 5},  "trial_expiry",     "Trial expiry audit   @ 08:05 UTC"),
        (stale_jobs_cleanup,   {"hour": 2,  "minute": 0},  "stale_cleanup",    "Stale job cleanup    @ 02:00 UTC"),
        (nightly_model_retrain,{"hour": 3,  "minute": 0},  "model_retrain",    "Nightly ML retrain   @ 03:00 UTC"),
    ]

    for func, cron_kwargs, job_id, description in jobs:
        scheduler.add_job(
            func,
            CronTrigger(**cron_kwargs, timezone="UTC"),
            id=job_id,
            misfire_grace_time=3600,   # allow 1h late start (e.g. after restart)
            replace_existing=True,
            coalesce=True,             # if missed multiple times, run once
        )
        log.info(f"[Scheduler] Registered: {description}")

    log.info(f"[Scheduler] {len(jobs)} jobs configured.")
