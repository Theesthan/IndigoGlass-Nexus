"""
IndigoGlass Nexus - API Tests
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Test health endpoint returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_root_redirect(client: AsyncClient):
    """Test root redirects to docs."""
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert "/docs" in response.headers.get("location", "")


@pytest.mark.anyio
async def test_openapi_schema(client: AsyncClient):
    """Test OpenAPI schema is accessible."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "IndigoGlass Nexus API"
    assert "paths" in data


@pytest.mark.anyio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "invalid@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_protected_endpoint_no_auth(client: AsyncClient):
    """Test protected endpoints require authentication."""
    response = await client.get("/api/v1/kpis/snapshot")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_kpis_snapshot_with_auth(client: AsyncClient):
    """Test KPIs endpoint with valid auth token."""
    # This would need a valid token - skipping for now
    pytest.skip("Requires database setup for auth")


@pytest.mark.anyio
async def test_forecast_endpoint_structure(client: AsyncClient):
    """Test forecast endpoint response structure."""
    # This would need a valid token - skipping for now
    pytest.skip("Requires database setup for auth")
