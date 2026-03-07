/** @type {import('next').NextConfig} */
const isMobileExport = process.env.NEXT_EXPORT === 'true'

const nextConfig = {
  // ── Static export for Capacitor (mobile) builds ────────────────────────
  ...(isMobileExport && {
    output: 'export',
    trailingSlash: true, // Required for static hosting / Capacitor
    images: { unoptimized: true }, // next/image doesn't work in static export
  }),

  // ── API proxy ─────────────────────────────────────────────────────────
  // Only active in dev/server mode (not in static export)
  ...(!isMobileExport && {
    async rewrites() {
      return [
        {
          source: '/api/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
        },
        // Serve offline page from public/offline.html
        {
          source: '/offline',
          destination: '/offline.html',
        },
      ]
    },
  }),

  // ── PWA / Mobile headers ───────────────────────────────────────────────
  // Only active in dev/server mode (not in static export)
  ...(!isMobileExport && {
    async headers() {
      return [
        {
          // Service worker must be served from root scope
          source: '/sw.js',
          headers: [
            { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
            { key: 'Service-Worker-Allowed', value: '/' },
          ],
        },
        {
          // Manifest
          source: '/manifest.json',
          headers: [
            { key: 'Cache-Control', value: 'public, max-age=0, must-revalidate' },
          ],
        },
        {
          // Security headers that improve mobile PWA trust
          source: '/(.*)',
          headers: [
            { key: 'X-Content-Type-Options', value: 'nosniff' },
            { key: 'X-Frame-Options', value: 'DENY' },
            { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          ],
        },
      ]
    },
  }),
}

export default nextConfig
