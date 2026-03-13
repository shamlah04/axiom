"""
app/services/email_service.py  — Phase 4 + gap-fill
─────────────────────────────────────────────────────
Adds the two missing templates that were called but not implemented:
  • send_welcome()          — sent on user registration
  • send_fleet_created()    — sent when a fleet is first created

All existing templates are preserved unchanged.
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
        self.api_key = settings.RESEND_API_KEY
        self.from_addr = settings.EMAIL_FROM
        self.base_url = settings.APP_BASE_URL
        self.enabled = bool(self.api_key and self.api_key != "disabled")

    async def _send(self, to: str, subject: str, html: str) -> dict:
        """
        Core send — never raises. Returns {"ok": True/False, ...}.
        Fire-and-forget friendly: wrap callers in asyncio.create_task().
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

    # ─────────────────────────────────────────────────────────────────────
    # ① NEW: Welcome email — sent immediately after user registration
    # Called from: app/api/v1/endpoints/auth.py  register()
    # ─────────────────────────────────────────────────────────────────────
    async def send_welcome(
        self,
        to_email: str,
        full_name: str,
    ) -> dict:
        """
        Sent right after POST /auth/register succeeds.
        Introduces the product and points to the onboarding step (create fleet).
        """
        onboard_url = f"{self.base_url}/register"
        subject = "Welcome to Axiom — let's set up your fleet"
        first_name = full_name.split()[0] if full_name else "there"
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
            <span style="color: #cbd5e1; font-size: 14px; margin-left: 12px;">Axiom Fleet Intelligence</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px;
                      border: 1px solid #e2e8f0; border-top: none;">
            <h2 style="margin: 0 0 8px; font-size: 22px; color: #0f172a;">
              Welcome, {first_name} 👋
            </h2>
            <p style="color: #64748b; margin: 0 0 16px; line-height: 1.6;">
              Your Axiom account is ready. The next step is to create your fleet —
              it only takes 30 seconds and unlocks instant profit predictions for every job.
            </p>
            <p style="color: #64748b; margin: 0 0 24px; line-height: 1.6;">
              Your 14-day free trial starts the moment your fleet is created,
              giving you full access to the ML prediction engine, intelligence dashboard,
              and scenario simulator.
            </p>
            <a href="{onboard_url}"
               style="display: inline-block; background: #06b6d4; color: #0f172a;
                      font-weight: 700; padding: 12px 28px; border-radius: 8px;
                      text-decoration: none; font-size: 15px;">
              Create your fleet →
            </a>
            <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #e2e8f0;">
              <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                Questions? Reply to this email — we read every one.
              </p>
            </div>
          </div>
        </div>
        """
        return await self._send(to_email, subject, html)

    # ─────────────────────────────────────────────────────────────────────
    # ② NEW: Fleet created — sent when the fleet is first set up
    # Called from: app/api/v1/endpoints/fleets.py  create_fleet()
    # ─────────────────────────────────────────────────────────────────────
    async def send_fleet_created(
        self,
        to_email: str,
        full_name: str,
        fleet_name: str,
        trial_days: int = 14,
    ) -> dict:
        """
        Sent right after POST /fleets succeeds (fleet onboarding complete).
        Confirms trial start and links to the dashboard + quick-start guide.
        """
        dashboard_url = f"{self.base_url}/dashboard"
        trucks_url = f"{self.base_url}/trucks"
        jobs_url = f"{self.base_url}/jobs/new"
        first_name = full_name.split()[0] if full_name else "there"
        subject = f"Your fleet '{fleet_name}' is live — trial started"
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
            <span style="color: #cbd5e1; font-size: 14px; margin-left: 12px;">Axiom Fleet Intelligence</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px;
                      border: 1px solid #e2e8f0; border-top: none;">
            <h2 style="margin: 0 0 4px; font-size: 22px; color: #0f172a;">
              🚛 {fleet_name} is live
            </h2>
            <p style="color: #06b6d4; font-weight: 600; margin: 0 0 20px; font-size: 14px;">
              Your {trial_days}-day free trial has started
            </p>
            <p style="color: #64748b; margin: 0 0 24px; line-height: 1.6;">
              Hi {first_name}, everything is set up. Here's how to get your first profit prediction
              in under 2 minutes:
            </p>
            <!-- Steps -->
            <div style="background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
                        padding: 20px; margin-bottom: 24px;">
              <div style="display: flex; align-items: flex-start; margin-bottom: 14px;">
                <span style="background: #06b6d4; color: #0f172a; border-radius: 50%;
                             width: 22px; height: 22px; display: inline-flex; align-items: center;
                             justify-content: center; font-weight: 700; font-size: 12px;
                             flex-shrink: 0; margin-right: 12px; margin-top: 1px;">1</span>
                <div>
                  <a href="{trucks_url}" style="color: #0f172a; font-weight: 600;
                     text-decoration: none; font-size: 14px;">Add your first truck & driver</a>
                  <p style="color: #94a3b8; font-size: 12px; margin: 2px 0 0;">
                    Fuel type, consumption, and cost inputs
                  </p>
                </div>
              </div>
              <div style="display: flex; align-items: flex-start;">
                <span style="background: #06b6d4; color: #0f172a; border-radius: 50%;
                             width: 22px; height: 22px; display: inline-flex; align-items: center;
                             justify-content: center; font-weight: 700; font-size: 12px;
                             flex-shrink: 0; margin-right: 12px; margin-top: 1px;">2</span>
                <div>
                  <a href="{jobs_url}" style="color: #0f172a; font-weight: 600;
                     text-decoration: none; font-size: 14px;">Submit your first job</a>
                  <p style="color: #94a3b8; font-size: 12px; margin: 2px 0 0;">
                    Get an instant profit prediction with cost breakdown
                  </p>
                </div>
              </div>
            </div>
            <a href="{dashboard_url}"
               style="display: inline-block; background: #06b6d4; color: #0f172a;
                      font-weight: 700; padding: 12px 28px; border-radius: 8px;
                      text-decoration: none; font-size: 15px;">
              Open dashboard →
            </a>
            <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid #e2e8f0;">
              <p style="color: #94a3b8; font-size: 12px; margin: 0; line-height: 1.6;">
                Trial ends in {trial_days} days. No card required now —
                upgrade anytime from <a href="{self.base_url}/settings/billing"
                style="color: #06b6d4;">Settings → Billing</a>.
              </p>
            </div>
          </div>
        </div>
        """
        return await self._send(to_email, subject, html)

    # ─────────────────────────────────────────────────────────────────────
    # ③ EXISTING (unchanged): Team invite
    # ─────────────────────────────────────────────────────────────────────
    async def send_team_invite(
        self,
        to_email: str,
        fleet_name: str,
        inviter_name: str,
        role: str,
        invite_token: str,
    ) -> dict:
        accept_url = f"{self.base_url}/accept-invite?token={invite_token}"
        subject = f"{inviter_name} invited you to join {fleet_name} on Axiom"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
            <span style="color: #cbd5e1; font-size: 14px; margin-left: 12px;">Axiom Fleet Intelligence</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px;
                      border: 1px solid #e2e8f0; border-top: none;">
            <h2 style="margin: 0 0 8px; font-size: 22px;">You've been invited</h2>
            <p style="color: #64748b; margin: 0 0 8px;">
              <strong>{inviter_name}</strong> has invited you to join
              <strong>{fleet_name}</strong> as a <strong>{role}</strong>.
            </p>
            <p style="color: #64748b; margin: 0 0 24px;">
              Click below to accept and set up your account.
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

    # ─────────────────────────────────────────────────────────────────────
    # ④ EXISTING (unchanged): Trial expiry warning
    # ─────────────────────────────────────────────────────────────────────
    async def send_trial_expiry_warning(
        self,
        to_email: str,
        fleet_name: str,
        days_remaining: int,
    ) -> dict:
        upgrade_url = f"{self.base_url}/settings/billing"
        subject = f"Your Axiom trial ends in {days_remaining} day{'s' if days_remaining != 1 else ''}"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px;
                      border: 1px solid #e2e8f0; border-top: none;">
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

    # ─────────────────────────────────────────────────────────────────────
    # ⑤ EXISTING (unchanged): Tier upgrade confirmation
    # ─────────────────────────────────────────────────────────────────────
    async def send_tier_upgrade_confirmation(
        self,
        to_email: str,
        fleet_name: str,
        new_tier_label: str,
    ) -> dict:
        subject = f"Welcome to {new_tier_label} — {fleet_name}"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px;
                      border: 1px solid #e2e8f0; border-top: none;">
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

    # ─────────────────────────────────────────────────────────────────────
    # ⑥ EXISTING (unchanged): Payment failed
    # ─────────────────────────────────────────────────────────────────────
    async def send_stripe_payment_failed(
        self,
        to_email: str,
        fleet_name: str,
        amount: str,
    ) -> dict:
        subject = f"Payment failed for {fleet_name} — action required"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color: #1e293b;">
          <div style="background: #0f172a; padding: 24px; border-radius: 12px 12px 0 0;">
            <span style="background: #06b6d4; color: #0f172a; font-weight: 900;
                         font-size: 18px; padding: 6px 12px; border-radius: 8px;">A</span>
          </div>
          <div style="background: #f8fafc; padding: 32px; border-radius: 0 0 12px 12px;
                      border: 1px solid #e2e8f0; border-top: none;">
            <h2 style="margin: 0 0 8px; color: #ef4444;">⚠️ Payment failed</h2>
            <p style="color: #64748b; margin: 0 0 24px;">
              We couldn't process a payment of <strong>{amount}</strong> for
              <strong>{fleet_name}</strong>.
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
