import pytest
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    payload = {
        "email": "test@example.com",
        "password": "strongpassword123",
        "full_name": "Test User"
    }
    response = await client.post(f"{settings.API_V1_PREFIX}/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert "id" in data

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    # Register first
    payload = {
        "email": "login@example.com",
        "password": "loginpassword123",
        "full_name": "Login User"
    }
    await client.post(f"{settings.API_V1_PREFIX}/auth/register", json=payload)
    
    # Login
    login_data = {
        "username": payload["email"],
        "password": payload["password"]
    }
    response = await client.post(f"{settings.API_V1_PREFIX}/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    # Register and login
    email = "me@example.com"
    password = "mepassword123"
    await client.post(f"{settings.API_V1_PREFIX}/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Me User"
    })
    
    login_res = await client.post(f"{settings.API_V1_PREFIX}/auth/login", data={
        "username": email,
        "password": password
    })
    token = login_res.json()["access_token"]
    
    # Get me
    response = await client.get(
        f"{settings.API_V1_PREFIX}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == email
