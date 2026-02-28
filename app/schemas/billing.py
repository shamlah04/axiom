"""
app/schemas/billing.py
───────────────────────
Pydantic schemas for Phase 4 billing and audit endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


# ── Stripe Checkout ───────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    new_tier: str   # "tier2" | "tier3"


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    portal_url: str


# ── Audit Log ─────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: uuid.UUID
    event_type: str
    actor_user_id: Optional[uuid.UUID]
    subject_id: Optional[str]
    metadata: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int
