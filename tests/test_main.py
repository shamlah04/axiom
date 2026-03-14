import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    # Accept any 5.x version
    assert data["version"].startswith("5.")


@pytest.mark.asyncio
async def test_root_not_found(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 404
