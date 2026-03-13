# Axiom — Complete App Distribution Guide
## Android (Direct + Google Play) & iOS (TestFlight + App Store)

---

## Quick Reference

| Goal | Command | Time |
|------|---------|------|
| Setup Android signing (once) | `npm run release:android:setup` | 2 min |
| Build Android APK + AAB | `npm run release:android` | 5–10 min |
| Upload to TestFlight | `npm run release:ios:testflight` | 10–15 min |
| Upload to App Store | `npm run release:ios:appstore` | 10–15 min |

---

## Part 1 — Android

### A. Direct APK Distribution (no account needed)

The fastest way to get the app on Android phones — share the file directly.

**Step 1: Create your signing keystore (once only)**
```bash
npm run release:android:setup
```
Follow the prompts. This generates `.keystore/axiom-release.keystore`.

> ⚠️ **Back this file up immediately.** If you lose it, you can never publish
> updates to Google Play under the same app listing. Store it in a password
> manager, Google Drive, or encrypted backup.

**Step 2: Build the release**
```bash
npm run release:android
```

This produces:
- `android/app/build/outputs/apk/release/app-release.apk` → share directly
- `android/app/build/outputs/bundle/release/app-release.aab` → upload to Play Store

**Step 3: Share the APK**

Send `app-release.apk` via:
- WhatsApp / Telegram / Email / Google Drive
- Host it on a website as a direct download link
- QR code pointing to the download URL

**Recipient installation steps:**
1. Open the APK file on their Android phone
2. If prompted: Settings → "Install unknown apps" → allow for their browser/files app
3. Tap Install → Done

---

### B. Google Play Store

