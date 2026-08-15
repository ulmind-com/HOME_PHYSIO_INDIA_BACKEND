import urllib.request
import urllib.parse
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
    if hasattr(e, 'read'):
        print(e.read().decode())
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 2. Categories
categories = [
    {
        "name": "Home Nursing Care",
        "description": "24/7 qualified nurses at your home — injections, wound care, monitoring.",
        "image": {"url": "/assets/categories/nursing-v2.jpg?v=2"},
        "order": 1,
    },
    {
        "name": "Elderly Care",
        "description": "Compassionate daily companionship and assisted living support.",
        "image": {"url": "/assets/categories/elder.jpg?v=2"},
        "order": 2,
    },
    {
        "name": "Mother & Baby Care",
        "description": "Expert postnatal care for new mothers & newborns — feeding support, baby care & recovery.",
        "image": {"url": "/assets/categories/mother-baby.png"},
        "order": 3,
    },
    {
        "name": "Physiotherapy & Recovery",
        "description": "In-home rehab, mobility & pain management by expert therapists.",
        "image": {"url": "/assets/categories/physio-v2.jpg?v=2"},
        "order": 4,
    },
    {
        "name": "Medical Equipment Rental",
        "description": "Hospital-grade beds, oxygen, monitors — delivered & installed.",
        "image": {"url": "/assets/categories/equipment-v2.jpg?v=2"},
        "order": 5,
    },
    {
        "name": "ICU Setup",
        "description": "Complete home ICU setup with ventilators, monitors & trained ICU nurses round the clock.",
        "image": {"url": "/assets/categories/icu-setup.png"},
        "order": 6,
    },
    {
        "name": "Home Sample Collection",
        "description": "Convenient at-home blood tests & lab sample collection by certified phlebotomists.",
        "image": {"url": "/assets/categories/home-sample.png"},
        "order": 7,
    },
]

for cat in categories:
    req = urllib.request.Request(f"{URL}/services/categories", data=json.dumps(cat).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            print(cat["name"], resp.status, resp.read().decode())
    except Exception as e:
        print(cat["name"], "failed:", e)
        if hasattr(e, 'read'):
            print(e.read().decode())
