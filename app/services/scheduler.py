"""
app/services/scheduler.py
──────────────────────────
APScheduler setup for trial warnings and expiry notifications.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.repositories.repositories import FleetRepository, UserRepository
from app.repositories.audit_repository import AuditRepository
from app.services.email_service import EmailService
from app.models.audit import AuditEventType

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_email = EmailService()

async def trial_warning_job():
    """Finds tier1 fleets whose trial ends within TRIAL_WARNING_DAYS and sends a warning email."""
    log.info("[Scheduler] Starting trial_warning_job")
    async with AsyncSessionLocal() as db:
        fleet_repo = FleetRepository(db)
        user_repo = UserRepository(db)
        audit_repo = AuditRepository(db)
        
        # Today at 00:00:00 for deduplication check
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        fleets = await fleet_repo.get_trial_expiring_in(settings.TRIAL_WARNING_DAYS)
        for fleet in fleets:
            # Dedup: skip if already sent today
            if await audit_repo.has_event_since(fleet.id, AuditEventType.TRIAL_WARNING_SENT, today_start):
                continue
            
            # Find owner
            owner = await user_repo.get_fleet_owner(fleet.id)
            if not owner:
                log.warning(f"[Scheduler] Fleet {fleet.id} has no owner, skipping warning")
                continue
            
            # Days remaining
            days_left = settings.TRIAL_WARNING_DAYS
            if fleet.trial_ends_at:
                try:
                    days_left = (fleet.trial_ends_at - datetime.now()).days + 1
                except Exception:
                    pass

            # Send email
            log.info(f"[Scheduler] Sending trial warning to {owner.email} for fleet {fleet.id}")
            email_res = await _email.send_trial_expiry_warning(
                to_email=owner.email,
                fleet_name=fleet.name,
                days_remaining=days_left
            )
            
            # Log audit
            if email_res.get("ok"):
                await audit_repo.log(
                    AuditEventType.TRIAL_WARNING_SENT,
                    fleet_id=fleet.id,
                    metadata={"to": owner.email, "days_remaining": days_left}
                )

async def trial_expiry_job():
    """Logs an audit event for fleets whose trial just ended."""
    log.info("[Scheduler] Starting trial_expiry_job")
    async with AsyncSessionLocal() as db:
        fleet_repo = FleetRepository(db)
        audit_repo = AuditRepository(db)
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        fleets = await fleet_repo.get_expired_trials()
        for fleet in fleets:
            # Dedup: only log once per day
            if await audit_repo.has_event_since(fleet.id, AuditEventType.TRIAL_EXPIRED, today_start):
                continue
            
            log.info(f"[Scheduler] Trial EXPIRED for fleet {fleet.id}")
            overdue = 0
            if fleet.trial_ends_at:
                overdue = (datetime.now() - fleet.trial_ends_at).days
            
            await audit_repo.log(
                AuditEventType.TRIAL_EXPIRED,
                fleet_id=fleet.id,
                metadata={"days_overdue": overdue}
            )

def setup_scheduler():
    """Registers jobs with the scheduler."""
    if not settings.SCHEDULER_ENABLED:
        log.info("APScheduler disabled via config.")
        return

    # Trial warning at 08:00 UTC
    scheduler.add_job(
        trial_warning_job,
        CronTrigger(hour=8, minute=0),
        id="trial_warning",
        misfire_grace_time=3600,
        replace_existing=True
    )
    
    # Trial expiry at 08:05 UTC
    scheduler.add_job(
        trial_expiry_job,
        CronTrigger(hour=8, minute=5),
        id="trial_expiry",
        misfire_grace_time=3600,
        replace_existing=True
    )
    
    log.info("APScheduler configured with trial_warning and trial_expiry jobs.")
