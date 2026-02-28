import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select

from app.models.models import User, Fleet, SubscriptionTier, Truck, Driver, Job
from app.models.audit import AuditEventType, AuditLog
from app.repositories.audit_repository import AuditRepository
from app.services.scheduler import trial_warning_job, trial_expiry_job
from app.core.config import settings

@pytest.fixture
async def auth_tokens(client: AsyncClient):
    """Creates a fleet and an owner, returns (token, fleet_id, user_id)."""
    email = f"owner_{uuid.uuid4().hex[:6]}@test.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Owner"}
    )
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"}
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    f_res = await client.post(
        "/api/v1/fleets",
        json={"name": "Audit Fleet", "country": "DK"},
        headers=headers
    )
    fleet_id = f_res.json()["id"]
    
    u_res = await client.get("/api/v1/auth/me", headers=headers)
    user_id = u_res.json()["id"]
    
    return token, fleet_id, user_id, email

@pytest.mark.asyncio
async def test_auth_audit_trail(client: AsyncClient, db_session):
    """Verifies register, login, and login_failed events."""
    email = f"audit_{uuid.uuid4().hex[:6]}@test.com"
    
    # 1. Register
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Auditor"}
    )
    
    # 2. Login
    await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"}
    )
    
    # 3. Login Failure
    await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "wrong"}
    )
    
    await asyncio.sleep(0.1) # Background tasks
    
    res = await db_session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()))
    logs = list(res.scalars().all())
    
    event_types = [l.event_type for l in logs]
    assert AuditEventType.USER_REGISTERED in event_types
    assert AuditEventType.USER_LOGIN in event_types
    assert AuditEventType.USER_LOGIN_FAILED in event_types

@pytest.mark.asyncio
async def test_billing_portal_route(client: AsyncClient, auth_tokens):
    token, fleet_id, user_id, email = auth_tokens
    headers = {"Authorization": f"Bearer {token}"}
    
    # Should work (mock mode by default in tests)
    res = await client.get("/api/v1/billing/portal", headers=headers)
    assert res.status_code == 200
    assert "portal_url" in res.json()
    assert "/billing/mock-portal" in res.json()["portal_url"]

@pytest.mark.asyncio
async def test_job_terminal_status_audit(client: AsyncClient, auth_tokens, db_session):
    token, fleet_id, user_id, email = auth_tokens
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Setup Truck/Driver
    t_res = await client.post(
        "/api/v1/trucks",
        json={"name": "T1", "fuel_consumption_per_100km": 30, "maintenance_cost_per_km": 0.5, "insurance_monthly": 100},
        headers=headers
    )
    tid = t_res.json()["id"]
    
    d_res = await client.post(
        "/api/v1/drivers",
        json={"name": "D1", "hourly_rate": 20},
        headers=headers
    )
    did = d_res.json()["id"]
    
    # 2. Create Job
    j_res = await client.post(
        "/api/v1/jobs",
        json={
            "truck_id": tid, "driver_id": did, "origin": "A", "destination": "B",
            "distance_km": 100, "estimated_duration_hours": 2, "offered_rate": 500,
            "fuel_price_per_unit": 1.5
        },
        headers=headers
    )
    jid = j_res.json()["job_id"]
    
    # 3. Update status to 'accepted'
    await client.patch(f"/api/v1/jobs/{jid}/status", json={"status": "accepted"}, headers=headers)
    
    await asyncio.sleep(0.1)
    
    audit = AuditRepository(db_session)
    logs = await audit.list_for_fleet(uuid.UUID(fleet_id), event_type=AuditEventType.JOB_ACCEPTED)
    assert len(logs) == 1
    assert logs[0].subject_id == jid
    assert logs[0].metadata_["status"] == "accepted"

@pytest.mark.asyncio
async def test_job_actuals_audit(client: AsyncClient, auth_tokens, db_session):
    token, fleet_id, user_id, email = auth_tokens
    headers = {"Authorization": f"Bearer {token}"}
    
    # Use existing job flow
    t_res = await client.post("/api/v1/trucks", json={"name": "T2", "fuel_consumption_per_100km": 30, "maintenance_cost_per_km": 0.5, "insurance_monthly": 100}, headers=headers)
    tid = t_res.json()["id"]
    d_res = await client.post("/api/v1/drivers", json={"name": "D2", "hourly_rate": 20}, headers=headers)
    did = d_res.json()["id"]
    j_res = await client.post("/api/v1/jobs", json={"truck_id": tid, "driver_id": did, "origin": "A", "destination": "B", "distance_km": 100, "estimated_duration_hours": 2, "offered_rate": 500, "fuel_price_per_unit": 1.5}, headers=headers)
    jid = j_res.json()["job_id"]
    
    # Update actuals
    await client.patch(f"/api/v1/jobs/{jid}/actual", json={"actual_revenue": 550, "actual_cost": 400}, headers=headers)
    
    await asyncio.sleep(0.1)
    
    audit = AuditRepository(db_session)
    logs = await audit.list_for_fleet(uuid.UUID(fleet_id), event_type=AuditEventType.JOB_ACTUALS_RECORDED)
    assert len(logs) == 1
    assert logs[0].metadata_["actual_revenue"] == 550
    assert logs[0].metadata_["predicted_net_profit"] is not None

@pytest.mark.asyncio
async def test_scheduler_trial_warning_job(db_session):
    """Unit test for trial_warning_job: finds fleet, sends email, logs audit."""
    # 1. Create a fleet with trial ending in 3 days
    fleet = Fleet(
        id=uuid.uuid4(),
        name="Warning Fleet",
        subscription_tier=SubscriptionTier.tier1,
        trial_ends_at=datetime.now() + timedelta(days=2, hours=23)
    )
    db_session.add(fleet)
    owner_email = f"owner_warn_{uuid.uuid4().hex[:6]}@test.com"
    owner = User(id=uuid.uuid4(), email=owner_email, hashed_password="...", full_name="Owner", role="owner", fleet_id=fleet.id)
    db_session.add(owner)
    await db_session.commit()
    
    # 2. Run job
    await trial_warning_job()
    
    # 3. Check audit log
    audit = AuditRepository(db_session)
    logs = await audit.list_for_fleet(fleet.id, event_type=AuditEventType.TRIAL_WARNING_SENT)
    assert len(logs) == 1
    assert logs[0].metadata_["to"] == owner_email

@pytest.mark.asyncio
async def test_scheduler_trial_expiry_job(db_session):
    """Unit test for trial_expiry_job: finds expired fleet, logs audit."""
    # 1. Create a fleet with expired trial
    fleet = Fleet(
        id=uuid.uuid4(),
        name="Expired Fleet",
        subscription_tier=SubscriptionTier.tier1,
        trial_ends_at=datetime.now() - timedelta(days=1)
    )
    db_session.add(fleet)
    await db_session.commit()
    
    # 2. Run job
    await trial_expiry_job()
    
    # 3. Check audit log
    audit = AuditRepository(db_session)
    logs = await audit.list_for_fleet(fleet.id, event_type=AuditEventType.TRIAL_EXPIRED)
    assert len(logs) == 1
