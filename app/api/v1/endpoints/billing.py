"""
app/api/v1/endpoints/billing.py
────────────────────────────────
Phase 4: Stripe Checkout + Webhook handler.

Routes:
  POST /billing/checkout          — Create Stripe Checkout session (authenticated)
  POST /webhooks/stripe           — Stripe webhook receiver (no auth — uses sig verification)
  GET  /billing/audit             — Paginated audit log for the fleet (owner only)

Stripe event handling:
  checkout.session.completed      → upgrade fleet tier, send confirmation email
  invoice.payment_failed          → send failure email, write audit log
  customer.subscription.deleted  → downgrade to tier1, write audit log
"""

from __future__ import annotations

import uuid
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.core.roles import require_owner
from app.core.tier_limits import build_plan_summary, get_limits
from app.models.models import User, SubscriptionTier
from app.models.audit import AuditEventType
from app.repositories.repositories import FleetRepository, UserRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    AuditLogOut,
    AuditLogPage,
)
from app.services.stripe_service import StripeService
from app.services.email_service import EmailService

log = logging.getLogger(__name__)

router = APIRouter(tags=["Billing"])
webhook_router = APIRouter(tags=["Webhooks"])

_stripe = StripeService()
_email = EmailService()


# ─────────────────────────────────────────────────────────────────────────
# Checkout — create Stripe session
# ─────────────────────────────────────────────────────────────────────────

