"""
Scenario simulation endpoint — what-if analysis for fleet operators.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.models.models import User
from app.repositories.repositories import TruckRepository, DriverRepository
from app.schemas.schemas import ScenarioInput, ScenarioResult
from app.services.prediction_engine import (
    profit_engine, TruckCostConfig, DriverCostConfig, JobInput
)

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.post("/simulate", response_model=list[ScenarioResult])
async def simulate(
    payload: ScenarioInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    truck_repo = TruckRepository(db)
    driver_repo = DriverRepository(db)

    truck = await truck_repo.get(payload.truck_id, current_user.fleet_id)
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    driver = await driver_repo.get(payload.driver_id, current_user.fleet_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    truck_config = TruckCostConfig(
        fuel_consumption_per_100km=truck.fuel_consumption_per_100km,
        maintenance_cost_per_km=truck.maintenance_cost_per_km,
        insurance_monthly=truck.insurance_monthly,
        leasing_monthly=truck.leasing_monthly or 0.0,
    )
    driver_config = DriverCostConfig(
        hourly_rate=driver.hourly_rate,
        monthly_fixed_cost=driver.monthly_fixed_cost,
    )

    results = []
    distance = payload.distance_km or payload.base_distance_km

    # Baseline scenario
    scenarios = [
        {"label": "Baseline", "offered_rate": payload.base_offered_rate, "fuel_price": payload.base_fuel_price}
    ]

    # Fuel sensitivity scenarios
    for fp in payload.fuel_price_variations:
        scenarios.append({
            "label": f"Fuel @ €{fp:.2f}/L",
            "offered_rate": payload.base_offered_rate,
            "fuel_price": fp,
        })

    # Rate sensitivity scenarios
    for rate in payload.rate_variations:
        scenarios.append({
            "label": f"Rate @ €{rate:.0f}",
            "offered_rate": rate,
            "fuel_price": payload.base_fuel_price,
        })

    for s in scenarios:
        job_input = JobInput(
            distance_km=distance,
            estimated_duration_hours=payload.estimated_duration_hours,
            offered_rate=s["offered_rate"],
            toll_costs=payload.base_toll_costs,
            fuel_price_per_unit=s["fuel_price"],
            other_costs=payload.base_other_costs,
        )
        p = profit_engine.predict(job_input, truck_config, driver_config)
        results.append(ScenarioResult(
            label=s["label"],
            offered_rate=s["offered_rate"],
            fuel_price=s["fuel_price"],
            total_cost=p.total_cost,
            net_profit=p.net_profit,
            margin_pct=p.margin_pct,
            risk_level=p.risk_level,
            recommendation=p.recommendation,
        ))

    return results
