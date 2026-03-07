#!/usr/bin/env node
// scripts/generate-icons.mjs
// Generates all required PWA icon sizes from a base SVG
// Run: node scripts/generate-icons.mjs
// Requires: npm install sharp --save-dev

import sharp from 'sharp'
import { mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const OUT_DIR = join(__dirname, '../public/icons')

mkdirSync(OUT_DIR, { recursive: true })

// Base SVG — Axiom "A" logo
const SVG = `
<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" rx="112" fill="#06b6d4"/>
  <text x="256" y="360" font-family="system-ui, -apple-system, sans-serif"
        font-size="300" font-weight="900" text-anchor="middle" fill="#0f172a">A</text>
</svg>
`

const SIZES = [72, 96, 128, 144, 152, 180, 192, 384, 512]

async function generateIcons() {
  console.log('Generating PWA icons...')
  const buffer = Buffer.from(SVG)

  for (const size of SIZES) {
    const output = join(OUT_DIR, `icon-${size}x${size}.png`)
    await sharp(buffer)
      .resize(size, size)
      .png()
      .toFile(output)
    console.log(`  ✓ icon-${size}x${size}.png`)
  }

  // Also generate favicon size
  await sharp(buffer).resize(32, 32).png().toFile(join(OUT_DIR, 'icon-32x32.png'))
  console.log('  ✓ icon-32x32.png')

  // Generate iPhone 14 Pro Max splash screen
  const splashSVG = `
  <svg width="1290" height="2796" xmlns="http://www.w3.org/2000/svg">
    <rect width="1290" height="2796" fill="#0f172a"/>
    <rect x="567" y="1298" width="156" height="156" rx="35" fill="#06b6d4"/>
    <text x="645" y="1405" font-family="system-ui, sans-serif"
          font-size="84" font-weight="900" text-anchor="middle" fill="#0f172a">A</text>
  </svg>`

  await sharp(Buffer.from(splashSVG))
    .resize(1290, 2796)
    .png()
    .toFile(join(OUT_DIR, 'splash-1290x2796.png'))
  console.log('  ✓ splash-1290x2796.png (iPhone 14 Pro Max)')

  console.log('\n✅ All icons generated in public/icons/')
}

generateIcons().catch(console.error)
