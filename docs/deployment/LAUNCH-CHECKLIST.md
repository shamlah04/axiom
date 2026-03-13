# Axiom — App Store & Play Store Launch Checklist
## Android + iOS, Direct Distribution + Store Publishing

---

## PHASE 1 — One-Time Setup (do these once)

### Apple Developer Account
- [ ] Sign up at developer.apple.com ($99/year)
- [ ] Accept all agreements in App Store Connect
- [ ] Create App ID: `com.axiom.fleet` (Certificates, IDs & Profiles → Identifiers)
- [ ] Create Distribution Certificate (Xcode → Settings → Accounts → Manage Certs)
- [ ] Create App Store provisioning profile for `com.axiom.fleet`
- [ ] Create App Store Connect API Key (Users & Access → Keys → save the .p8 file)
- [ ] Create the app record in App Store Connect (My Apps → +)

### Google Play Account
- [ ] Sign up at play.google.com/console ($25 one-time)
- [ ] Accept developer agreement and set up payments
- [ ] Create app in Play Console (All apps → Create app)
- [ ] Set up Google Cloud project and link to Play Console (Setup → API access)
- [ ] Create service account with Release Manager role, download JSON key

### Android Keystore (CRITICAL — never lose this file)
```bash
cd web/android
keytool -genkey -v \
  -keystore axiom-release.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias axiom-key
```
- [ ] Keystore generated and stored in a password manager + backup
- [ ] Passwords saved securely (you need these forever for every update)
- [ ] `axiom-release.jks` added to `.gitignore` (never commit to git)

### GitHub Secrets (repo → Settings → Secrets → Actions)
- [ ] `NEXT_PUBLIC_API_URL` — your deployed backend URL
- [ ] `ANDROID_KEYSTORE_BASE64`
- [ ] `ANDROID_KEYSTORE_PASSWORD`
- [ ] `ANDROID_KEY_ALIAS`
- [ ] `ANDROID_KEY_PASSWORD`
- [ ] `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`
- [ ] `IOS_CERTIFICATE_BASE64`
- [ ] `IOS_CERTIFICATE_PASSWORD`
- [ ] `IOS_PROVISIONING_PROFILE_BASE64`
- [ ] `KEYCHAIN_PASSWORD`
- [ ] `APP_STORE_CONNECT_KEY_ID`
- [ ] `APP_STORE_CONNECT_ISSUER_ID`
- [ ] `APP_STORE_CONNECT_API_KEY_BASE64`

See `GITHUB-SECRETS.md` for exactly how to get each value.

---

## PHASE 2 — App Preparation

### Code
- [ ] Copy all PWA files into `web/` (from previous deliverables)
- [ ] Copy Capacitor config files into `web/`
- [ ] Run `npx cap init` and `npx cap add android && npx cap add ios`
- [ ] Update `capacitor.config.ts`: set your Team ID
- [ ] Update `web/ExportOptions.plist`: set your Team ID
- [ ] Update `fastlane/Appfile`: set your Apple ID and Team IDs
- [ ] Test build locally: `npm run cap:android` and `npm run cap:ios`
- [ ] Fix any white screen / routing issues (see Troubleshooting in NATIVE-APP-GUIDE.md)

### Icons & Splash Screen
- [ ] Run `npm run icons` to generate all icon sizes
- [ ] Icons look correct at all sizes (check in Android Studio / Xcode)
- [ ] Android: set splash screen in `android/app/src/main/res/`
- [ ] iOS: set splash screen in Xcode (App → LaunchScreen.storyboard)
- [ ] Android adaptive icon configured (foreground + background layers)

### Backend
- [ ] FastAPI deployed to a public HTTPS URL (Railway / Render / VPS)
- [ ] `NEXT_PUBLIC_API_URL` set to the live API URL
- [ ] CORS updated in `app/main.py` to only allow your frontend domains
- [ ] Auth works end-to-end on a real device

---

## PHASE 3 — Store Listings

