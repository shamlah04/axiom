'use client'
// components/charts/CostBreakdownChart.tsx
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts'
import type { JobPredictionResult } from '@/types/api'

const COLORS = ['#06b6d4', '#8b5cf6', '#f59e0b', '#ef4444', '#10b981', '#64748b']

export function CostBreakdownChart({ prediction }: { prediction: JobPredictionResult }) {
  const data = [
    { name: 'Fuel',        value: prediction.fuel_cost },
    { name: 'Driver',      value: prediction.driver_cost },
    { name: 'Maintenance', value: prediction.maintenance_cost },
    { name: 'Tolls',       value: prediction.toll_costs },
    { name: 'Fixed',       value: prediction.fixed_cost_allocation },
    { name: 'Other',       value: prediction.other_costs },
  ].filter(d => d.value > 0)

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" innerRadius={55} outerRadius={80}
          dataKey="value" paddingAngle={2}>
          {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Pie>
        <Tooltip
          contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }}
          formatter={(value: number) => [`€${value.toFixed(2)}`, '']}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: '#64748b' }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
