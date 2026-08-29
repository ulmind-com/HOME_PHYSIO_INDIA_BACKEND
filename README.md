# Home Physio India — Backend API

A production-grade, **API-only** backend for the *Home Physio India*
platform. It powers both the admin panel and the public website (services,
bookings, medical-equipment rentals, careers, blogs, videos, testimonials, FAQs,
contact, settings/SEO, uploads, notifications and analytics).

> This project is **backend only** — no frontend, no HTML templates. Everything
> is exposed as JSON REST APIs, ready to serve a modern React/Next.js frontend
> without any backend changes.

---

## ✨ Tech Stack

| Concern           | Technology                                   |
| ----------------- | -------------------------------------------- |
| Language          | Python 3.13+                                 |
| Framework         | FastAPI                                       |
| Database          | MongoDB Atlas                                 |
| ODM               | Beanie (async, on Motor)                      |
| Auth              | JWT access + refresh tokens, bcrypt hashing   |
| File storage      | Cloudinary                                    |
| Email             | SMTP + FastAPI BackgroundTasks (aiosmtplib)   |
| Validation        | Pydantic v2                                   |
| Rate limiting     | SlowAPI                                        |
| Docs              | Swagger (`/docs`) + ReDoc (`/redoc`)          |
| Logging           | Structured JSON logs with request correlation |
| Deployment        | Docker / Render                               |

---

## 🏗️ Architecture

The codebase follows SOLID principles with clear separation of concerns and
dependency injection throughout.

```
app/
├── api/v1/            # Route handlers (thin controllers), one package per module
│   ├── auth/  users/  dashboard/  services/  bookings/  equipment/
│   ├── careers/  blogs/  videos/  testimonials/  faq/  reviews/
│   ├── contact/  settings/  notifications/  uploads/  search/
│   └── helpers.py     # Response-building helpers
├── core/              # Cross-cutting: config-free security, logging, exceptions,
│                      #   responses, pagination, rate limiter, permissions, handlers
├── config/            # Pydantic settings (env-driven)
├── database/          # Mongo connection, Beanie init, idempotent seeding
├── dependencies/      # FastAPI DI: auth, RBAC (require_permission)
├── middleware/        # Request-id/logging + security headers
├── models/            # Beanie documents (collections)
├── repositories/      # Generic async data-access layer (BaseRepository)
├── schemas/           # Pydantic request/response models
├── services/          # Business logic (auth, booking, dashboard, crud, email,
│                      #   cloudinary, notifications, activity log)
├── utils/             # Slugs, references, sanitisation, file validation
└── main.py            # App factory, lifespan, middleware & router wiring
```

**Layering:** `routes → services → repositories → models`. Routes never touch
the ODM directly; a generic `BaseRepository` and `CrudService` keep the modules
DRY while each retains its own schemas and custom endpoints.

### Standard response envelope

Every endpoint returns the same shape:

```json
{
  "success": true,
  "message": "",
  "data": {},
  "errors": null
}
```

List endpoints wrap results with pagination metadata:

```json
{
  "success": true,
  "message": "Fetched successfully",
  "data": {
    "items": [ ... ],
    "pagination": {
      "total": 42, "page": 1, "page_size": 10,
      "total_pages": 5, "has_next": true, "has_prev": false
    }
  },
  "errors": null
}
```

---

## 🚀 Getting Started (Local)

### Prerequisites

- Python **3.13+**
- A MongoDB Atlas connection string (already configured in `.env`)
- (Optional) Cloudinary + SMTP credentials for uploads and email

### 1. Install dependencies

```bash
python3.13 -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> Using [`uv`](https://github.com/astral-sh/uv)? `uv venv --python 3.13 venv && uv pip install -r requirements.txt`

### 2. Configure environment

A ready-to-run `.env` is already included. Copy the template for other
environments:

```bash
cp .env.example .env
```

Generate a strong secret key for production:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3. Run the API

```bash
python run.py
# or
uvicorn app.main:app --reload
```

On first startup the app automatically:
- connects to MongoDB Atlas and registers all indexes,
- seeds the permission catalogue and default roles,
- creates a bootstrap **super-admin** from `FIRST_ADMIN_*` env vars.

### 4. Open the docs

- Swagger UI → http://localhost:8000/docs
- ReDoc → http://localhost:8000/redoc
- Health → http://localhost:8000/health

### 5. Log in

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@homephysioindia.com","password":"Admin@12345"}'
```

Use the returned `access_token` as `Authorization: Bearer <token>`.

---

## 🧪 Testing

Tests run against an in-memory Mongo (`mongomock-motor`) — no network required.

```bash
pytest
```

---

## 🐳 Docker

```bash
# Build & run (reads .env)
docker compose up --build
```

The image runs Gunicorn with Uvicorn workers and a container health check.

---

## ☁️ Deploying to Render

1. Push this repo to GitHub.
2. In Render, create a **Blueprint** from `render.yaml` (or a Web Service with
   build `pip install -r requirements.txt` and the start command below).
3. Set the secret environment variables (marked `sync: false`) in the Render
   dashboard — at minimum `MONGODB_URL`, Cloudinary and SMTP credentials,
   `CORS_ORIGINS`, and `FIRST_ADMIN_*`.
