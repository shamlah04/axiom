"""
app/schemas/team.py
────────────────────
Pydantic schemas for Phase 3 team + billing endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.team import UserRole, InviteStatus


# ── Team Invites ──────────────────────────────────────────────────────────

class InviteCreate(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.dispatcher


class InviteAccept(BaseModel):
    token: str


class InviteOut(BaseModel):
    id: uuid.UUID
    fleet_id: uuid.UUID
    email: str
    role: str           # UserRole value as string
    status: str         # InviteStatus value as string
    token: str          # Included on creation response so owner can share the invite link
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime]

    model_config = {"from_attributes": True}


class InviteRevoke(BaseModel):
    invite_id: uuid.UUID


# ── Team Members ──────────────────────────────────────────────────────────

class MemberOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str           # UserRole value as string
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberRoleUpdate(BaseModel):
    role: UserRole


# ── Subscription / Plan ───────────────────────────────────────────────────

class PlanLimits(BaseModel):
    max_trucks: int
    max_drivers: int
    max_team_members: int


class PlanUsage(BaseModel):
    trucks: int
    drivers: int


class PlanFeatures(BaseModel):
    intelligence_dashboard: bool
    team_invites: bool
    ml_predictions: bool
    scenario_simulator: bool
    anomaly_detection: bool
    trend_analysis: bool
    cross_fleet_benchmark: bool


class PlanSummary(BaseModel):
    subscription_tier: str
    plan_label: str
    trial_active: bool
    trial_expired: bool
    trial_days_remaining: Optional[int]
    trial_ends_at: Optional[str]
    limits: PlanLimits
    usage: PlanUsage
    features: PlanFeatures


# ── Subscription Upgrade ──────────────────────────────────────────────────

class SubscriptionUpgrade(BaseModel):
    """
    Request to upgrade fleet subscription tier.
    In Phase 3 this is a direct DB update (self-serve).
    Phase 4 will integrate with Stripe webhooks for payment verification.
    """
    new_tier: str  # "tier2" | "tier3"
