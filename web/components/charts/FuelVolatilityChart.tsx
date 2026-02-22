'use client'
// components/charts/FuelVolatilityChart.tsx
import {
  ResponsiveContainer, ComposedChart, Bar, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts'
import { monthLabel } from '@/lib/utils'
import type { FuelVolatilityMonth } from '@/types/api'

export function FuelVolatilityChart({ data }: { data: FuelVolatilityMonth[] }) {
  const chartData = data.map(d => ({
    month: monthLabel(d.year, d.month),
    'Fuel price (€/L)': d.avg_fuel_price,
    'Margin %': d.avg_margin_pct,
    'Price range': d.fuel_price_range,
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis yAxisId="left" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis yAxisId="right" orientation="right" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: '#64748b' }} />
        <Bar yAxisId="left" dataKey="Fuel price (€/L)" fill="#f59e0b" opacity={0.6} />
        <Line yAxisId="right" type="monotone" dataKey="Margin %" stroke="#10b981" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
