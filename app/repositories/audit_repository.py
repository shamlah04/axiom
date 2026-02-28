"""
app/repositories/audit_repository.py
──────────────────────────────────────
Append-only writes + paginated reads for the audit log.

Rule: Never call update() or delete() on AuditLog rows.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, AuditEventType


class AuditRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        event_type: AuditEventType | str,
        *,
        actor_user_id: Optional[uuid.UUID] = None,
        fleet_id: Optional[uuid.UUID] = None,
        subject_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Insert a single audit event. Fire-and-forget pattern:
        callers should not block on audit failures.

        Example:
            await audit.log(
                AuditEventType.MEMBER_INVITED,
                actor_user_id=current_user.id,
                fleet_id=current_user.fleet_id,
                subject_id=invite.email,
                metadata={"role": "dispatcher", "invite_id": str(invite.id)},
            )
        """
        row = AuditLog(
            id=uuid.uuid4(),
            event_type=event_type.value if isinstance(event_type, AuditEventType) else event_type,
            actor_user_id=actor_user_id,
            fleet_id=fleet_id,
            subject_id=str(subject_id) if subject_id else None,
            metadata_=metadata,
            ip_address=ip_address,
        )
        self.db.add(row)
        await self.db.commit()
        return row

    async def list_for_fleet(
        self,
        fleet_id: uuid.UUID,
        *,
        event_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        since: Optional[datetime] = None,
    ) -> list[AuditLog]:
        """
        Paginated audit log for a fleet.
        Sorted most-recent-first.
        """
        q = select(AuditLog).where(AuditLog.fleet_id == fleet_id)
        if event_type:
            q = q.where(AuditLog.event_type == event_type)
        if since:
            q = q.where(AuditLog.created_at >= since)
        q = q.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def count_for_fleet(
        self,
        fleet_id: uuid.UUID,
        event_type: Optional[str] = None,
    ) -> int:
        from sqlalchemy import func
        q = select(func.count(AuditLog.id)).where(AuditLog.fleet_id == fleet_id)
        if event_type:
            q = q.where(AuditLog.event_type == event_type)
        result = await self.db.execute(q)
        return result.scalar() or 0
