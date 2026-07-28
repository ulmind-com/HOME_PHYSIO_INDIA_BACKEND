"""Health & root endpoint tests."""


async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "version" in body["data"]


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] in {"ok", "degraded"}
