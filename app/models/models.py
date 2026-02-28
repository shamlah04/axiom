"""
SQLAlchemy ORM models for FCIP Phase 1.

Multi-tenant: every entity belongs to a Fleet (tenant).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, String, Text, Enum, UUID
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

import enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FuelType(str, enum.Enum):
    diesel = "diesel"
    petrol = "petrol"
    electric = "electric"
    hybrid = "hybrid"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class JobRecommendation(str, enum.Enum):
    accept = "accept"
    review = "review"
    reject = "reject"


class SubscriptionTier(str, enum.Enum):
    tier1 = "tier1"   # 1-2 trucks
    tier2 = "tier2"   # 3-10 trucks
    tier3 = "tier3"   # enterprise


# ---------------------------------------------------------------------------
# User / Auth
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(50), nullable=True, default="owner")  # UserRole: owner | dispatcher | viewer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fleet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fleets.id"), nullable=True)
    fleet: Mapped["Fleet"] = relationship(back_populates="users")


# ---------------------------------------------------------------------------
# Fleet (Tenant)
# ---------------------------------------------------------------------------

class Fleet(Base):
    __tablename__ = "fleets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(10), default="DK")
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), default=SubscriptionTier.tier1
    )
    trial_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="fleet")
    trucks: Mapped[list["Truck"]] = relationship(back_populates="fleet", cascade="all, delete-orphan")
    drivers: Mapped[list["Driver"]] = relationship(back_populates="fleet", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship(back_populates="fleet", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Truck
# ---------------------------------------------------------------------------

class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fleets.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    license_plate: Mapped[str] = mapped_column(String(30), nullable=True)
    fuel_type: Mapped[FuelType] = mapped_column(Enum(FuelType), default=FuelType.diesel)

    # Cost inputs (per km or per month)
    fuel_consumption_per_100km: Mapped[float] = mapped_column(Float, nullable=False)  # litres or kWh
    maintenance_cost_per_km: Mapped[float] = mapped_column(Float, nullable=False)     # EUR
    insurance_monthly: Mapped[float] = mapped_column(Float, nullable=False)           # EUR
    leasing_monthly: Mapped[float] = mapped_column(Float, nullable=True, default=0.0) # EUR

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_trucks_fleet_id", "fleet_id"),)

    fleet: Mapped["Fleet"] = relationship(back_populates="trucks")
    jobs: Mapped[list["Job"]] = relationship(back_populates="truck")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fleets.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False)       # EUR/hour
    monthly_fixed_cost: Mapped[float] = mapped_column(Float, default=0.0)  # EUR
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_drivers_fleet_id", "fleet_id"),)

    fleet: Mapped["Fleet"] = relationship(back_populates="drivers")
    jobs: Mapped[list["Job"]] = relationship(back_populates="driver")


# ---------------------------------------------------------------------------
# Job (Trip)
# ---------------------------------------------------------------------------

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fleet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fleets.id"), nullable=False)
    truck_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trucks.id"), nullable=False)
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False)

    # Route info
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_duration_hours: Mapped[float] = mapped_column(Float, nullable=False)

    # Cost inputs
    offered_rate: Mapped[float] = mapped_column(Float, nullable=False)       # EUR — what customer pays
    toll_costs: Mapped[float] = mapped_column(Float, default=0.0)            # EUR
    fuel_price_per_unit: Mapped[float] = mapped_column(Float, nullable=False) # EUR/litre or EUR/kWh
    other_costs: Mapped[float] = mapped_column(Float, default=0.0)           # EUR

    # Computed outputs (stored after prediction)
    total_cost: Mapped[float] = mapped_column(Float, nullable=True)
    net_profit: Mapped[float] = mapped_column(Float, nullable=True)
    margin_pct: Mapped[float] = mapped_column(Float, nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=True)
    recommendation: Mapped[JobRecommendation] = mapped_column(Enum(JobRecommendation), nullable=True)
    ai_explanation: Mapped[str] = mapped_column(Text, nullable=True)

    # Actual outcome (filled after job completion)
    actual_revenue: Mapped[float] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[float] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending/accepted/rejected/completed
    job_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_jobs_fleet_id", "fleet_id"),)

    fleet: Mapped["Fleet"] = relationship(back_populates="jobs")
    truck: Mapped["Truck"] = relationship(back_populates="jobs")
    driver: Mapped["Driver"] = relationship(back_populates="jobs")
