"""Services CRUD, slug, pagination and authorization tests."""


async def test_create_requires_auth(client):
    resp = await client.post("/api/v1/services", json={"title": "X Service"})
    assert resp.status_code == 401


async def test_service_crud_lifecycle(client, auth_headers):
    # Create
    create = await client.post(
        "/api/v1/services",
        headers=auth_headers,
        json={"title": "Physiotherapy at Home", "price": 900},
    )
    assert create.status_code == 201
    service = create.json()["data"]
    assert service["slug"] == "physiotherapy-at-home"
    service_id = service["id"]

    # Read by id
    got = await client.get(f"/api/v1/services/{service_id}")
    assert got.status_code == 200
    assert got.json()["data"]["title"] == "Physiotherapy at Home"

    # Read by slug
    by_slug = await client.get("/api/v1/services/slug/physiotherapy-at-home")
    assert by_slug.status_code == 200

    # Update
    upd = await client.put(
        f"/api/v1/services/{service_id}",
        headers=auth_headers,
        json={"price": 1200, "is_featured": True},
    )
    assert upd.status_code == 200
    assert upd.json()["data"]["price"] == 1200
    assert upd.json()["data"]["is_featured"] is True

    # Delete
    delete = await client.delete(
        f"/api/v1/services/{service_id}", headers=auth_headers
    )
    assert delete.status_code == 200

    # Confirm gone
    missing = await client.get(f"/api/v1/services/{service_id}")
    assert missing.status_code == 404


async def test_unique_slug_on_duplicate_titles(client, auth_headers):
    a = await client.post(
        "/api/v1/services", headers=auth_headers, json={"title": "Duplicate Name"}
    )
    b = await client.post(
        "/api/v1/services", headers=auth_headers, json={"title": "Duplicate Name"}
    )
    assert a.json()["data"]["slug"] != b.json()["data"]["slug"]


async def test_services_pagination(client, auth_headers):
    for i in range(5):
        await client.post(
            "/api/v1/services", headers=auth_headers, json={"title": f"Svc {i}"}
        )
    resp = await client.get("/api/v1/services?page=1&page_size=2")
    body = resp.json()["data"]
    assert len(body["items"]) == 2
    assert body["pagination"]["total"] >= 5
    assert body["pagination"]["has_next"] is True
