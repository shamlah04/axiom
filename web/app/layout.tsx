// app/layout.tsx  — PWA-enhanced root layout
import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { InstallBanner } from '@/components/pwa/InstallBanner'

const inter = Inter({ subsets: ['latin'] })

// ── PWA / Mobile metadata ──────────────────────────────────────────────────
export const metadata: Metadata = {
  title: 'Axiom — Fleet Intelligence',
  description: 'AI-powered fleet management and profit prediction',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Axiom',
    startupImage: [
      // iPhone 14 Pro Max
      { url: '/icons/splash-1290x2796.png', media: '(device-width: 430px) and (device-height: 932px)' },
      // iPhone 14 / 13 / 12
      { url: '/icons/splash-1170x2532.png', media: '(device-width: 390px) and (device-height: 844px)' },
      // iPhone SE
      { url: '/icons/splash-750x1334.png', media: '(device-width: 375px) and (device-height: 667px)' },
    ],
  },
  other: {
    'mobile-web-app-capable': 'yes',
    'msapplication-TileColor': '#0f172a',
    'msapplication-tap-highlight': 'no',
  },
  icons: {
    icon: [
      { url: '/icons/icon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icons/icon-96x96.png', sizes: '96x96', type: 'image/png' },
      { url: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
    ],
    apple: [
      { url: '/icons/icon-152x152.png', sizes: '152x152', type: 'image/png' },
      { url: '/icons/icon-180x180.png', sizes: '180x180', type: 'image/png' },
    ],
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,          // Prevents accidental zoom in form fields on iOS
  userScalable: false,
  viewportFit: 'cover',     // Fills iPhone notch / Dynamic Island area
  themeColor: [
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
    { media: '(prefers-color-scheme: light)', color: '#06b6d4' },
  ],
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100 antialiased`}>
        {children}
        {/* PWA install prompt — shows on mobile automatically */}
        <InstallBanner />
      </body>
    </html>
  )
}
