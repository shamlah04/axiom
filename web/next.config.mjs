/** @type {import('next').NextConfig} */
const nextConfig = {
  // ── API proxy ─────────────────────────────────────────────────────────
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

  // ── PWA / Mobile headers ───────────────────────────────────────────────
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
}

export default nextConfig
