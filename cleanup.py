import urllib.request
import json

URL = "http://localhost:8000/api/v1"

# 1. Login
data = json.dumps({
    "email": "admin@nupunhealth.com",
    "password": "Admin@12345"
}).encode()

req = urllib.request.Request(f"{URL}/auth/login", data=data)
req.add_header("Content-Type", "application/json")

try:
    with urllib.request.urlopen(req) as resp:
        res_data = json.loads(resp.read().decode())
        token = res_data["data"]["access_token"]
except Exception as e:
    print("Login failed", e)
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 2. Fetch all categories
req = urllib.request.Request(f"{URL}/services/categories?page=1&page_size=50", headers=headers)
with urllib.request.urlopen(req) as resp:
    res_data = json.loads(resp.read().decode())
    items = res_data["data"]["items"]

print(f"Found {len(items)} categories:")
for cat in items:
    print(f"  {cat['id']} | {cat['name']} | slug={cat['slug']} | order={cat['order']}")

# 3. Delete old duplicates (keep only the ones from the seed - they have the newer IDs)
# Keep track of names we've seen
seen_names = {}
to_delete = []

for cat in items:
    name = cat["name"].lower().strip()
    # Normalize "Elder Care" -> "elderly care"
    if name == "elder care":
        name = "elderly care"
    
    if name in seen_names:
        # Keep the one with newer date (higher ID), delete the older one
        existing = seen_names[name]
        if cat["created_at"] < existing["created_at"]:
            to_delete.append(cat["id"])
        else:
            to_delete.append(existing["id"])
            seen_names[name] = cat
    else:
        seen_names[name] = cat

print(f"\nDeleting {len(to_delete)} duplicates:")
for cat_id in to_delete:
    req = urllib.request.Request(f"{URL}/services/categories/{cat_id}", headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"  Deleted {cat_id}: {resp.status}")
    except Exception as e:
        print(f"  Failed to delete {cat_id}: {e}")

# 4. Verify
req = urllib.request.Request(f"{URL}/services/categories?page=1&page_size=50", headers=headers)
with urllib.request.urlopen(req) as resp:
    res_data = json.loads(resp.read().decode())
    items = res_data["data"]["items"]

print(f"\nAfter cleanup: {len(items)} categories:")
for cat in items:
    print(f"  {cat['id']} | {cat['name']} | order={cat['order']}")
