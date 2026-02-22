import pytest
import uuid
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_create_job_with_prediction_smoke(client: AsyncClient):
    """
    Smoke test for Phase 1 ML integration:
    - User registration/login
    - Truck/Driver creation
    - Job creation (triggers prediction engine)
    - Prediction log verification
    - Explanation endpoint verification
    """
    # 1. Register and login
    email = f"ml_test_{uuid.uuid4().hex[:6]}@example.com"
    password = "jobspassword123"
    reg_res = await client.post(f"{settings.API_V1_PREFIX}/auth/register", json={
        "email": email, "password": password, "full_name": "ML Test User"
    })
    assert reg_res.status_code == 201

    login_res = await client.post(f"{settings.API_V1_PREFIX}/auth/login", data={
        "username": email, "password": password
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create a fleet
    await client.post(
        f"{settings.API_V1_PREFIX}/fleets",
        headers=headers,
        json={"name": "Test Fleet", "country": "DK", "subscription_tier": "tier2"}
    )

    # 3. Create a truck
    truck_res = await client.post(
        f"{settings.API_V1_PREFIX}/trucks",
        headers=headers,
        json={
            "name": "Test Truck",
            "fuel_consumption_per_100km": 30.0,
            "maintenance_cost_per_km": 0.5,
            "insurance_monthly": 500.0,
            "leasing_monthly": 1000.0,
            "fuel_type": "diesel"
        }
    )
    assert truck_res.status_code == 201
    truck_id = truck_res.json()["id"]

    # 3. Create a driver
    driver_res = await client.post(
        f"{settings.API_V1_PREFIX}/drivers",
        headers=headers,
        json={
            "name": "Test Driver",
            "hourly_rate": 25.0,
            "monthly_fixed_cost": 2000.0
        }
    )
    assert driver_res.status_code == 201
    driver_id = driver_res.json()["id"]

    # 4. Create a job (triggers prediction engine)
    job_payload = {
        "truck_id": truck_id,
        "driver_id": driver_id,
        "origin": "Copenhagen",
        "destination": "Berlin",
        "distance_km": 440.0,
        "estimated_duration_hours": 6.0,
        "offered_rate": 1200.0,
        "fuel_price_per_unit": 1.5,
        "job_date": "2026-03-01T12:00:00Z"
    }
    job_res = await client.post(f"{settings.API_V1_PREFIX}/jobs", headers=headers, json=job_payload)
    assert job_res.status_code == 201
    job_data = job_res.json()
    
    # Verify job output schema
    assert "job_id" in job_data
    assert "net_profit" in job_data
    assert "ai_explanation" in job_data
    assert "fuel_cost" in job_data
    
    job_id = job_data["job_id"]

    # 5. Check explanation endpoint
    exp_res = await client.get(f"{settings.API_V1_PREFIX}/jobs/{job_id}/explanation", headers=headers)
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    
    assert exp_data["job_id"] == job_id
    assert "feature_importances" in exp_data
    assert exp_data["used_ml_model"] is False  # Should be False as no model is trained yet
    
    # 6. Check ML status endpoint
    status_res = await client.get(f"{settings.API_V1_PREFIX}/ml/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "fallback"
