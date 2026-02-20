```mermaid
graph TB
    subgraph Client["Client Layer"]
        UI[Next.js Dashboard]
        API_DOC[OpenAPI / Swagger]
    end

    subgraph API["FastAPI — /api/v1"]
        AUTH[/auth\nRegister · Login · Me]
        FLEETS[/fleets\nCreate · Get]
        TRUCKS[/trucks\nCRUD]
        DRIVERS[/drivers\nCRUD]
        JOBS[/jobs\nCreate+Predict · List · Status · Actual]
        DASH[/dashboard\nKPIs]
        SIM[/scenarios/simulate\nWhat-If]
    end

    subgraph Services["Service Layer (Business Logic)"]
        PE[Profit Prediction Engine\n──────────────\nCost Breakdown\nMargin Calculation\nRisk Scoring\nRecommendation\nExplanation]
        SS[Scenario Simulator\n──────────────\nFleet Growth\nFuel Sensitivity\nBreakeven Analysis]
    end

    subgraph Repos["Repository Layer (Data Access)"]
        UR[UserRepository]
        FR[FleetRepository]
        TR[TruckRepository]
        DR[DriverRepository]
        JR[JobRepository]
    end

    subgraph DB["PostgreSQL"]
        USERS[(users)]
        FLEETS_T[(fleets)]
        TRUCKS_T[(trucks)]
        DRIVERS_T[(drivers)]
        JOBS_T[(jobs)]
    end

    subgraph Auth["Security"]
        JWT[JWT Bearer\nHS256]
        BCRYPT[bcrypt\nPassword Hash]
    end

    UI --> API
    API --> Auth
    AUTH --> UR
    FLEETS --> FR
    TRUCKS --> TR
    DRIVERS --> DR
    JOBS --> PE
    JOBS --> JR
    DASH --> JR
    SIM --> SS

    Repos --> DB

    style PE fill:#4A90D9,color:#fff
    style SS fill:#7B68EE,color:#fff
    style DB fill:#336791,color:#fff
```

## API Route Map

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| POST | `/api/v1/auth/register` | ❌ | Register user |
| POST | `/api/v1/auth/login` | ❌ | Get JWT token |
| GET | `/api/v1/auth/me` | ✅ | Current user |
| POST | `/api/v1/fleets` | ✅ | Create fleet (tenant) |
| GET | `/api/v1/fleets/me` | ✅ | Get my fleet |
| GET | `/api/v1/trucks` | ✅ Fleet | List trucks |
| POST | `/api/v1/trucks` | ✅ Fleet | Add truck |
| PATCH | `/api/v1/trucks/{id}` | ✅ Fleet | Update truck |
| GET | `/api/v1/drivers` | ✅ Fleet | List drivers |
| POST | `/api/v1/drivers` | ✅ Fleet | Add driver |
| **POST** | **`/api/v1/jobs`** | ✅ Fleet | **Create job → instant prediction** |
| GET | `/api/v1/jobs` | ✅ Fleet | List jobs |
| PATCH | `/api/v1/jobs/{id}/status` | ✅ Fleet | Accept / Reject |
| PATCH | `/api/v1/jobs/{id}/actual` | ✅ Fleet | Record actuals |
| GET | `/api/v1/dashboard` | ✅ Fleet | KPI summary |
| POST | `/api/v1/scenarios/simulate` | ✅ Fleet | What-if simulation |

## Prediction Engine — Cost Components

```
Offered Rate (€)
    └── Total Cost (€)
            ├── Fuel Cost = (km / 100) × consumption × price_per_unit
            ├── Driver Cost = hours × hourly_rate
            ├── Maintenance = km × maintenance_cost_per_km
            ├── Toll Costs = (user input)
            ├── Fixed Allocation = (insurance + leasing + driver_fixed) / avg_monthly_km × km
            └── Other Costs = (user input)
                                    ↓
Net Profit = Offered Rate − Total Cost
Margin %   = Net Profit / Offered Rate × 100

Risk Score:
  < 5%  margin → HIGH   → REJECT
  < 15% margin → MEDIUM → REVIEW
  ≥ 15% margin → LOW    → ACCEPT
  (+ fuel > 50% of cost → bump to MEDIUM)
```

## Database Schema (Key Tables)

```
fleets          → id, name, country, subscription_tier, trial_ends_at
users           → id, email, hashed_password, fleet_id (FK)
trucks          → id, fleet_id (FK), fuel_type, costs...
drivers         → id, fleet_id (FK), hourly_rate, monthly_fixed_cost
jobs            → id, fleet_id, truck_id, driver_id
                  inputs: distance, duration, offered_rate, tolls, fuel_price
                  outputs: total_cost, net_profit, margin_pct, risk_level,
                           recommendation, ai_explanation
                  actuals: actual_revenue, actual_cost (post-completion)
```

## Phase 2 Extension Points

The `ProfitPredictionEngine.predict()` method signature stays the same. In Phase 2:
- Replace `_calculate_costs` internals with trained regression model
- Replace `_score_risk` with ML classifier
- Add anomaly detection on `actual vs predicted` deltas
- Feed actuals back into training pipeline