**Requirements:**
- Google Play Developer account: **$25 one-time fee** at [play.google.com/console](https://play.google.com/console)
- Signed AAB file (built above)

**Steps:**
1. Go to [Google Play Console](https://play.google.com/console) → Create app
2. Fill in:
   - App name: `Axiom Fleet Intelligence`
   - Default language: English
   - App or game: App
   - Free or paid
3. Complete the **store listing**:
   - Short description (80 chars): `AI-powered fleet management & profit prediction`
   - Full description (4000 chars): describe your features
   - Screenshots: at least 2 phone screenshots (1080×1920px recommended)
   - Feature graphic: 1024×500px banner image
   - App icon: 512×512px PNG (use one from `public/icons/`)
4. Go to **Production** (or **Internal Testing** first) → Create new release
5. Upload `app-release.aab`
6. Fill in release notes
7. Submit for review

**Review time:** Usually 1–3 days for new apps, faster for updates.

---

## Part 2 — iOS

> iOS builds require a **Mac with Xcode**. If you're on Windows/Linux,
> use a Mac, or a cloud service like [Codemagic](https://codemagic.io) (free tier).

### A. TestFlight (Beta Distribution)

TestFlight lets up to 10,000 external testers install your app via a link.
No App Store review for internal testers. External testers need a brief review (~1 day).

**Requirements:**
- Apple Developer Program: **$99/year** at [developer.apple.com](https://developer.apple.com)
- Mac with Xcode 14+
- App registered in [App Store Connect](https://appstoreconnect.apple.com)

**Step 1: Register your App ID**
1. [developer.apple.com](https://developer.apple.com) → Certificates, Identifiers & Profiles
2. Identifiers → + → App IDs → App
3. Bundle ID: `com.axiom.fleet` (must match `capacitor.config.ts`)
4. Enable capabilities if needed (Push Notifications, etc.)

**Step 2: Update export plist**

Open `ios/ExportOptions-TestFlight.plist` and replace:
```xml
<string>YOUR_TEAM_ID</string>
```
with your actual Team ID from [developer.apple.com/account](https://developer.apple.com/account) → Membership.

**Step 3: Build and upload**
```bash
# Option A: command line
npm run release:ios:testflight

# Option B: Xcode UI
npm run cap:ios          # opens Xcode
# Then: Product → Archive → Distribute App → TestFlight & App Store
```

**Step 4: Invite testers**
1. [App Store Connect](https://appstoreconnect.apple.com) → Your app → TestFlight
2. Internal Testing → Add testers (your team, up to 100)
3. External Testing → Add group → invite by email or share public link

Testers install [TestFlight](https://apps.apple.com/app/testflight/id899247764) from the App Store,
then tap your invite link.

---

### B. App Store

**Step 1: Prepare your app listing in App Store Connect**
1. [appstoreconnect.apple.com](https://appstoreconnect.apple.com) → My Apps → +
2. Fill in:
   - Name: `Axiom Fleet Intelligence`
   - Primary language
   - Bundle ID: `com.axiom.fleet`
   - SKU: any unique string (e.g. `axiom-fleet-001`)

**Step 2: App Store listing metadata**
- **Description**: what the app does (up to 4000 chars)
- **Keywords**: fleet, trucking, logistics, profit, AI (100 chars total)
- **Support URL**: your website or GitHub
- **Screenshots**: required sizes:
  - iPhone 6.9": 1320×2868 or 1290×2796px (at least 3)
  - iPhone 6.5": 1284×2778 or 1242×2688px
  - iPad Pro 12.9" (if supporting iPad)
- **App Preview** (optional): 15–30 second video

**Step 3: Build and submit**
```bash
npm run release:ios:appstore
```

Or via Xcode: Product → Archive → Distribute App → App Store Connect → Upload

**Step 4: Submit for review**
1. In App Store Connect → your app → App Store tab
2. Select the build you uploaded
3. Answer export compliance questions (usually: no encryption)
4. Add review notes if needed
5. Submit for Review

**Review time:** 1–3 days. Apple may ask for login credentials if your app
requires authentication — create a demo account for reviewers.

---

## App Store Assets Checklist

Before submitting to either store, prepare:

### Google Play
- [ ] App icon: 512×512 PNG (no alpha, no rounded corners — Play adds them)
- [ ] Feature graphic: 1024×500 PNG or JPG
- [ ] Phone screenshots: min 2, max 8 (16:9 or 9:16)
- [ ] Short description: ≤ 80 characters
- [ ] Full description: ≤ 4000 characters
- [ ] Privacy Policy URL (required if app collects any data)
- [ ] Content rating questionnaire (completed in Play Console)
- [ ] Data safety section (what data you collect/share)

### Apple App Store
- [ ] App icon: 1024×1024 PNG (no alpha channel, no rounded corners)
- [ ] iPhone 6.9" screenshots: 1320×2868px (at least 3)
- [ ] iPhone 6.5" screenshots: 1284×2778px (at least 3)
- [ ] Description: ≤ 4000 characters
- [ ] Keywords: ≤ 100 characters
- [ ] Privacy Policy URL (mandatory)
- [ ] Support URL
- [ ] Export compliance answers
- [ ] Demo account credentials for reviewers (if login required)

---

## Version Management

Each release needs a version bump in two places:

**`package.json`** — semantic version for your reference:
```json
{ "version": "1.0.1" }
```

**`capacitor.config.ts`** — shown in stores, format: `major.minor.patch`:
```typescript
// Add to your capacitor.config.ts:
// (Capacitor reads from native project files — update those too)
```

**Android** — `android/app/build.gradle`:
```gradle
defaultConfig {
    versionCode 2        // increment by 1 for every Play Store upload
    versionName "1.0.1"  // human-readable version shown in store
}
```

**iOS** — in Xcode: target → General → Version + Build
Or `ios/App/App/Info.plist`:
```xml
<key>CFBundleShortVersionString</key><string>1.0.1</string>
<key>CFBundleVersion</key><string>2</string>
```

---

## Cost Summary

| Channel | Cost | Notes |
|---------|------|-------|
| Android APK (direct) | Free | Share file directly, no review |
| Google Play Store | $25 one-time | Per developer account |
| iOS TestFlight | $99/year | Included with Apple Developer Program |
| Apple App Store | $99/year | Same subscription as TestFlight |
| iOS device testing | Free | 7-day expiry without paid account |