@router.post(
    "/billing/checkout",
    response_model=CheckoutResponse,
    dependencies=[Depends(require_owner)],
)
async def create_checkout(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Creates a Stripe Checkout session for upgrading to tier2 or tier3.

    Returns a `checkout_url` — the frontend redirects the user here.
    On payment success, Stripe calls our webhook which upgrades the tier.

    Note: POST /fleets/me/upgrade still works for direct upgrades (e.g. internal/testing).
    This endpoint provides the production Stripe-verified path.
    """
    valid_tiers = {"tier2", "tier3"}
    if payload.new_tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be tier2 or tier3.")

    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get(current_user.fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")

    tier_order = {SubscriptionTier.tier1: 1, SubscriptionTier.tier2: 2, SubscriptionTier.tier3: 3}
    target = SubscriptionTier(payload.new_tier)
    if tier_order[target] <= tier_order[fleet.subscription_tier]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot downgrade or stay at current tier ({fleet.subscription_tier.value})."
        )

    result = await _stripe.create_checkout_session(
        fleet_id=str(current_user.fleet_id),
        fleet_name=fleet.name,
        customer_email=current_user.email,
        new_tier=payload.new_tier,
    )

    if not result["ok"]:
        raise HTTPException(status_code=502, detail=f"Stripe error: {result.get('error')}")

    # Audit log
    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.STRIPE_CHECKOUT_CREATED,
        actor_user_id=current_user.id,
        fleet_id=current_user.fleet_id,
        metadata={
            "new_tier": payload.new_tier,
            "session_id": result["session_id"],
        },
    )

    return CheckoutResponse(
        checkout_url=result["checkout_url"],
        session_id=result["session_id"],
    )


# ─────────────────────────────────────────────────────────────────────────
# Stripe Webhook
# ─────────────────────────────────────────────────────────────────────────

@webhook_router.post("/webhooks/stripe", status_code=200)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Stripe webhook receiver. Must be unauthenticated — Stripe calls this directly.
    Signature verification replaces auth.

    Register this URL in your Stripe dashboard:
      https://your-domain.com/webhooks/stripe

    Enable events:
      checkout.session.completed
      invoice.payment_failed
      customer.subscription.deleted
    """
    body = await request.body()

    if not stripe_signature:
        log.warning("[Webhook] Missing Stripe-Signature header")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    event = _stripe.verify_webhook_signature(body, stripe_signature)
    if not event:
        log.warning("[Webhook] Signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event.get("type", "")
    event_object = event.get("data", {}).get("object", {})

    log.info(f"[Webhook] Received event: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_success(event_object, db)

        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(event_object, db)

        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_cancelled(event_object, db)

        else:
            log.info(f"[Webhook] Unhandled event type: {event_type}")

    except Exception as e:
        # Never let webhook handler exceptions return non-200 to Stripe
        # Stripe would retry indefinitely on 5xx
        log.error(f"[Webhook] Handler error for {event_type}: {e}", exc_info=True)

    # Always return 200 so Stripe doesn't retry
    return {"received": True}


async def _handle_checkout_success(session: dict, db: AsyncSession) -> None:
    """
    checkout.session.completed: upgrade fleet tier.
    """
    metadata = session.get("metadata", {})
    fleet_id_str = metadata.get("fleet_id")
    new_tier_str = metadata.get("new_tier")
    fleet_name = metadata.get("fleet_name", "your fleet")
    customer_email = session.get("customer_email")

    if not fleet_id_str or not new_tier_str:
        log.error(f"[Webhook] checkout.session.completed missing metadata: {metadata}")
        return

    try:
        fleet_id = uuid.UUID(fleet_id_str)
    except ValueError:
        log.error(f"[Webhook] Invalid fleet_id in metadata: {fleet_id_str}")
        return

    valid_tiers = {"tier2": SubscriptionTier.tier2, "tier3": SubscriptionTier.tier3}
    new_tier = valid_tiers.get(new_tier_str)
    if not new_tier:
        log.error(f"[Webhook] Invalid tier in metadata: {new_tier_str}")
        return

    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get(fleet_id)
    if not fleet:
        log.error(f"[Webhook] Fleet not found: {fleet_id}")
        return

    # Idempotency: skip if already at this tier or higher
    tier_order = {SubscriptionTier.tier1: 1, SubscriptionTier.tier2: 2, SubscriptionTier.tier3: 3}
    if tier_order.get(fleet.subscription_tier, 0) >= tier_order[new_tier]:
        log.info(f"[Webhook] Fleet {fleet_id} already at {fleet.subscription_tier.value}, skipping upgrade")
        return

    old_tier = fleet.subscription_tier.value
    fleet.subscription_tier = new_tier
    fleet.trial_ends_at = None
    await db.commit()
    await db.refresh(fleet)

    log.info(f"[Webhook] Fleet {fleet_id} upgraded {old_tier} → {new_tier_str}")

    # Audit log
    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.STRIPE_PAYMENT_SUCCESS,
        fleet_id=fleet_id,
        metadata={
            "old_tier": old_tier,
            "new_tier": new_tier_str,
            "stripe_session_id": session.get("id"),
            "customer_email": customer_email,
        },
    )
    await audit.log(
        AuditEventType.TIER_UPGRADED,
        fleet_id=fleet_id,
        metadata={"from": old_tier, "to": new_tier_str, "via": "stripe"},
    )

    # Send confirmation email (non-blocking)
    if customer_email:
        tier_label = get_limits(new_tier)["label"]
        asyncio.create_task(
            _email.send_tier_upgrade_confirmation(
                to_email=customer_email,
                fleet_name=fleet_name,
                new_tier_label=tier_label,
            )
        )


async def _handle_payment_failed(invoice: dict, db: AsyncSession) -> None:
    """invoice.payment_failed: send alert email."""
    subscription = invoice.get("subscription")
    customer_email = invoice.get("customer_email")
    amount_due = invoice.get("amount_due", 0)
    currency = invoice.get("currency", "eur").upper()
    amount_str = f"{currency} {amount_due / 100:.2f}"

    # Try to find fleet via subscription metadata
    fleet_id = None
    fleet_name = "your fleet"

    if isinstance(subscription, dict):
        fleet_id_str = subscription.get("metadata", {}).get("fleet_id")
        if fleet_id_str:
            try:
                fleet_id = uuid.UUID(fleet_id_str)
                fleet_repo = FleetRepository(db)
                fleet = await fleet_repo.get(fleet_id)
                if fleet:
                    fleet_name = fleet.name
            except ValueError:
                pass

    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.STRIPE_PAYMENT_FAILED,
        fleet_id=fleet_id,
        metadata={
            "amount": amount_str,
            "customer_email": customer_email,
            "invoice_id": invoice.get("id"),
        },
    )

    if customer_email:
        asyncio.create_task(
            _email.send_stripe_payment_failed(
                to_email=customer_email,
                fleet_name=fleet_name,
                amount=amount_str,
            )
        )


async def _handle_subscription_cancelled(subscription: dict, db: AsyncSession) -> None:
    """customer.subscription.deleted: downgrade to tier1."""
    fleet_id_str = subscription.get("metadata", {}).get("fleet_id")
    if not fleet_id_str:
        log.warning("[Webhook] subscription.deleted missing fleet_id in metadata")
        return

    try:
        fleet_id = uuid.UUID(fleet_id_str)
    except ValueError:
        return

    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get(fleet_id)
    if not fleet:
        return

    old_tier = fleet.subscription_tier.value
    fleet.subscription_tier = SubscriptionTier.tier1
    await db.commit()

    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.STRIPE_SUBSCRIPTION_CANCELLED,
        fleet_id=fleet_id,
        metadata={
            "old_tier": old_tier,
            "new_tier": "tier1",
            "stripe_subscription_id": subscription.get("id"),
        },
    )

    log.info(f"[Webhook] Fleet {fleet_id} subscription cancelled, downgraded to tier1")


# ─────────────────────────────────────────────────────────────────────────
# Audit Log — Read
# ─────────────────────────────────────────────────────────────────────────

@router.get(
    "/billing/audit",
    response_model=AuditLogPage,
    dependencies=[Depends(require_owner)],
)
async def get_audit_log(
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Paginated audit log for the fleet. Owner only.
    Shows billing events, team events, and high-value job actions.
    """
    audit = AuditRepository(db)
    rows = await audit.list_for_fleet(
        current_user.fleet_id,
        event_type=event_type,
        limit=min(limit, 100),
        offset=offset,
    )
    total = await audit.count_for_fleet(current_user.fleet_id, event_type=event_type)

    return AuditLogPage(
        items=[
            AuditLogOut(
                id=r.id,
                event_type=r.event_type,
                actor_user_id=r.actor_user_id,
                subject_id=r.subject_id,
                metadata=r.metadata_,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