### App Store (iOS)
- [ ] App name: "Axiom Fleet Intelligence" (30 chars max)
- [ ] Subtitle: "Profit prediction for fleets" (30 chars max)
- [ ] Description: in `fastlane/metadata/ios/en-US/description.txt` ✓
- [ ] Keywords: in `fastlane/metadata/ios/en-US/keywords.txt` ✓
- [ ] Privacy Policy URL (required): host a simple privacy policy page
- [ ] Support URL: your website or email
- [ ] Screenshots: required sizes:
  - 6.9" (iPhone 16 Pro Max): 1320×2868 or 2868×1320
  - 6.5" (iPhone 14 Plus):    1284×2778 or 2778×1284
  - 12.9" iPad Pro (optional): 2048×2732
- [ ] App category: Business (primary), Productivity (secondary)
- [ ] Age rating: 4+ (no objectionable content)
- [ ] Price: Free (or set paid pricing)
- [ ] Availability: All countries (or restrict as needed)

### Google Play (Android)
- [ ] App name: "Axiom Fleet Intelligence" (50 chars max)
- [ ] Short description: in `fastlane/metadata/android/en-US/short_description.txt` ✓
- [ ] Full description: in `fastlane/metadata/android/en-US/full_description.txt` ✓
- [ ] Category: Business
- [ ] Screenshots (at least 2, max 8): 16:9 or 9:16, min 320px, max 3840px
- [ ] Feature graphic: 1024×500px (shown at top of Play listing)
- [ ] App icon: 512×512px PNG
- [ ] Privacy Policy URL (required)
- [ ] Content rating: complete the questionnaire in Play Console
- [ ] Data safety form: complete in Play Console (explain what data you collect)
- [ ] Target audience: 18+

---

## PHASE 4 — First Release

### Direct Distribution (share APK/IPA without stores)

**Android APK:**
```bash
# Trigger a build manually in GitHub Actions, or tag a release:
git tag v1.0.0
git push origin v1.0.0
```
- [ ] APK appears in GitHub Releases as a download attachment
- [ ] Test install: download APK on Android → enable "Unknown sources" → tap to install
- [ ] Share download link with users

**iOS IPA (without App Store):**
- Option A: TestFlight (requires Apple Developer account) — users install TestFlight app and get invite link
- Option B: AltStore / Sideloadly — users install AltStore and sideload the IPA (technical users only)
- [ ] TestFlight invite sent and working

### Store Publishing

**Google Play:**
- [ ] First build uploaded to internal track (GitHub Actions does this on tag push)
- [ ] Test on internal track with 1-2 devices
- [ ] Promote to closed testing (beta) with a small group
- [ ] Promote to open testing or production
- [ ] Google Play review: typically 1-3 days for new apps

**Apple App Store:**
- [ ] Build uploaded to TestFlight via GitHub Actions
- [ ] TestFlight testing passed
- [ ] Submit for App Store review in App Store Connect
- [ ] Fill in all required fields (export compliance, etc.)
- [ ] Apple review: typically 1-3 days (can be longer for first submission)
- [ ] App goes live after approval

---

## PHASE 5 — Ongoing Updates

For every new release:

```bash
# 1. Update version in web/package.json
#    e.g. "version": "1.0.1"

# 2. Tag the release
git tag v1.0.1
git push origin v1.0.1

# GitHub Actions automatically:
# → Builds new APK + AAB
# → Uploads to Play Store internal track
# → Builds new IPA
# → Uploads to TestFlight
# → Creates GitHub Release with download links
```

- [ ] Update `fastlane/metadata/android/en-US/changelogs/default.txt`
- [ ] Update `fastlane/metadata/ios/en-US/release_notes.txt`
- [ ] Test on real devices before promoting to production

---

## Quick Commands Reference

```bash
# Local development with mobile
npm run dev:https                          # HTTPS dev server for mobile testing

# Build for mobile
npm run build:mobile                       # Next.js static export

# Open in IDE
npm run cap:android                        # Open Android Studio
npm run cap:ios                            # Open Xcode

# Fastlane (from project root, Mac only)
fastlane android apk                       # Build APK locally
fastlane android beta                      # Upload to Play Store internal
fastlane android release                   # Promote to Play Store production
fastlane ios beta                          # Build + upload to TestFlight
fastlane ios release                       # Submit to App Store

# Tag and release (triggers CI/CD)
git tag v1.0.0 && git push origin v1.0.0
```
