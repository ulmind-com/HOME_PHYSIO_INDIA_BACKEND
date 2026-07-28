"""Authentication flow tests."""


async def test_login_success(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin@12345"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == "admin@test.com"


async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["success"] is False


async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_returns_profile(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_superuser"] is True


async def test_refresh_token(client):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin@12345"},
    )
    refresh = login.json()["data"]["refresh_token"]
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert resp.json()["data"]["access_token"]


async def test_change_password_wrong_current(client, auth_headers):
    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "nope", "new_password": "NewPass@123"},
    )
    assert resp.status_code == 400