4. `SECRET_KEY` is generated automatically; health checks hit `/health`.

Start command:

```
gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:$PORT --timeout 120
```

---

## 🔐 Authentication & Authorization

- **JWT access tokens** (short-lived) + **refresh tokens** (long-lived, stored
  server-side for rotation & revocation).
- **Logout** blacklists the refresh token; **change/reset password** revokes all
  sessions.
- **RBAC**: permissions use a `resource:action` convention (e.g. `bookings:update`).
  Roles bundle permissions; users may also hold direct `extra_permissions`.
  Superusers implicitly hold `*`.
- Seeded roles: `super_admin`, `admin`, `editor`, `support`.
- Every admin action is written to the **activity log** for auditing.

---

## 🔧 Environment Variables

| Variable | Description | Example |
| --- | --- | --- |
| `APP_NAME` | Display name | `Home Physio India` |
| `APP_ENV` | `development` / `production` | `development` |
| `DEBUG` | Debug mode & reload | `true` |
| `API_V1_PREFIX` | API base path | `/api/v1` |
| `HOST` / `PORT` | Bind address | `0.0.0.0` / `8000` |
| `SECRET_KEY` | JWT signing key (**required**) | `token_urlsafe(64)` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token TTL | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token TTL | `7` |
| `PASSWORD_RESET_EXPIRE_MINUTES` | Reset-token TTL | `30` |
| `MONGODB_URL` | Atlas connection string (**required**) | `mongodb+srv://...` |
| `MONGODB_DB_NAME` | Database name | `home_physio_india` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud | `l1on8azb` |
| `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | Cloudinary creds | — |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server | `smtp.gmail.com` / `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP creds (Gmail app password) | — |
| `SMTP_FROM_EMAIL` / `SMTP_FROM_NAME` | From identity | — |
| `ADMIN_NOTIFICATION_EMAIL` | Where admin alerts go | — |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `RATE_LIMIT_DEFAULT` / `RATE_LIMIT_AUTH` | SlowAPI limits | `200/minute` / `10/minute` |
| `FRONTEND_URL` | For password-reset links | `http://localhost:3000` |
| `FIRST_ADMIN_NAME/EMAIL/PASSWORD` | Bootstrap admin | — |

---

## 📚 API Overview

All routes are prefixed with `/api/v1`. Public endpoints need no auth; admin
endpoints require a Bearer token and the relevant permission.

| Module | Key endpoints | Access |
| --- | --- | --- |
| **Auth** | `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/change-password`, `/auth/forgot-password`, `/auth/reset-password`, `GET/PUT /auth/me` | Public / User |
| **Users & Roles** | `GET/POST/PUT/DELETE /users`, `/users/roles`, `/users/permissions/all` | `users:*`, `roles:*` |
| **Dashboard** | `/dashboard/stats`, `/dashboard/charts`, `/dashboard/recent-*`, `/dashboard/activity-logs` | `dashboard:view` |
| **Services** | `GET/POST/PUT/DELETE /services`, `/services/categories`, `/services/slug/{slug}` | Public read / `services:*` |
| **Bookings** | `POST /bookings` (public), list/approve/reject/cancel/assign/export | Public create / `bookings:*` |
| **Equipment** | `/equipment`, `/equipment/categories`, `/equipment/rentals` | Public read / `equipment:*`, `rentals:*` |
| **Careers** | `/careers`, `/careers/categories`, `/careers/applications` (resume upload) | Public apply / `careers:*`, `applications:*` |
| **Blogs** | `/blogs`, `/blogs/categories`, `/blogs/slug/{slug}` | Public read / `blogs:*` |
| **Videos** | `/videos` (YouTube or Cloudinary) | Public read / `videos:*` |
| **Testimonials** | `/testimonials` | Public read / `testimonials:*` |
| **FAQ** | `/faqs` | Public read / `faqs:*` |
| **Reviews** | `/reviews/summary` | Public |
| **Contact** | `POST /contact` (public), admin management | Public create / `contacts:*` |
| **Settings & SEO** | `/settings`, `/settings/social`, `/settings/seo` | Public read / `settings:*`, `seo:*` |
| **Notifications** | `/notifications`, `/notifications/unread-count`, `read`, `read-all` | User |
| **Uploads** | `POST /uploads/image`, `/uploads/file`, `/uploads/video`, `DELETE /uploads` | `media:*` |
| **Search** | `GET /search?q=` (across services, blogs, equipment, bookings, applications) | `dashboard:view` |

Full request/response schemas are documented interactively at `/docs`.

### Common list query parameters

`page`, `page_size` (max 100), `search`, `sort_by`, `sort_order` (`asc`/`desc`),
plus per-module filters like `status`, `category_id`, `is_featured`.

---

## 🛡️ Security Features

- JWT access/refresh with server-side refresh-token rotation & blacklist
- bcrypt password hashing
- Role/permission based authorization
- Pydantic input validation + input sanitisation
- Per-route and global rate limiting (SlowAPI)
- Configurable CORS
- Security headers (CSP, X-Frame-Options, nosniff, ...) middleware
- Consistent error envelope via a global exception handler
- Full audit trail (activity logs) + admin session tracking

---

## 📄 License

Proprietary — © Home Physio India.
