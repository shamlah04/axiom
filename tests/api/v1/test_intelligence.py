"""
tests/api/v1/test_intelligence.py
──────────────────────────────────
Integration tests for Phase 2 intelligence endpoints.

Tests cover:
  - GET /intelligence/benchmark  (cold start — no jobs)
  - GET /intelligence/trends     (insufficient data path)
  - GET /intelligence/anomalies  (insufficient baseline path)
  - GET /intelligence/summary    (all three combined)
  - Benchmark with seeded jobs   (happy path)
  - Anomaly detection with outlier job
"""

import pytest
import uuid
from httpx import AsyncClient
from app.core.config import settings

API = settings.API_V1_PREFIX


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

async def _register_login(client: AsyncClient, suffix: str = "") -> dict:
    email = f"intel_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    password = "testpassword123"
    await client.post(f"{API}/auth/register", json={
        "email": email, "password": password, "full_name": "Intel Test"
    })
    res = await client.post(f"{API}/auth/login", data={"username": email, "password": password})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create fleet
    await client.post(f"{API}/fleets", headers=headers, json={
        "name": "Intel Test Fleet", "country": "DK", "subscription_tier": "tier2"
    })
    return headers


async def _create_truck_driver(client: AsyncClient, headers: dict) -> tuple[str, str]:
    truck = await client.post(f"{API}/trucks", headers=headers, json={
        "name": "T1", "fuel_consumption_per_100km": 30.0,
        "maintenance_cost_per_km": 0.5, "insurance_monthly": 500.0,
        "leasing_monthly": 1000.0, "fuel_type": "diesel"
    })
    driver = await client.post(f"{API}/drivers", headers=headers, json={
        "name": "D1", "hourly_rate": 25.0, "monthly_fixed_cost": 2000.0
    })
    return truck.json()["id"], driver.json()["id"]


async def _create_job(client, headers, truck_id, driver_id, rate=1200.0, distance=440.0):
    res = await client.post(f"{API}/jobs", headers=headers, json={
        "truck_id": truck_id, "driver_id": driver_id,
        "origin": "Copenhagen", "destination": "Hamburg",
        "distance_km": distance, "estimated_duration_hours": 6.0,
        "offered_rate": rate, "fuel_price_per_unit": 1.5,
    })
    return res.json()


# ─────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_benchmark_cold_start(client: AsyncClient):
    """Benchmark returns gracefully when fleet has no jobs."""
    headers = await _register_login(client, "bench_cold")
    res = await client.get(f"{API}/intelligence/benchmark", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["insufficient_data"] is True
    assert data["fleet_metrics"]["job_count"] == 0
    assert len(data["insights"]) > 0


@pytest.mark.asyncio
async def test_trends_insufficient_data(client: AsyncClient):
    """Trend returns 'unknown' when not enough weekly data."""
    headers = await _register_login(client, "trend_cold")
    res = await client.get(f"{API}/intelligence/trends?weeks=12", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["trend"] == "unknown"
    assert data["confidence"] == "insufficient_data"
    assert data["alert"] is False


@pytest.mark.asyncio
async def test_anomalies_insufficient_baseline(client: AsyncClient):
    """Anomaly endpoint reports insufficient baseline when < 10 jobs."""
    headers = await _register_login(client, "anomaly_cold")
    res = await client.get(f"{API}/intelligence/anomalies?days=30", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["insufficient_baseline"] is True
    assert data["n_anomalies"] == 0


@pytest.mark.asyncio
async def test_summary_endpoint_returns_all_sections(client: AsyncClient):
    """Summary endpoint always returns all three sections."""
    headers = await _register_login(client, "summary")
    res = await client.get(f"{API}/intelligence/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "benchmark" in data
    assert "trend" in data
    assert "anomalies" in data
    # Each section has required keys
    assert "fleet_percentile" in data["benchmark"]
    assert "trend" in data["trend"]
    assert "n_anomalies" in data["anomalies"]


@pytest.mark.asyncio
async def test_benchmark_with_accepted_jobs(client: AsyncClient):
    """Benchmark returns fleet metrics after jobs are accepted."""
    headers = await _register_login(client, "bench_jobs")
    truck_id, driver_id = await _create_truck_driver(client, headers)

    # Create and accept 3 jobs
    for rate in [1200.0, 1400.0, 1100.0]:
        job = await _create_job(client, headers, truck_id, driver_id, rate=rate)
        await client.patch(
            f"{API}/jobs/{job['job_id']}/status",
            headers=headers,
            json={"status": "accepted"}
        )

    res = await client.get(f"{API}/intelligence/benchmark", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Fleet metrics should now be populated
    assert data["fleet_metrics"]["job_count"] == 3
    assert data["fleet_metrics"]["avg_margin_pct"] is not None
    # Industry context may or may not exist depending on test DB state
    assert "industry_context" in data


@pytest.mark.asyncio
async def test_anomaly_detection_with_outlier(client: AsyncClient):
    """
    Create 12 normal jobs + 1 low-margin outlier.
    The outlier should be flagged.
    """
    headers = await _register_login(client, "anomaly_outlier")
    truck_id, driver_id = await _create_truck_driver(client, headers)

    # Create 12 normal jobs (good margin ~20%)
    for _ in range(12):
        job = await _create_job(client, headers, truck_id, driver_id, rate=1200.0, distance=440.0)
        await client.patch(
            f"{API}/jobs/{job['job_id']}/status",
            headers=headers, json={"status": "accepted"}
        )

    # Create 1 outlier job (very low rate = low/negative margin)
    outlier_job = await _create_job(client, headers, truck_id, driver_id, rate=300.0, distance=440.0)
    await client.patch(
        f"{API}/jobs/{outlier_job['job_id']}/status",
        headers=headers, json={"status": "accepted"}
    )

    res = await client.get(f"{API}/intelligence/anomalies?days=30", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Should detect the outlier
    assert data["insufficient_baseline"] is False
    assert data["n_jobs_scanned"] >= 1
    # The low-margin job should appear in anomalies
    assert data["n_anomalies"] >= 1
    anomaly_types = [a["anomaly_type"] for a in data["anomalies"]]
    assert "margin_outlier" in anomaly_types


@pytest.mark.asyncio
async def test_trends_query_param_validation(client: AsyncClient):
    """Trend weeks param is validated (4-52)."""
    headers = await _register_login(client, "trend_val")
    res = await client.get(f"{API}/intelligence/trends?weeks=2", headers=headers)
    assert res.status_code == 422   # FastAPI validation error

    res = await client.get(f"{API}/intelligence/trends?weeks=100", headers=headers)
    assert res.status_code == 422
