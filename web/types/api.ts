// types/api.ts
// TypeScript types mirroring all FCIP backend Pydantic schemas

export type FuelType = 'diesel' | 'petrol' | 'electric' | 'hybrid'
export type RiskLevel = 'low' | 'medium' | 'high'
export type JobRecommendation = 'accept' | 'review' | 'reject'
export type JobStatus = 'pending' | 'accepted' | 'rejected' | 'completed'
export type SubscriptionTier = 'tier1' | 'tier2' | 'tier3'

// ── Auth ─────────────────────────────────────────────────
export interface Token {
  access_token: string
  token_type: string
}

export interface UserOut {
  id: string
  email: string
  full_name: string
  fleet_id: string | null
  created_at: string
}

export interface UserRegister {
  email: string
  password: string
  full_name: string
}

// ── Fleet ────────────────────────────────────────────────
export interface FleetCreate {
  name: string
  country: string
  subscription_tier: SubscriptionTier
}

export interface FleetOut {
  id: string
  name: string
  country: string
  subscription_tier: SubscriptionTier
  trial_ends_at: string | null
  created_at: string
}

// ── Truck ────────────────────────────────────────────────
export interface TruckCreate {
  name: string
  license_plate?: string
  fuel_type: FuelType
  fuel_consumption_per_100km: number
  maintenance_cost_per_km: number
  insurance_monthly: number
  leasing_monthly: number
}

export interface TruckUpdate extends Partial<TruckCreate> {
  is_active?: boolean
}

export interface TruckOut extends TruckCreate {
  id: string
  fleet_id: string
  is_active: boolean
  created_at: string
}

// ── Driver ───────────────────────────────────────────────
export interface DriverCreate {
  name: string
  hourly_rate: number
  monthly_fixed_cost: number
}

export interface DriverOut extends DriverCreate {
  id: string
  fleet_id: string
  is_active: boolean
  created_at: string
}

// ── Job ──────────────────────────────────────────────────
export interface JobCreate {
  truck_id: string
  driver_id: string
  origin: string
  destination: string
  distance_km: number
  estimated_duration_hours: number
  offered_rate: number
  toll_costs: number
  fuel_price_per_unit: number
  other_costs: number
  job_date?: string
}

export interface JobPredictionResult {
  job_id: string
  total_cost: number
  net_profit: number
  margin_pct: number
  risk_level: RiskLevel
  recommendation: JobRecommendation
  ai_explanation: string
  // Cost breakdown
  fuel_cost: number
  driver_cost: number
  maintenance_cost: number
  toll_costs: number
  fixed_cost_allocation: number
  other_costs: number
}

export interface JobOut {
  id: string
  fleet_id: string
  truck_id: string
  driver_id: string
  origin: string
  destination: string
  distance_km: number
  offered_rate: number
  total_cost: number | null
  net_profit: number | null
  margin_pct: number | null
  risk_level: RiskLevel | null
  recommendation: JobRecommendation | null
  ai_explanation: string | null
  actual_revenue: number | null
  actual_cost: number | null
  status: JobStatus
  job_date: string | null
  created_at: string
}

// ── Dashboard ────────────────────────────────────────────
export interface DashboardSummary {
  total_jobs: number
  accepted_jobs: number
  rejected_jobs: number
  total_revenue: number
  total_cost: number
  total_profit: number
  avg_margin_pct: number
  high_risk_jobs: number
}

// ── Analytics ────────────────────────────────────────────
export interface MonthlyTrend {
  year: number
  month: number
  job_count: number
  accepted_count: number
  rejected_count: number
  total_revenue: number
  total_cost: number
  total_profit: number
  avg_margin_pct: number
}

export interface TopRoute {
  origin: string
  destination: string
  job_count: number
  avg_margin_pct: number
  avg_net_profit: number
  avg_rate: number
  avg_cost: number
  avg_distance_km: number
}

export interface FuelVolatilityMonth {
  year: number
  month: number
  job_count: number
  avg_fuel_price: number
  min_fuel_price: number
  max_fuel_price: number
  fuel_price_range: number
  avg_margin_pct: number
  avg_total_cost: number
  avg_rate: number
}

// ── Scenarios ────────────────────────────────────────────
export interface ScenarioInput {
  base_monthly_revenue: number
  base_monthly_cost: number
  additional_trucks: number
  fuel_price_change_pct: number
  additional_driver_cost: number
}

export interface ScenarioResult {
  projected_revenue: number
  projected_cost: number
  projected_profit: number
  projected_margin_pct: number
  breakeven_jobs_needed: number
  notes: string[]
}
