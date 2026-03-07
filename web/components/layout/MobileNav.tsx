'use client'
// components/layout/MobileNav.tsx
// Bottom tab bar for mobile — replaces sidebar on small screens

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const tabs = [
  { href: '/dashboard', label: 'Home', icon: '◈' },
  { href: '/jobs', label: 'Jobs', icon: '⟁' },
  { href: '/trucks', label: 'Fleet', icon: '⬡' },
  { href: '/analytics', label: 'Analytics', icon: '◉' },
  { href: '/scenarios', label: 'Scenarios', icon: '◎' },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    // Safe-area inset handles iPhone home indicator
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-slate-900/95 backdrop-blur-md border-t border-slate-800 flex md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
      {tabs.map((tab) => {
        const active = pathname.startsWith(tab.href)
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={[
              'relative flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors',
              active ? 'text-cyan-400' : 'text-slate-500'
            ].join(' ')}
          >
            <span className="text-xl leading-none">{tab.icon}</span>
            <span className="text-[10px] font-medium tracking-wide">{tab.label}</span>
            {active && (
              <span className="absolute bottom-0 w-6 h-0.5 bg-cyan-500 rounded-full" />
            )}
          </Link>
        )
      })}
    </nav>
  )
}
