# Axiom — Mobile App Conversion Guide

## Overview

This guide converts Axiom Fleet Intelligence into a **Progressive Web App (PWA)** — installable on both Android and iPhone from the browser, with no App Store required. Users get a native-feeling app icon, full-screen experience, and offline support.

---

## What's Included

| File | Purpose |
|------|---------|
| `public/manifest.json` | Tells browsers this is an installable app |
| `public/sw.js` | Service worker: caching, offline support |
| `public/offline.html` | Shown when user is offline |
| `app/layout.tsx` | Root layout with all PWA meta tags |
| `app/(dashboard)/layout.tsx` | Mobile-aware layout with bottom nav |
| `components/pwa/InstallBanner.tsx` | "Add to Home Screen" prompt |
| `components/layout/MobileNav.tsx` | Bottom tab bar for mobile |
| `hooks/usePWA.ts` | Service worker registration + install logic |
| `next.config.mjs` | Updated config with PWA headers |
| `app/mobile-globals.css` | Mobile CSS (safe areas, touch, viewport) |
| `scripts/generate-icons.mjs` | Auto-generates all icon sizes |

---

## Step-by-Step Installation

### 1. Copy files into your `web/` project

```
web/
├── public/
│   ├── manifest.json           ← copy
│   ├── sw.js                   ← copy
│   └── offline.html            ← copy
├── app/
│   ├── layout.tsx              ← replace existing
│   ├── mobile-globals.css      ← add import to globals.css
│   └── (dashboard)/
│       └── layout.tsx          ← replace existing
├── components/
│   ├── layout/
│   │   └── MobileNav.tsx       ← new file
│   └── pwa/
│       └── InstallBanner.tsx   ← new file
├── hooks/
│   └── usePWA.ts               ← new file
├── next.config.mjs             ← replace existing
└── scripts/
    └── generate-icons.mjs      ← new file
```

### 2. Add mobile CSS to globals.css

Open `app/globals.css` and add at the bottom:

```css
@import './mobile-globals.css';
```

### 3. Generate app icons

```bash
cd web
npm install sharp --save-dev
node scripts/generate-icons.mjs
```

This creates all required icons in `public/icons/`:
- 72×72, 96×96, 128×128, 144×144, 152×152, 192×192, 384×384, 512×512 PNG
- 32×32 favicon
- 1290×2796 iPhone splash screen

To use a custom logo instead of the default "A":
- Replace the `SVG` constant in `scripts/generate-icons.mjs` with your logo SVG
- Or place a 512×512 PNG at `public/icons/source.png` and update the script to use it

### 4. Deploy to HTTPS

PWAs **require HTTPS** to work. Options:
- **Vercel** (recommended): `vercel deploy` — free, automatic HTTPS
- **Netlify**: drag-drop the `web/` folder
- **Railway / Render**: connect your GitHub repo
- Your own server with Let's Encrypt SSL

```bash
# Vercel (easiest)
cd web
npx vercel
```

### 5. Verify the PWA

After deploying, open Chrome DevTools → Application tab:
- ✅ Manifest loads correctly
- ✅ Service worker is registered and active  
- ✅ "Installable" shows no errors

Or use [web.dev/measure](https://web.dev/measure) to run a Lighthouse PWA audit.

---

## How Users Install It

### Android (Chrome, Edge, Samsung Browser)
1. Open the app URL in Chrome
2. A banner appears at the bottom: **"Install Axiom"**
3. Tap **Install** → app icon appears on home screen
4. Opens full-screen, no browser chrome

### iPhone / iPad (Safari only)
1. Open the app URL in **Safari** (must be Safari, not Chrome)
2. Tap the **Share** button (↑) at the bottom
3. Scroll and tap **"Add to Home Screen"**
4. Tap **"Add"** → app icon appears on home screen

> **Note:** iOS requires Safari for PWA installation. The app will show iOS-specific instructions automatically via the `InstallBanner` component.

---

## Mobile UX Changes Made

### Bottom Navigation Bar
- On screens < 768px (mobile), the sidebar is hidden
- A bottom tab bar appears with 5 tabs: Home, Jobs, Fleet, Analytics, Scenarios
- Matches native iOS/Android app navigation patterns

### Safe Area Support
- Content respects iPhone notch and Dynamic Island (`env(safe-area-inset-top)`)
- Bottom nav clears the iPhone home indicator bar
- Prevents content being obscured by system UI

### Touch Optimizations
- Minimum 44×44px touch targets (Apple HIG requirement)
- No tap highlight flash on button taps
- Font size ≥ 16px on inputs (prevents iOS zoom-on-focus)
- Overscroll bounce disabled

### Offline Support
- App shell cached on first visit
- Navigation pages cached after first visit
- API errors return a clean JSON message when offline
- `/offline` page shown for uncached routes

---

## Optional: Push Notifications

The service worker includes push notification scaffolding. To enable:

1. Generate VAPID keys:
```bash
npx web-push generate-vapid-keys
```

2. Add to backend `.env`:
```
VAPID_PUBLIC_KEY=your_public_key
VAPID_PRIVATE_KEY=your_private_key
VAPID_EMAIL=mailto:you@example.com
```

3. Add a subscription endpoint to FastAPI, then call `self.registration.pushManager.subscribe()` in the frontend.

---

## Alternative: Native App with Capacitor

If you need access to native APIs (camera, GPS, contacts, biometrics), you can wrap this PWA using Capacitor:

```bash
cd web
npm install @capacitor/core @capacitor/cli
npx cap init "Axiom" "com.axiom.fleet" --web-dir out

# Build Next.js as static
npm run build && npx next export   # add output: 'export' to next.config.mjs

# Add platforms
npx cap add android
npx cap add ios

# Sync and open in IDE
npx cap sync
npx cap open android   # opens Android Studio
npx cap open ios       # opens Xcode
```

Then build and publish to Google Play / App Store from the IDE.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Service worker not registering | Must be on HTTPS (or localhost) |
| Install banner not showing | Browser already has the app installed, or not on HTTPS |
| iOS "Add to Home Screen" missing | Must use Safari (not Chrome) on iOS |
| White flash on app open | Add `background_color` to manifest.json ✓ already done |
| Content behind iPhone notch | `viewport-fit=cover` + `env(safe-area-inset-*)` ✓ already done |
| Form inputs zoom on iOS | Font size ≥ 16px on inputs ✓ already done |
