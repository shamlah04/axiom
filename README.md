# Axiom — Fleet Cognitive Intelligence Platform

Axiom is an AI-driven decision intelligence platform designed for small and micro fleet operators. It transforms raw logistics data into actionable insights, providing profit predictions, risk assessments, and fleet performance benchmarking.

---

## 🚀 Key Features

### 🧠 Intelligence & Predictions
*   **Profit Prediction Engine**: Instant margin analysis for every job, including detailed cost breakdowns (fuel, driver, tolls, maintenance, fixed costs).
*   **Risk Scoring**: Automatic categorization of jobs (Accept/Review/Reject) based on profitability and volatility.
*   **Data Intelligence Dashboard**:
    *   **Benchmarking**: Compare your fleet's margin and cost performance against anonymized industry peers.
    *   **Trend Detection**: Regression-based profitability signals over time.
    *   **Anomaly Detection**: Identify jobs with significant "actual vs. predicted" deltas.

### 💼 SaaS & Monetization
*   **Subscription Tiers**: Three levels of service (Launch, Growth, Enterprise) with resource limits (trucks, drivers, team members).
*   **Trial System**: 14-day full-featured trials for all new fleets.
*   **Stripe Integration**: Self-serve checkout and automated tier upgrades via webhooks.

### 👥 Team & Governance
*   **Role-Based Access Control (RBAC)**:
    *   `Owner`: Full control, billing, and team management.
    *   `Dispatcher`: Manage operational data (trucks, drivers, jobs).
    *   `Viewer`: Read-only access to intelligence and logs.
*   **Audit Logging**: Append-only, immutable trail of all critical system events (billing, role changes, job actions).

---

## 🛠 Tech Stack

*   **Backend**: Python (FastAPI), SQLAlchemy (Async), PostgreSQL, Alembic, Pydantic.
*   **Frontend**: Next.js, Tailwind CSS (Vanilla CSS components), HSL color system.
*   **ML & Data**: Statistics/Regression-based signals, ML prediction fallback.
*   **Integrations**:
    *   **Payments**: Stripe API.
    *   **Email**: Resend API.
*   **DevOps**: Docker, Docker Compose, Pytest.

---

## 📥 Installation

### 1. Prerequisites
*   Docker & Docker Compose
*   (Optional) Python 3.10+ (for local development outside Docker)

### 2. Setup Environment
Clone the repository and create your `.env` file:
```bash
cp .env.example .env
```
Edit `.env` and set at minimum:
*   `SECRET_KEY`: A long random string.
*   `DATABASE_URL`: Use the default for Docker or point to your own Postgres.

### 3. Run with Docker
```bash
docker-compose up --build
```
The API will be available at `http://localhost:8000`.
The Frontend (if enabled) will be at `http://localhost:3000`.

### 4. Database Migrations
Migrations run automatically on Docker startup. To run them manually:
```bash
alembic upgrade head
```

---

## 📖 Usage Guide

### First Steps
1.  **Register**: Create an account via `POST /api/v1/auth/register`.
2.  **Onboard**: Create your fleet via `POST /api/v1/fleets`. You will start with a 14-day trial.
3.  **Setup Assets**: Add your trucks (`/trucks`) and drivers (`/drivers`).
4.  **Create Jobs**: Use `POST /api/v1/jobs` to get instant profit predictions.

### Documentation
*   **Swagger UI**: `http://localhost:8000/docs`
*   **Redoc**: `http://localhost:8000/redoc`

### Local Development / Mock Mode
Axiom supports a "Mock Mode" for easier development:
*   **Stripe**: If `STRIPE_SECRET_KEY` is not set, the app provides dummy checkout URLs.
*   **Email**: If `RESEND_API_KEY` is not set, emails are logged to the console instead of being sent.

---

## 🧪 Testing
Run the full test suite (40+ integration tests):
```bash
pytest tests/ -v
```

---

## 🗺 Roadmap
- [x] Phase 1: Core Logistics & Prediction Engine
- [x] Phase 2: ML & Data Intelligence Layer
- [x] Phase 3: SaaS Monetization & RBAC
- [x] Phase 4: Billing & Audit Logs
- [ ] Phase 5: Scheduled Tasks & Capacity Orchestration

---

© 2026 Axiom Fleet Intelligence.
