# Axiom — Native App Build Guide
## Download & Install on Android and iPhone

---

## Overview

Capacitor wraps your existing Next.js app into a real native app container.
The result is a proper `.apk` / `.aab` file (Android) and `.ipa` file (iOS)
that users download and install just like any app.

```
web/out/          ← Next.js static build
    │
    └── Capacitor wraps this into:
          android/   ← Android Studio project  →  .apk / .aab
          ios/       ← Xcode project           →  .ipa
```

---

## Prerequisites

### Everyone needs:
- Node.js 18+
- Your project cloned and `cd web/` as working directory

### For Android:
- [Android Studio](https://developer.android.com/studio) (free)
- Android SDK (installed via Android Studio)
- A physical Android device OR Android emulator

### For iOS (Mac only):
- macOS with [Xcode](https://apps.apple.com/app/xcode/id497799835) 14+ (free)
- Apple Developer account — **free** for device testing, **$99/year** for App Store
- A physical iPhone OR iOS Simulator

> iOS apps can **only be built on a Mac**. If you're on Windows/Linux,
> you can still build the Android app. For iOS, use a Mac or a cloud
> build service like [Codemagic](https://codemagic.io) (free tier available).

---

## Step 1 — Install Capacitor

```bash
cd web
npm install
npx cap init
```

When prompted:
- App name: `Axiom`
- App ID: `com.axiom.fleet`  *(must be unique if publishing to stores)*
- Web asset directory: `out`

Then add platforms:
```bash
npx cap add android   # adds android/ folder
npx cap add ios       # adds ios/ folder (Mac only)
```

---

## Step 2 — Configure your API URL

Since your backend is local, open `web/.env.local` and set:

```bash
# For Android emulator (maps to your machine's localhost):
NEXT_PUBLIC_API_URL=http://10.0.2.2:8000

# For a real Android/iPhone device on the same WiFi:
NEXT_PUBLIC_API_URL=http://192.168.1.42:8000
# (replace with your actual machine IP — run `ipconfig` or `ifconfig`)

# For production (when your API is deployed):
NEXT_PUBLIC_API_URL=https://your-api.com
```

---

## Step 3 — Build the app

```bash
# Builds Next.js as static files + syncs to Android/iOS projects
npm run cap:android   # opens Android Studio
npm run cap:ios       # opens Xcode (Mac only)
```

These commands:
1. Run `next build` with `NEXT_EXPORT=true` → generates `web/out/`
2. Run `npx cap sync` → copies `out/` into the native project
3. Open the IDE

---

## Step 4A — Build Android APK

### Option 1: Direct install (no Play Store)

In **Android Studio**:
1. Wait for Gradle sync to finish (first time takes ~5 min)
2. **Build** → **Build Bundle(s) / APK(s)** → **Build APK(s)**
3. Click "locate" when done — find the file at:
   `android/app/build/outputs/apk/debug/app-debug.apk`

**Install on any Android phone:**
```bash
# Via USB (phone connected, USB debugging enabled)
adb install android/app/build/outputs/apk/debug/app-debug.apk

# Or: copy the .apk to the phone and open it
# (Phone must have "Install unknown apps" enabled in Settings)
```

**Share with anyone:**
Send the `.apk` file via WhatsApp, email, Google Drive, etc.
Recipients enable "Install unknown apps" and tap to install.

### Option 2: Google Play Store

In Android Studio:
1. **Build** → **Generate Signed Bundle / APK**
2. Choose **Android App Bundle (.aab)**
3. Create a keystore (or use existing) — **save this file forever**, you need it for all future updates
4. Build **release** variant
5. Upload the `.aab` to [Google Play Console](https://play.google.com/console)
   - Google Play Developer account: **$25 one-time fee**

---

## Step 4B — Build iOS IPA (Mac only)

### Option 1: Install on your own iPhone (free)

In **Xcode**:
1. Open `web/ios/App/App.xcworkspace`
2. Select your iPhone in the device picker (top bar)
3. Sign in to your Apple ID: **Xcode** → **Settings** → **Accounts**
4. Under "Signing & Capabilities" → select your personal team
5. Press **▶ Run** — app installs directly on your phone

> Free Apple accounts can sideload to personal devices. The app expires after 7 days
> and you need to re-run from Xcode. For permanent installs, you need the $99/year plan.

### Option 2: Share with testers via TestFlight

Requires Apple Developer Program ($99/year):
1. In Xcode: **Product** → **Archive**
2. In Organizer: **Distribute App** → **TestFlight**
3. Invite testers by email in [App Store Connect](https://appstoreconnect.apple.com)
4. Testers install [TestFlight](https://apps.apple.com/app/testflight/id899247664) and get a link

### Option 3: App Store

1. Archive as above → **Distribute App** → **App Store Connect**
2. Fill in metadata, screenshots, description in App Store Connect
3. Submit for Apple review (~1-3 days)

---

## Android: Allow Local HTTP Traffic

Android 9+ blocks plain HTTP by default. Since your API is on HTTP locally:

1. Copy `android-network-security-config.xml` to:
   `android/app/src/main/res/xml/network_security_config.xml`

2. Open `android/app/src/main/AndroidManifest.xml` and add to `<application>`:
   ```xml
   <application
     android:networkSecurityConfig="@xml/network_security_config"
     ...>
   ```

3. Update the IP address in the config to match your machine's actual local IP.

---

## Quick Reference

| Goal | Command | Output |
|------|---------|--------|
| Build + open Android Studio | `npm run cap:android` | Android Studio |
| Build + open Xcode | `npm run cap:ios` | Xcode |
| Run on connected Android | `npm run cap:run:android` | Installs on device |
| Run on iPhone/Simulator | `npm run cap:run:ios` | Installs on device |
| Sync code changes only | `npm run build:mobile && npm run cap:sync` | Updates native projects |

---

## Workflow for Updates

After changing your Next.js code:

```bash
# Rebuild and sync to both platforms
npm run build:mobile
npm run cap:sync

# Then rebuild in Android Studio / Xcode
```

Or use live reload during development (no rebuild needed):
```bash
# Start dev server first
npm run dev:https

# Then in capacitor.config.ts, uncomment:
# server: { url: 'https://192.168.1.42:3000', cleartext: false }

# Sync and run — app loads from your live dev server
npx cap sync
npx cap run android
```

---

## File Locations After Building

```
web/
├── out/                          ← Static Next.js build (Capacitor's source)
├── capacitor.config.ts           ← Capacitor config
├── android/                      ← Full Android Studio project
│   └── app/build/outputs/apk/   ← Your .apk files live here
└── ios/                          ← Full Xcode project
    └── App/                      ← Your .xcworkspace lives here
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `npx cap add android` fails | Make sure Android Studio + SDK installed |
| Gradle sync fails | File → Invalidate Caches / Restart in Android Studio |
| API calls fail on device | Check `NEXT_PUBLIC_API_URL` uses device-accessible IP |
| "Network error" on Android | Add network security config (see above) |
| White screen on launch | Check `webDir: 'out'` in capacitor.config.ts matches your build output |
| iOS build fails "No profiles" | Sign in to Apple ID in Xcode → Preferences → Accounts |
| App crashes immediately | Run `npx cap run android` and check logcat in Android Studio |
| `out/` folder not found | Run `npm run build:mobile` first — creates the static export |
