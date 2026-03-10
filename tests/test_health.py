import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "SIGNAL" in data["service"]


@pytest.mark.asyncio
async def test_discover_returns_202(client):
    resp = await client.post(
        "/api/v1/discover",
        json={"url": "https://example.com"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "audit_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_status_404_for_unknown(client):
    resp = await client.get("/api/v1/discover/nonexistent/status")
    assert resp.status_code == 404
