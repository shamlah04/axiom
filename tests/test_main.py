import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "5.0.0", "db": "ok"}

@pytest.mark.asyncio
async def test_root_not_found(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 404
