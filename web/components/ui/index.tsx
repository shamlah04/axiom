'use client'
// components/ui/index.tsx — all base UI components

import { cn } from '@/lib/utils'
import { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes } from 'react'

// ── Button ────────────────────────────────────────────────
type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
}

const buttonVariants: Record<ButtonVariant, string> = {
  primary:   'bg-cyan-500 hover:bg-cyan-400 text-slate-900 font-semibold',
  secondary: 'bg-slate-700 hover:bg-slate-600 text-slate-100 border border-slate-600',
  danger:    'bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20',
  ghost:     'hover:bg-slate-700/50 text-slate-400 hover:text-slate-100',
}

const buttonSizes: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

export function Button({
  variant = 'primary', size = 'md', loading, children, className, disabled, ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        'rounded-lg transition-all duration-150 inline-flex items-center gap-2',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        buttonVariants[variant], buttonSizes[size], className
      )}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
        </svg>
      )}
      {children}
    </button>
  )
}

// ── Card ──────────────────────────────────────────────────
export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn(
      'bg-slate-800/50 border border-slate-700/50 rounded-xl backdrop-blur-sm',
      className
    )}>
      {children}
    </div>
  )
}

export function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('px-6 py-4 border-b border-slate-700/50', className)}>{children}</div>
}

export function CardContent({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('px-6 py-4', className)}>{children}</div>
}

// ── Badge ─────────────────────────────────────────────────
export function Badge({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border',
      className
    )}>
      {children}
    </span>
  )
}

// ── Input ─────────────────────────────────────────────────
interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export function Input({ label, error, hint, className, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          {label}
        </label>
      )}
      <input
        className={cn(
          'w-full bg-slate-900/50 border rounded-lg px-3 py-2 text-sm text-slate-100',
          'placeholder:text-slate-500 outline-none transition-colors',
          'focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20',
          error ? 'border-red-500/50' : 'border-slate-700',
          className
        )}
        {...props}
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

// ── Select ────────────────────────────────────────────────
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options: { value: string; label: string }[]
}

export function Select({ label, error, options, className, ...props }: SelectProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          {label}
        </label>
      )}
      <select
        className={cn(
          'w-full bg-slate-900/50 border rounded-lg px-3 py-2 text-sm text-slate-100',
          'outline-none transition-colors focus:border-cyan-500/50',
          error ? 'border-red-500/50' : 'border-slate-700',
          className
        )}
        {...props}
      >
        {options.map(o => (
          <option key={o.value} value={o.value} className="bg-slate-900">
            {o.label}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}

// ── Modal ─────────────────────────────────────────────────
export function Modal({
  open, onClose, title, children
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose}/>
      <div className="relative bg-slate-800 border border-slate-700 rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">{title}</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>
  )
}

// ── Empty State ───────────────────────────────────────────
export function EmptyState({ icon, title, description, action }: {
  icon: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">{title}</h3>
      <p className="text-xs text-slate-500 max-w-xs mb-4">{description}</p>
      {action}
    </div>
  )
}

// ── Stat Card ─────────────────────────────────────────────
export function StatCard({ label, value, sub, accent }: {
  label: string
  value: string
  sub?: string
  accent?: string
}) {
  return (
    <Card className="p-5">
      <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={cn('text-2xl font-bold font-mono', accent || 'text-slate-100')}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </Card>
  )
}
