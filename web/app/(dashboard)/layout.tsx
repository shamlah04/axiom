// app/(dashboard)/layout.tsx — Mobile-aware layout with bottom nav
import { Sidebar } from '@/components/layout/Sidebar'
import { MobileNav } from '@/components/layout/MobileNav'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar: hidden on mobile, shown on md+ */}
      <Sidebar />

      {/* Main content: add bottom padding on mobile for the tab bar */}
      <main className="flex-1 overflow-auto pb-20 md:pb-0">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 md:py-8">
          {children}
        </div>
      </main>

      {/* Bottom tab bar: only visible on mobile */}
      <MobileNav />
    </div>
  )
}
