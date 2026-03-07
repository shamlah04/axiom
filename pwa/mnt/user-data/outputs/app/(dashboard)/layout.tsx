// app/(dashboard)/layout.tsx  — replace existing with this mobile-aware version
import { Sidebar } from '@/components/layout/Sidebar'
import { MobileNav } from '@/components/layout/MobileNav'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen min-h-dvh">
      {/* Sidebar — hidden on mobile, visible md+ */}
      <div className="hidden md:block">
        <Sidebar />
      </div>

      {/* Main content */}
      <main className="flex-1 overflow-auto"
            style={{ paddingTop: 'env(safe-area-inset-top)' }}>
        {/* Mobile top bar */}
        <div className="flex items-center px-4 py-3 border-b border-slate-800 md:hidden">
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

        {/* Page content — extra bottom padding on mobile for nav bar */}
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-4 md:py-8
                        pb-24 md:pb-8">
          {children}
        </div>
      </main>

      {/* Bottom tab bar — mobile only */}
      <MobileNav />
    </div>
  )
}
