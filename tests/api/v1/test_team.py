"""
tests/api/v1/test_team.py
──────────────────────────
Integration tests for Phase 3 — Team Management & Subscription.

Coverage:
  - GET /team/members
  - PATCH /team/members/{id}/role
  - DELETE /team/members/{id}
  - POST /team/invites (tier gate, seat limit, owner-only)
  - GET /team/invites
  - DELETE /team/invites/{id}
  - POST /team/invites/accept
  - GET /fleets/me/plan
  - POST /fleets/me/upgrade
  - Intelligence endpoints return 403 for tier1
  - Intelligence endpoints pass for tier2+
"""

import pytest
import uuid
from httpx import AsyncClient
from app.core.config import settings

API = settings.API_V1_PREFIX


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

async def _create_user_with_fleet(
    client: AsyncClient,
    email: str,
    password: str = "password123",
    tier: str = "tier1",
) -> dict:
    """Register, login, create fleet. Returns auth headers."""
    await client.post(f"{API}/auth/register", json={
        "email": email, "password": password, "full_name": "Test User"
    })
    res = await client.post(f"{API}/auth/login", data={"username": email, "password": password})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(f"{API}/fleets", headers=headers, json={
        "name": f"Fleet-{email[:6]}", "country": "DK", "subscription_tier": tier
    })
    return headers


async def _create_bare_user(client: AsyncClient, email: str, password: str = "password123") -> dict:
    """Register and login but NO fleet. Returns headers."""
    await client.post(f"{API}/auth/register", json={
        "email": email, "password": password, "full_name": "Bare User"
    })
    res = await client.post(f"{API}/auth/login", data={"username": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────
# Plan Summary Tests
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_plan_summary_tier1(client: AsyncClient):
    """Plan summary correctly reflects tier1 limits and features."""
    email = f"plan1_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier1")

    res = await client.get(f"{API}/fleets/me/plan", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["subscription_tier"] == "tier1"
    assert data["limits"]["max_trucks"] == 2
    assert data["limits"]["max_team_members"] == 1
    assert data["features"]["intelligence_dashboard"] is False
    assert data["features"]["team_invites"] is False
    assert data["features"]["ml_predictions"] is True   # all tiers


@pytest.mark.asyncio
async def test_plan_summary_tier2(client: AsyncClient):
    """Plan summary correctly reflects tier2 features."""
    email = f"plan2_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier2")

    res = await client.get(f"{API}/fleets/me/plan", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["subscription_tier"] == "tier2"
    assert data["limits"]["max_trucks"] == 10
    assert data["features"]["intelligence_dashboard"] is True
    assert data["features"]["team_invites"] is True


@pytest.mark.asyncio
async def test_upgrade_tier1_to_tier2(client: AsyncClient):
    """Fleet owner can upgrade from tier1 to tier2."""
    email = f"upgrade_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier1")

    res = await client.post(
        f"{API}/fleets/me/upgrade", headers=headers,
        json={"new_tier": "tier2"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["subscription_tier"] == "tier2"
    assert data["features"]["intelligence_dashboard"] is True


@pytest.mark.asyncio
async def test_upgrade_rejects_downgrade(client: AsyncClient):
    """Cannot downgrade subscription tier."""
    email = f"downgrade_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier2")

    res = await client.post(
        f"{API}/fleets/me/upgrade", headers=headers,
        json={"new_tier": "tier1"}
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_upgrade_rejects_invalid_tier(client: AsyncClient):
    """Invalid tier name rejected."""
    email = f"badtier_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier1")

    res = await client.post(
        f"{API}/fleets/me/upgrade", headers=headers,
        json={"new_tier": "tier99"}
    )
    assert res.status_code == 400


# ─────────────────────────────────────────────────────────────────────────
# Intelligence Tier Gate Tests
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_intelligence_blocked_for_tier1(client: AsyncClient):
    """tier1 users cannot access intelligence endpoints."""
    email = f"intel1_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier1")

    for endpoint in ["/intelligence/benchmark", "/intelligence/trends", "/intelligence/anomalies", "/intelligence/summary"]:
        res = await client.get(f"{API}{endpoint}", headers=headers)
        assert res.status_code == 403, f"Expected 403 for tier1 on {endpoint}, got {res.status_code}"
        assert res.json()["detail"]["error"] == "tier_required"


@pytest.mark.asyncio
async def test_intelligence_accessible_for_tier2(client: AsyncClient):
    """tier2 users can access all intelligence endpoints."""
    email = f"intel2_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier2")

    for endpoint in ["/intelligence/benchmark", "/intelligence/trends", "/intelligence/anomalies", "/intelligence/summary"]:
        res = await client.get(f"{API}{endpoint}", headers=headers)
        assert res.status_code == 200, f"Expected 200 for tier2 on {endpoint}, got {res.status_code}"


