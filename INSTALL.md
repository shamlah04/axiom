# Axiom Installation & Configuration Guide

This document provides detailed instructions on how to set up, configure, and operate the Axiom platform.

---

## 🏗 System Architecture Overview

Axiom follows a modern asynchronous Python architecture:
- **FastAPI**: Non-blocking handles for high-concurrency API requests.
- **SQLAlchemy 2.0 (Async)**: Type-safe database interactions.
- **Alembic**: Transactional database migrations.
- **Docker**: Containerized deployment for consistent environments.

---

## 🛠 Installation Methods

### Method A: Docker Compose (Recommended)
This is the fastest way to get a production-ready setup with PostgreSQL.

1.  **Configure environment**:
    ```bash
    cp .env.example .env
    # Generate a secure key
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    ```
2.  **Launch**:
    ```bash
    docker-compose up --build -d
    ```
3.  **Verify**:
    Check health at `http://localhost:8000/health`.

### Method B: Manual (Development)
Use this if you want to run the API directly on your host machine.

1.  **Create Virtual Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements_ml.txt
    ```
2.  **Database Strategy**:
    Axiom can run on **PostgreSQL** (recommended) or **SQLite** (for zero-setup dev).
    *   For SQLite, set in `.env`: `DATABASE_URL=sqlite+aiosqlite:///./dev.db`
3.  **Run Dev Server**:
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```

---

## ⚙️ Configuration (.env)

| Variable | Required | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` or `sqlite+aiosqlite://...` |
| `SECRET_KEY` | Yes | 32+ character random string for JWT signing. |
| `DEBUG` | No | Set `true` to enable SQL echo and verbose logging. |
| `RESEND_API_KEY` | No | API key from resend.com. Set to `disabled` for mock mode. |
| `STRIPE_SECRET_KEY` | No | Stripe secret key (`sk_...`). Set to `disabled` for mock mode. |
| `STRIPE_WEBHOOK_SECRET` | No | Secret for verifying Stripe webhooks. |
| `APP_BASE_URL` | No | Deep links in emails will point here (default: `localhost:3000`). |

---

## 🛡️ Role-Based Access Control (RBAC)

Axiom enforces permissions at the API level:

1.  **Owner**:
    *   Access to `/billing` (Stripe checkouts)
    *   Access to `/team` (Invites, role changing)
    *   Access to `/billing/audit` (Audit logs)
    *   Has all Dispatcher & Viewer permissions.
2.  **Dispatcher**:
    *   Write access to Trucks, Drivers, and Jobs.
    *   Read access to Dashboards and Intelligence.
3.  **Viewer**:
    *   Read-only access to Fleet data.
    *   Cannot create/edit trucks, drivers, or jobs.

---

## 💳 Billing & Stripe Setup

To test the full billing cycle:
1.  **Stripe Dashboard**: Create products and prices for "Growth" (Tier 2) and "Enterprise" (Tier 3).
2.  **Env**: Set `STRIPE_PRICE_TIER2` and `STRIPE_PRICE_TIER3` with the Stripe Price IDs.
3.  **Webhooks**: Point Stripe webhooks to `https://your-domain.com/webhooks/stripe`.
4.  **Local Testing**: Use the Stripe CLI to forward webhooks:
    ```bash
    stripe listen --forward-to localhost:8000/webhooks/stripe
    ```

---

## 🧪 Testing

Axiom uses `pytest` with `pytest-asyncio`. Tests use an in-memory SQLite database automatically.

```bash
# Run all tests
pytest tests/

# Run specific phase tests
pytest tests/api/v1/test_team.py           # Phase 3
pytest tests/api/v1/test_billing_audit.py  # Phase 4
```

---

## 📂 Project Structure

```text
├── alembic/              # DB Migrations
├── app/
│   ├── api/v1/           # Route handlers
│   ├── core/             # Auth, Security, Config
│   ├── ml/               # Prediction Logic & Features
│   ├── models/           # SQLAlchemy ORM
│   ├── repositories/     # Data Access Layer
│   ├── schemas/          # Pydantic Schemas
│   └── services/         # Business Logic (Stripe/Email)
├── tests/                # Integration & Unit Tests
└── web/                  # Next.js Frontend
```
