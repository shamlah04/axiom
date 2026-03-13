#!/usr/bin/env node
// scripts/dev-https.mjs
// Starts Next.js dev server with HTTPS so PWA features work on mobile.
//
// SETUP (one time):
//   1. Install mkcert: https://github.com/FiloSottile/mkcert#installation
//      - Mac:     brew install mkcert && mkcert -install
//      - Windows: choco install mkcert  (or scoop install mkcert)
//      - Linux:   sudo apt install libnss3-tools && brew install mkcert
//   2. Run: node scripts/dev-https.mjs --setup
//   3. Then run: npm run dev:https
//
// USAGE ON MOBILE:
//   - Find your computer's local IP: ipconfig (Win) / ifconfig (Mac/Linux)
//   - Open https://<YOUR_IP>:3000 in Safari (iPhone) or Chrome (Android)
//   - Both devices must be on the same WiFi network

import { execSync, spawn } from 'child_process'
import { existsSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const CERT_DIR = join(__dirname, '../.certs')
const CERT_FILE = join(CERT_DIR, 'localhost.pem')
const KEY_FILE  = join(CERT_DIR, 'localhost-key.pem')

const args = process.argv.slice(2)

// ── Setup: generate certs ──────────────────────────────────────────────────
if (args.includes('--setup')) {
  console.log('🔐 Setting up local HTTPS certificates...\n')

  // Check mkcert is installed
  try {
    execSync('mkcert --version', { stdio: 'pipe' })
  } catch {
    console.error('❌ mkcert not found. Install it first:')
    console.error('   Mac:     brew install mkcert && mkcert -install')
    console.error('   Windows: choco install mkcert')
    console.error('   Linux:   see https://github.com/FiloSottile/mkcert\n')
    process.exit(1)
  }

  mkdirSync(CERT_DIR, { recursive: true })

  // Get local IP for mobile access
  let localIP = 'localhost'
  try {
    const { networkInterfaces } = await import('os')
    const nets = networkInterfaces()
    for (const iface of Object.values(nets)) {
      for (const net of iface) {
        if (net.family === 'IPv4' && !net.internal) {
          localIP = net.address
          break
        }
      }
      if (localIP !== 'localhost') break
    }
  } catch {}

  console.log(`📱 Your local IP: ${localIP}`)
  console.log(`   Mobile devices will access: https://${localIP}:3000\n`)

  execSync(
    `mkcert -cert-file "${CERT_FILE}" -key-file "${KEY_FILE}" localhost 127.0.0.1 ${localIP}`,
    { stdio: 'inherit' }
  )

  console.log('\n✅ Certificates generated!')
  console.log('   Run: npm run dev:https')
  process.exit(0)
}

// ── Start HTTPS dev server ─────────────────────────────────────────────────
if (!existsSync(CERT_FILE) || !existsSync(KEY_FILE)) {
  console.error('❌ SSL certificates not found.')
  console.error('   Run setup first: node scripts/dev-https.mjs --setup\n')
  process.exit(1)
}

// Get local IP for display
let localIP = 'localhost'
try {
  const { networkInterfaces } = await import('os')
  const nets = networkInterfaces()
  for (const iface of Object.values(nets)) {
    for (const net of iface) {
      if (net.family === 'IPv4' && !net.internal) {
        localIP = net.address
        break
      }
    }
    if (localIP !== 'localhost') break
  }
} catch {}

console.log('🚀 Starting Axiom dev server with HTTPS...\n')
console.log(`   Local:   https://localhost:3000`)
console.log(`   Mobile:  https://${localIP}:3000`)
console.log(`\n   ⚠️  Make sure your phone is on the same WiFi network`)
console.log(`   ⚠️  FastAPI backend must be running: uvicorn app.main:app --reload\n`)

// Start Next.js with HTTPS using the custom server approach
const env = {
  ...process.env,
  NODE_TLS_REJECT_UNAUTHORIZED: '0',
}

const next = spawn(
  'node_modules/.bin/next',
  ['dev', '--experimental-https',
   `--experimental-https-key=${KEY_FILE}`,
   `--experimental-https-cert=${CERT_FILE}`],
  { stdio: 'inherit', env, shell: true }
)

next.on('close', (code) => process.exit(code))
process.on('SIGINT', () => { next.kill('SIGINT'); process.exit(0) })
