"""
Profit Prediction Engine — Phase 1 (Deterministic / Regression-ready)

This module is the core AI layer for Phase 1. It:
1. Calculates all cost components
2. Computes net profit and margin
3. Scores risk based on heuristic rules
4. Produces a human-readable explanation

Designed to be replaced/augmented by ML models in Phase 2 without
changing the API contract.
"""

from dataclasses import dataclass

from app.models.models import RiskLevel, JobRecommendation


# ---------------------------------------------------------------------------
# Data classes (decoupled from ORM/Pydantic — pure domain logic)
# ---------------------------------------------------------------------------

@dataclass
class TruckCostConfig:
    fuel_consumption_per_100km: float   # litres or kWh
    maintenance_cost_per_km: float      # EUR
    insurance_monthly: float            # EUR
    leasing_monthly: float              # EUR
    working_days_per_month: int = 22


@dataclass
class DriverCostConfig:
    hourly_rate: float
    monthly_fixed_cost: float


@dataclass
class JobInput:
    distance_km: float
    estimated_duration_hours: float
    offered_rate: float
    toll_costs: float
    fuel_price_per_unit: float
    other_costs: float


@dataclass
class CostBreakdown:
    fuel_cost: float
    driver_cost: float
    maintenance_cost: float
    toll_costs: float
    fixed_cost_allocation: float
    other_costs: float

    @property
    def total(self) -> float:
        return (
            self.fuel_cost
            + self.driver_cost
            + self.maintenance_cost
            + self.toll_costs
            + self.fixed_cost_allocation
            + self.other_costs
        )


@dataclass
class PredictionOutput:
    cost_breakdown: CostBreakdown
    total_cost: float
    net_profit: float
    margin_pct: float
    risk_level: RiskLevel
    recommendation: JobRecommendation
    explanation: str


# ---------------------------------------------------------------------------
# Prediction Engine
# ---------------------------------------------------------------------------

class ProfitPredictionEngine:
    """
    Deterministic profit prediction engine.

    Phase 1: rule-based with clear extension points for Phase 2 ML.
    """

    # Risk thresholds
    MARGIN_HIGH_RISK_THRESHOLD = 5.0    # below 5% margin → high risk
    MARGIN_MEDIUM_RISK_THRESHOLD = 15.0 # below 15% margin → medium risk

    # Recommendation thresholds
    REJECT_MARGIN = 0.0        # no profit → reject
    REVIEW_MARGIN = 10.0       # below 10% margin → review

    def predict(
        self,
        job: JobInput,
        truck: TruckCostConfig,
        driver: DriverCostConfig,
    ) -> PredictionOutput:
        # Guard against nonsense inputs
        if job.distance_km <= 0:
            raise ValueError(f"distance_km must be positive, got {job.distance_km}")
        if job.estimated_duration_hours <= 0:
            raise ValueError(f"estimated_duration_hours must be positive, got {job.estimated_duration_hours}")
        if job.offered_rate <= 0:
            raise ValueError(f"offered_rate must be positive, got {job.offered_rate}")
        if job.fuel_price_per_unit < 0:
            raise ValueError(f"fuel_price_per_unit cannot be negative, got {job.fuel_price_per_unit}")

        breakdown = self._calculate_costs(job, truck, driver)
        total_cost = breakdown.total
        net_profit = job.offered_rate - total_cost
        margin_pct = (net_profit / job.offered_rate * 100) if job.offered_rate > 0 else 0.0

        risk_level = self._score_risk(margin_pct, job, breakdown)
        recommendation = self._recommend(margin_pct, risk_level)
        explanation = self._explain(margin_pct, risk_level, recommendation, breakdown, job)

        return PredictionOutput(
            cost_breakdown=breakdown,
            total_cost=round(total_cost, 2),
            net_profit=round(net_profit, 2),
            margin_pct=round(margin_pct, 2),
            risk_level=risk_level,
            recommendation=recommendation,
            explanation=explanation,
        )

    # ------------------------------------------------------------------

    def _calculate_costs(
        self,
        job: JobInput,
        truck: TruckCostConfig,
        driver: DriverCostConfig,
    ) -> CostBreakdown:
        # Fuel cost
        fuel_cost = (job.distance_km / 100) * truck.fuel_consumption_per_100km * job.fuel_price_per_unit

        # Driver cost
        driver_cost = job.estimated_duration_hours * driver.hourly_rate

        # Maintenance cost
        maintenance_cost = job.distance_km * truck.maintenance_cost_per_km

        # Fixed cost allocation: insurance + leasing spread across working day (avg 400 km/day assumed)
        avg_km_per_month = truck.working_days_per_month * 400
        fixed_monthly = truck.insurance_monthly + truck.leasing_monthly + driver.monthly_fixed_cost
        fixed_cost_per_km = fixed_monthly / avg_km_per_month if avg_km_per_month > 0 else 0
        fixed_cost_allocation = fixed_cost_per_km * job.distance_km

        return CostBreakdown(
            fuel_cost=round(fuel_cost, 2),
            driver_cost=round(driver_cost, 2),
            maintenance_cost=round(maintenance_cost, 2),
            toll_costs=round(job.toll_costs, 2),
            fixed_cost_allocation=round(fixed_cost_allocation, 2),
            other_costs=round(job.other_costs, 2),
        )

    def _score_risk(
        self, margin_pct: float, job: JobInput, breakdown: CostBreakdown
    ) -> RiskLevel:
        if margin_pct < self.MARGIN_HIGH_RISK_THRESHOLD:
            return RiskLevel.high
        if margin_pct < self.MARGIN_MEDIUM_RISK_THRESHOLD:
            return RiskLevel.medium
        # Additional risk signals
        fuel_pct_of_cost = breakdown.fuel_cost / breakdown.total if breakdown.total > 0 else 0
        if fuel_pct_of_cost > 0.50:
            # Fuel dominates — sensitive to price volatility
            return RiskLevel.medium
        return RiskLevel.low

    def _recommend(self, margin_pct: float, risk_level: RiskLevel) -> JobRecommendation:
        if margin_pct <= self.REJECT_MARGIN:
            return JobRecommendation.reject
        if margin_pct < self.REVIEW_MARGIN or risk_level == RiskLevel.high:
            return JobRecommendation.review
        return JobRecommendation.accept

    def _explain(
        self,
        margin_pct: float,
        risk_level: RiskLevel,
        recommendation: JobRecommendation,
        breakdown: CostBreakdown,
        job: JobInput,
    ) -> str:
        lines = [
            f"Margin is {margin_pct:.1f}% ({risk_level.value} risk).",
        ]

        # Identify biggest cost driver
        costs = {
            "fuel": breakdown.fuel_cost,
            "driver": breakdown.driver_cost,
            "maintenance": breakdown.maintenance_cost,
            "tolls": breakdown.toll_costs,
            "fixed allocation": breakdown.fixed_cost_allocation,
        }
        top_cost = max(costs, key=costs.get)
        lines.append(f"Largest cost component: {top_cost} (€{costs[top_cost]:.2f}).")

        if recommendation == JobRecommendation.reject:
            lines.append("This job does not cover total costs. Rejection recommended.")
        elif recommendation == JobRecommendation.review:
            lines.append(
                "Margin is thin. Consider negotiating a higher rate or reducing toll/other costs."
            )
        else:
            lines.append("Job appears profitable. Acceptance recommended.")

        return " ".join(lines)


# Singleton — stateless, safe to share
profit_engine = ProfitPredictionEngine()
