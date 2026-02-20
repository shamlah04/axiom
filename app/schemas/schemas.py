"""
Pydantic schemas for all request and response models.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.models import FuelType, RiskLevel, JobRecommendation, SubscriptionTier


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    fleet_id: Optional[uuid.UUID]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Fleet
# ---------------------------------------------------------------------------

class FleetCreate(BaseModel):
    name: str
    country: str = "DK"
    subscription_tier: SubscriptionTier = SubscriptionTier.tier1


class FleetOut(BaseModel):
    id: uuid.UUID
    name: str
    country: str
    subscription_tier: SubscriptionTier
    trial_ends_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Truck
# ---------------------------------------------------------------------------

class TruckCreate(BaseModel):
    name: str
    license_plate: Optional[str] = None
    fuel_type: FuelType = FuelType.diesel
    fuel_consumption_per_100km: float
    maintenance_cost_per_km: float
    insurance_monthly: float
    leasing_monthly: float = 0.0


class TruckUpdate(BaseModel):
    name: Optional[str] = None
    license_plate: Optional[str] = None
    fuel_type: Optional[FuelType] = None
    fuel_consumption_per_100km: Optional[float] = None
    maintenance_cost_per_km: Optional[float] = None
    insurance_monthly: Optional[float] = None
    leasing_monthly: Optional[float] = None
    is_active: Optional[bool] = None


class TruckOut(BaseModel):
    id: uuid.UUID
    fleet_id: uuid.UUID
    name: str
    license_plate: Optional[str]
    fuel_type: FuelType
    fuel_consumption_per_100km: float
    maintenance_cost_per_km: float
    insurance_monthly: float
    leasing_monthly: Optional[float]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

class DriverCreate(BaseModel):
    name: str
    hourly_rate: float
    monthly_fixed_cost: float = 0.0


class DriverOut(BaseModel):
    id: uuid.UUID
    fleet_id: uuid.UUID
    name: str
    hourly_rate: float
    monthly_fixed_cost: float
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class JobCreate(BaseModel):
    truck_id: uuid.UUID
    driver_id: uuid.UUID
    origin: str
    destination: str
    distance_km: float
    estimated_duration_hours: float
    offered_rate: float
    toll_costs: float = 0.0
    fuel_price_per_unit: float
    other_costs: float = 0.0
    job_date: Optional[datetime] = None


class JobOut(BaseModel):
    id: uuid.UUID
    fleet_id: uuid.UUID
    truck_id: uuid.UUID
    driver_id: uuid.UUID
    origin: str
    destination: str
    distance_km: float
    estimated_duration_hours: float
    offered_rate: float
    toll_costs: float
    fuel_price_per_unit: float
    other_costs: float
    total_cost: Optional[float]
    net_profit: Optional[float]
    margin_pct: Optional[float]
    risk_level: Optional[RiskLevel]
    recommendation: Optional[JobRecommendation]
    ai_explanation: Optional[str]
    actual_revenue: Optional[float]
    actual_cost: Optional[float]
    status: str
    job_date: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class JobPredictionResult(BaseModel):
    job_id: uuid.UUID
    total_cost: float
    net_profit: float
    margin_pct: float
    risk_level: RiskLevel
    recommendation: JobRecommendation
    ai_explanation: str
    # Cost breakdown
    fuel_cost: float
    driver_cost: float
    maintenance_cost: float
    toll_costs: float
    fixed_cost_allocation: float
    other_costs: float


class JobStatusUpdate(BaseModel):
    status: str  # pending / accepted / rejected / completed


class JobActualUpdate(BaseModel):
    actual_revenue: float
    actual_cost: float


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardKPI(BaseModel):
    total_jobs: int
    accepted_jobs: int
    rejected_jobs: int
    completed_jobs: int
    avg_margin_pct: Optional[float]
    total_revenue: Optional[float]
    total_profit: Optional[float]


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

class ScenarioInput(BaseModel):
    base_distance_km: float
    base_offered_rate: float
    base_fuel_price: float
    base_toll_costs: float = 0.0
    base_other_costs: float = 0.0
    truck_id: uuid.UUID
    driver_id: uuid.UUID
    # What-if parameters
    fuel_price_variations: list[float] = []   # list of alternative fuel prices
    rate_variations: list[float] = []          # list of alternative offered rates
    distance_km: Optional[float] = None        # override distance
    estimated_duration_hours: float = 8.0


class ScenarioResult(BaseModel):
    label: str
    offered_rate: float
    fuel_price: float
    total_cost: float
    net_profit: float
    margin_pct: float
    risk_level: RiskLevel
    recommendation: JobRecommendation
