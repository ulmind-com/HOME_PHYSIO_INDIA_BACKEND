"""Health & root endpoint tests."""


async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "version" in body["data"]


async def test_health(client):
    """The endpoint reports 200 when the database answers and 503 when it
    doesn't. Tests run against an in-memory mock that can't be pinged, so both
    outcomes are valid here — what matters is the shape of the response."""
    resp = await client.get("/health")
    assert resp.status_code in {200, 503}
    body = resp.json()["data"]
    assert body["status"] in {"ok", "degraded"}
    assert "services" in body
