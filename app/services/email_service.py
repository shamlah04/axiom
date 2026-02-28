"""
app/services/email_service.py
───────────────────────────────
Phase 4: Transactional email via Resend (https://resend.com).

Why Resend over SendGrid:
  - Simple REST API (no SDK required)
  - Generous free tier (3,000 emails/month)
  - Clean Python usage: just httpx POST
  - Good deliverability for European SaaS

Configuration:
  Set RESEND_API_KEY in environment/.env
  Set EMAIL_FROM in environment/.env (e.g. "Axiom <noreply@axiom.fleet>")

All methods are fire-and-forget friendly:
  Use `asyncio.create_task(email.send_invite(...))` to not block request handlers.
  On failure, logs are written to audit_logs with event_type=email.failed.

Templates are inline for simplicity. Phase 5 can extract to a template engine.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailService:

    def __init__(self):
        self.api_key = getattr(settings, "RESEND_API_KEY", None)
        self.from_addr = getattr(settings, "EMAIL_FROM", "Axiom <noreply@axiom.fleet>")
        self.base_url = getattr(settings, "APP_BASE_URL", "https://app.axiom.fleet")
        self.enabled = bool(self.api_key and self.api_key != "disabled")

    async def _send(self, to: str, subject: str, html: str) -> dict:
        """
        Core send. Returns {"id": "...", "ok": True} on success.
        Returns {"ok": False, "error": "..."} on failure (never raises).
        """
        if not self.enabled:
            log.info(f"[EmailService] DISABLED — would send to {to}: {subject}")
            return {"ok": True, "id": "disabled", "skipped": True}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": self.from_addr,
                        "to": [to],
                        "subject": subject,
                        "html": html,
                    },
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {"ok": True, "id": data.get("id", "unknown")}
                else:
                    log.error(f"[EmailService] Resend error {resp.status_code}: {resp.text}")
                    return {"ok": False, "error": resp.text, "status": resp.status_code}
        except Exception as e:
            log.error(f"[EmailService] Exception sending to {to}: {e}")
            return {"ok": False, "error": str(e)}

    # ── Email Templates ───────────────────────────────────────────────────

    async def send_team_invite(
        self,
        to_email: str,
        fleet_name: str,
        inviter_name: str,
        role: str,
        invite_token: str,
    ) -> dict:
        """
        Invitation email sent when a fleet owner creates a team invite.
        Deep link: {base_url}/accept-invite?token={token}
        """
        accept_url = f"{self.base_url}/accept-invite?token={invite_token}"
        subject = f"{inviter_name} invited you to join {fleet_name} on Axiom"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
            <span style="color: #cbd5e1; font-size: 14px; margin-left: 12px;">Axiom Fleet Intelligence</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid #e2e8f0;">
            <h2 style="margin: 0 0 8px; font-size: 22px;">You've been invited</h2>
            <p style="color: #64748b; margin: 0 0 24px;">
              <strong>{inviter_name}</strong> has invited you to join
              <strong>{fleet_name}</strong> as a <strong>{role}</strong>.
            </p>
            <a href="{accept_url}"
               style="display: inline-block; background: #06b6d4; color: #0f172a;
                      font-weight: 700; padding: 12px 28px; border-radius: 8px;
                      text-decoration: none; font-size: 15px;">
              Accept Invitation
            </a>
            <p style="color: #94a3b8; font-size: 12px; margin: 24px 0 0;">
              This invitation expires in 7 days. If you didn't expect this, ignore it.
              <br>Or copy this link: <code style="font-size: 11px;">{accept_url}</code>
            </p>
          </div>
        </div>
        """
        return await self._send(to_email, subject, html)

    async def send_trial_expiry_warning(
        self,
        to_email: str,
        fleet_name: str,
        days_remaining: int,
    ) -> dict:
        """Sent 3 days before trial ends."""
        upgrade_url = f"{self.base_url}/settings/billing"
        subject = f"Your Axiom trial ends in {days_remaining} day{'s' if days_remaining != 1 else ''}"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid #e2e8f0;">
            <h2 style="margin: 0 0 8px; font-size: 22px;">
              ⏳ {days_remaining} day{'s' if days_remaining != 1 else ''} left on your trial
            </h2>
            <p style="color: #64748b; margin: 0 0 8px;">
              Your free trial for <strong>{fleet_name}</strong> ends soon.
            </p>
            <p style="color: #64748b; margin: 0 0 24px;">
              Upgrade to Growth or Enterprise to keep access to ML predictions,
              the intelligence dashboard, and team management.
            </p>
            <a href="{upgrade_url}"
               style="display: inline-block; background: #06b6d4; color: #0f172a;
                      font-weight: 700; padding: 12px 28px; border-radius: 8px;
                      text-decoration: none; font-size: 15px;">
              Upgrade Now
            </a>
          </div>
        </div>
        """
        return await self._send(to_email, subject, html)

    async def send_tier_upgrade_confirmation(
        self,
        to_email: str,
        fleet_name: str,
        new_tier_label: str,
    ) -> dict:
        """Confirmation email after successful tier upgrade."""
        subject = f"Welcome to {new_tier_label} — {fleet_name}"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid #e2e8f0;">
            <h2 style="margin: 0 0 8px;">✅ You're on {new_tier_label}</h2>
            <p style="color: #64748b; margin: 0 0 24px;">
              <strong>{fleet_name}</strong> has been upgraded to {new_tier_label}.
              Your intelligence dashboard, team invites, and full feature set are now active.
            </p>
            <a href="{self.base_url}/intelligence"
               style="display: inline-block; background: #06b6d4; color: #0f172a;
                      font-weight: 700; padding: 12px 28px; border-radius: 8px;
                      text-decoration: none; font-size: 15px;">
              Open Intelligence Dashboard
            </a>
          </div>
        </div>
        """
        return await self._send(to_email, subject, html)

    async def send_stripe_payment_failed(
        self,
        to_email: str,
        fleet_name: str,
        amount: str,
    ) -> dict:
        """Stripe payment failure notification."""
        subject = f"Payment failed for {fleet_name} — action required"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px; border: 1px solid #e2e8f0;">
            <h2 style="margin: 0 0 8px; color: #ef4444;">⚠️ Payment failed</h2>
            <p style="color: #64748b; margin: 0 0 24px;">
              We couldn't process a payment of <strong>{amount}</strong> for <strong>{fleet_name}</strong>.
              Please update your payment method to avoid service interruption.
            </p>
            <a href="{self.base_url}/settings/billing"
               style="display: inline-block; background: #ef4444; color: #fff;
                      font-weight: 700; padding: 12px 28px; border-radius: 8px;
                      text-decoration: none; font-size: 15px;">
              Update Payment Method
            </a>
          </div>
        </div>
        """
        return await self._send(to_email, subject, html)
