'use client'
// components/layout/Sidebar.tsx
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const nav = [
  { href: '/dashboard',  label: 'Dashboard',  icon: '◈' },
  { href: '/jobs',       label: 'Jobs',        icon: '⟁' },
  { href: '/trucks',     label: 'Fleet',       icon: '⬡' },
  { href: '/analytics',  label: 'Analytics',   icon: '◉' },
  { href: '/scenarios',  label: 'Scenarios',   icon: '◎' },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-56 min-h-screen bg-slate-900 border-r border-slate-800 flex flex-col">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-cyan-500 rounded-lg flex items-center justify-center">
            <span className="text-slate-900 text-xs font-black">A</span>
          </div>
          <div>
            <p className="text-sm font-bold text-slate-100 tracking-tight">Axiom</p>
            <p className="text-[10px] text-slate-500">Fleet Intelligence</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map(item => {
          const active = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all',
                active
                  ? 'bg-cyan-500/10 text-cyan-400 font-medium'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'
              )}
            >
              <span className="text-base leading-none">{item.icon}</span>
              {item.label}
              {active && (
                <span className="ml-auto w-1 h-4 bg-cyan-500 rounded-full"/>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Bottom */}
      <div className="px-3 py-4 border-t border-slate-800">
        <Link
          href="/login"
          onClick={() => { if (typeof window !== 'undefined') localStorage.removeItem('fcip_token') }}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 transition-all w-full"
        >
          <span>⎋</span> Sign out
        </Link>
      </div>
    </aside>
  )
}
