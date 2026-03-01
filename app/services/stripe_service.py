"""
app/services/stripe_service.py
───────────────────────────────
Phase 4: Stripe Checkout + Billing Portal integration.

Flow:
  1. Fleet owner hits POST /billing/checkout → we create a Stripe Checkout session
  2. User is redirected to Stripe's hosted checkout page
  3. On payment success, Stripe sends a webhook to POST /webhooks/stripe
  4. Webhook verifies signature, upgrades fleet tier, writes audit log, sends email
  5. On cancel/failure, Stripe sends webhook, we write audit log

Why Checkout (not Payment Intents):
  - Checkout handles all card UI, 3DS, SCA compliance
  - No PCI scope for us — Stripe handles card data entirely
  - Supports subscriptions natively

Price IDs:
  Set STRIPE_PRICE_TIER2 and STRIPE_PRICE_TIER3 in .env
  These map to your Stripe dashboard recurring price IDs.

Configuration required in .env:
  STRIPE_SECRET_KEY=sk_live_...
  STRIPE_WEBHOOK_SECRET=whsec_...
  STRIPE_PRICE_TIER2=price_...
  STRIPE_PRICE_TIER3=price_...
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

STRIPE_API_BASE = "https://api.stripe.com/v1"


class StripeService:

    def __init__(self):
        self.secret_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        self.price_tier2 = settings.STRIPE_PRICE_TIER2
        self.price_tier3 = settings.STRIPE_PRICE_TIER3
        self.enabled = bool(self.secret_key and not self.secret_key.startswith("disabled"))
        self.app_url = settings.APP_BASE_URL

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _price_for_tier(self, tier: str) -> Optional[str]:
        if tier == "tier2":
            return self.price_tier2
        if tier == "tier3":
            return self.price_tier3
        return None

    async def create_checkout_session(
        self,
        fleet_id: str,
        fleet_name: str,
        customer_email: str,
        new_tier: str,
    ) -> dict:
        """
        Creates a Stripe Checkout session for a subscription upgrade.

        Returns {"checkout_url": "...", "session_id": "...", "ok": True}
        or {"ok": False, "error": "..."} on failure.

        The checkout_url should be returned to the frontend to redirect the user.
        """
        if not self.enabled:
            # Test/dev mode: return a fake URL
            fake_url = f"{self.app_url}/billing/mock-checkout?fleet_id={fleet_id}&tier={new_tier}"
            log.info(f"[Stripe] DISABLED — mock checkout for fleet {fleet_id} → {new_tier}")
            return {"ok": True, "checkout_url": fake_url, "session_id": "mock_session"}

        price_id = self._price_for_tier(new_tier)
        if not price_id:
            return {"ok": False, "error": f"No price configured for tier '{new_tier}'"}

        # Stripe's API uses form-encoded data
        params = {
            "mode": "subscription",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "customer_email": customer_email,
            "success_url": f"{self.app_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{self.app_url}/settings/billing?cancelled=1",
            # Store fleet_id and new_tier in metadata — retrieved in webhook
            "metadata[fleet_id]": fleet_id,
            "metadata[new_tier]": new_tier,
            "metadata[fleet_name]": fleet_name,
            "subscription_data[metadata][fleet_id]": fleet_id,
            "subscription_data[metadata][new_tier]": new_tier,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{STRIPE_API_BASE}/checkout/sessions",
                    headers=self._headers(),
                    data=params,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "ok": True,
                        "checkout_url": data["url"],
                        "session_id": data["id"],
                    }
                else:
                    log.error(f"[Stripe] Checkout creation failed {resp.status_code}: {resp.text}")
                    return {"ok": False, "error": resp.json().get("error", {}).get("message", resp.text)}
        except Exception as e:
            log.error(f"[Stripe] Exception creating checkout: {e}")
            return {"ok": False, "error": str(e)}

    def verify_webhook_signature(self, payload: bytes, sig_header: str) -> Optional[dict]:
        """
        Verifies Stripe webhook signature using HMAC-SHA256.
        Returns parsed event dict on success, None on failure.

        Stripe's Stripe-Signature header format:
          t=<timestamp>,v1=<hmac_sha256>

        We verify: HMAC-SHA256(webhook_secret, f"{timestamp}.{payload}")
        """
        if not self.webhook_secret:
            log.warning("[Stripe] No webhook secret configured — skipping verification")
            try:
                return json.loads(payload)
            except Exception:
                return None

        try:
            parts = {k: v for k, v in (p.split("=", 1) for p in sig_header.split(","))}
            timestamp = parts.get("t")
            v1_sig = parts.get("v1")

            if not timestamp or not v1_sig:
                log.warning("[Stripe] Malformed signature header")
                return None

            # Replay attack prevention: reject webhooks older than 5 minutes
            if abs(time.time() - int(timestamp)) > 300:
                log.warning(f"[Stripe] Webhook timestamp too old: {timestamp}")
                return None

            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected = hmac.new(
                self.webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(expected, v1_sig):
                log.warning("[Stripe] Signature mismatch")
                return None

            return json.loads(payload)

        except Exception as e:
            log.error(f"[Stripe] Signature verification error: {e}")
            return None

    def parse_subscription_tier(self, event: dict) -> Optional[str]:
        """
        Extracts the target tier from a Stripe event's metadata.
        Works for checkout.session.completed and invoice events.
        """
        try:
            # checkout.session.completed
            metadata = event.get("data", {}).get("object", {}).get("metadata", {})
            tier = metadata.get("new_tier")
            if tier:
                return tier

            # invoice.payment_succeeded → subscription metadata
            subscription = event.get("data", {}).get("object", {}).get("subscription")
            if isinstance(subscription, dict):
                return subscription.get("metadata", {}).get("new_tier")

            return None
        except Exception:
            return None

    async def get_or_create_customer(self, email: str, fleet_id: str, fleet_name: str) -> Optional[str]:
        """
        Finds a Stripe customer by email or creates a new one.
        Returns the Stripe Customer ID.
        """
        if not self.enabled:
            return f"cus_mock_{fleet_id}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 1. Search for existing customer
                search_resp = await client.get(
                    f"{STRIPE_API_BASE}/customers?email={email}",
                    headers=self._headers()
                )
                if search_resp.status_code == 200:
                    data = search_resp.json()
                    customers = data.get("data", [])
                    if customers:
                        return customers[0]["id"]

                # 2. Create if not found
                create_resp = await client.post(
                    f"{STRIPE_API_BASE}/customers",
                    headers=self._headers(),
                    data={
                        "email": email,
                        "name": fleet_name,
                        "metadata[fleet_id]": fleet_id
                    }
                )
                if create_resp.status_code in (200, 201):
                    return create_resp.json().get("id")
                else:
                    log.error(f"[Stripe] Customer creation failed: {create_resp.text}")
                    return None
        except Exception as e:
            log.error(f"[Stripe] Exception in get_or_create_customer: {e}")
            return None

    async def create_portal_session(self, customer_id: str) -> dict:
        """
        Creates a Stripe Customer Portal session.
        Returns {"portal_url": "...", "ok": True} or {"ok": False, "error": "..."}
        """
        if not self.enabled:
            fake_url = f"{self.app_url}/billing/mock-portal?customer_id={customer_id}"
            return {"ok": True, "portal_url": fake_url}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{STRIPE_API_BASE}/billing_portal/sessions",
                    headers=self._headers(),
                    data={
                        "customer": customer_id,
                        "return_url": f"{self.app_url}/settings/billing"
                    }
                )
                if resp.status_code in (200, 201):
                    return {"ok": True, "portal_url": resp.json().get("url")}
                else:
                    log.error(f"[Stripe] Portal session failed: {resp.text}")
                    return {"ok": False, "error": resp.text}
        except Exception as e:
            log.error(f"[Stripe] Exception creating portal session: {e}")
            return {"ok": False, "error": str(e)}