# ─────────────────────────────────────────────────────────────────────────
# Team Members Tests
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_members_shows_owner(client: AsyncClient):
    """Fleet owner appears in member list with owner role."""
    email = f"member_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier2")

    res = await client.get(f"{API}/team/members", headers=headers)
    assert res.status_code == 200
    members = res.json()
    assert len(members) == 1
    assert members[0]["email"] == email
    assert members[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_cannot_remove_self(client: AsyncClient):
    """Owner cannot remove themselves from fleet."""
    email = f"self_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier2")

    # Get own user id
    me_res = await client.get(f"{API}/auth/me", headers=headers)
    my_id = me_res.json()["id"]

    res = await client.delete(f"{API}/team/members/{my_id}", headers=headers)
    assert res.status_code == 400


# ─────────────────────────────────────────────────────────────────────────
# Invite Tests
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_blocked_for_tier1(client: AsyncClient):
    """tier1 fleet cannot send invites."""
    email = f"inv1_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier1")

    res = await client.post(f"{API}/team/invites", headers=headers, json={
        "email": "newuser@test.com", "role": "dispatcher"
    })
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_invite_create_and_list(client: AsyncClient):
    """Owner on tier2 can create invite and see it in the list."""
    email = f"inv2_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier2")

    invite_email = f"invite_target_{uuid.uuid4().hex[:6]}@test.com"
    res = await client.post(f"{API}/team/invites", headers=headers, json={
        "email": invite_email, "role": "dispatcher"
    })
    assert res.status_code == 201
    invite_data = res.json()
    assert invite_data["email"] == invite_email
    assert invite_data["role"] == "dispatcher"
    assert invite_data["status"] == "pending"

    # Check it appears in list
    list_res = await client.get(f"{API}/team/invites", headers=headers)
    assert list_res.status_code == 200
    invites = list_res.json()
    assert any(i["email"] == invite_email for i in invites)


@pytest.mark.asyncio
async def test_invite_owner_role_rejected(client: AsyncClient):
    """Cannot invite someone with the owner role directly."""
    email = f"invown_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier2")

    res = await client.post(f"{API}/team/invites", headers=headers, json={
        "email": "newowner@test.com", "role": "owner"
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_invite_accept_flow(client: AsyncClient):
    """Full invite → accept flow works correctly."""
    # Owner creates fleet and invite
    owner_email = f"owner_{uuid.uuid4().hex[:6]}@test.com"
    owner_headers = await _create_user_with_fleet(client, owner_email, tier="tier2")

    invitee_email = f"invitee_{uuid.uuid4().hex[:6]}@test.com"
    inv_res = await client.post(f"{API}/team/invites", headers=owner_headers, json={
        "email": invitee_email, "role": "dispatcher"
    })
    assert inv_res.status_code == 201
    token = inv_res.json()["token"]

    # Invitee registers and accepts
    invitee_headers = await _create_bare_user(client, invitee_email)

    accept_res = await client.post(f"{API}/team/invites/accept",
                                    headers=invitee_headers,
                                    json={"token": token})
    assert accept_res.status_code == 200
    assert accept_res.json()["role"] == "dispatcher"

    # Invitee now appears in member list
    members_res = await client.get(f"{API}/team/members", headers=owner_headers)
    member_emails = [m["email"] for m in members_res.json()]
    assert invitee_email in member_emails


@pytest.mark.asyncio
async def test_invite_wrong_email_rejected(client: AsyncClient):
    """Accepting invite with wrong email returns 403."""
    owner_email = f"owner2_{uuid.uuid4().hex[:6]}@test.com"
    owner_headers = await _create_user_with_fleet(client, owner_email, tier="tier2")

    # Invite sent to specific email
    inv_res = await client.post(f"{API}/team/invites", headers=owner_headers, json={
        "email": "specific@test.com", "role": "viewer"
    })
    token = inv_res.json()["token"]

    # Different user tries to accept
    wrong_email = f"wrong_{uuid.uuid4().hex[:6]}@test.com"
    wrong_headers = await _create_bare_user(client, wrong_email)

    res = await client.post(f"{API}/team/invites/accept",
                             headers=wrong_headers, json={"token": token})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_revoke_invite(client: AsyncClient):
    """Owner can revoke a pending invite."""
    email = f"revoke_{uuid.uuid4().hex[:6]}@test.com"
    headers = await _create_user_with_fleet(client, email, tier="tier2")

    inv_res = await client.post(f"{API}/team/invites", headers=headers, json={
        "email": "revokable@test.com", "role": "dispatcher"
    })
    invite_id = inv_res.json()["id"]

    revoke_res = await client.delete(f"{API}/team/invites/{invite_id}", headers=headers)
    assert revoke_res.status_code == 204

    # Should no longer be pending
    list_res = await client.get(f"{API}/team/invites", headers=headers)
    invites = list_res.json()
    pending = [i for i in invites if i["id"] == invite_id and i["status"] == "pending"]
    assert len(pending) == 0
