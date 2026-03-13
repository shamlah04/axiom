#!/bin/bash
# scripts/ios-release.sh
# Builds an iOS archive and exports for TestFlight or App Store
# from the command line (no need to click through Xcode UI).
#
# USAGE:
#   chmod +x scripts/ios-release.sh
#   ./scripts/ios-release.sh testflight   # Upload to TestFlight
#   ./scripts/ios-release.sh appstore     # Upload to App Store
#   ./scripts/ios-release.sh export       # Just export IPA locally
#
# REQUIREMENTS:
#   - macOS with Xcode 14+
#   - Apple Developer account signed in to Xcode
#   - xcrun altool or Transporter for upload
#   - Update TEAM_ID and BUNDLE_ID below

set -e  # Exit on error

# ── Config — update these ──────────────────────────────────────────────────
TEAM_ID="YOUR_TEAM_ID"            # From developer.apple.com → Membership
BUNDLE_ID="com.axiom.fleet"
SCHEME="App"
WORKSPACE="ios/App/App.xcworkspace"
ARCHIVE_PATH="ios/build/Axiom.xcarchive"
EXPORT_PATH="ios/build/export"
# ──────────────────────────────────────────────────────────────────────────

DISTRIBUTION="${1:-export}"

echo ""
echo "🍎 Axiom iOS Release Build"
echo "   Distribution: $DISTRIBUTION"
echo ""

# Step 1: Build Next.js static export
echo "1/4  Building Next.js..."
NEXT_EXPORT=true npx next build
echo "     ✓ Next.js build complete"

# Step 2: Sync to iOS
echo "2/4  Syncing to iOS..."
npx cap sync ios
echo "     ✓ Capacitor sync complete"

# Step 3: Archive
echo "3/4  Archiving with Xcode..."
xcodebuild archive \
  -workspace "$WORKSPACE" \
  -scheme "$SCHEME" \
  -configuration Release \
  -archivePath "$ARCHIVE_PATH" \
  -destination "generic/platform=iOS" \
  DEVELOPMENT_TEAM="$TEAM_ID" \
  CODE_SIGN_STYLE="Automatic" \
  | xcpretty 2>/dev/null || true

echo "     ✓ Archive created at $ARCHIVE_PATH"

# Step 4: Export
echo "4/4  Exporting IPA..."

if [ "$DISTRIBUTION" = "testflight" ] || [ "$DISTRIBUTION" = "appstore" ]; then
  EXPORT_OPTIONS="ios/ExportOptions-TestFlight.plist"
  if [ "$DISTRIBUTION" = "appstore" ]; then
    EXPORT_OPTIONS="ios/ExportOptions-AppStore.plist"
  fi

  xcodebuild -exportArchive \
    -archivePath "$ARCHIVE_PATH" \
    -exportPath "$EXPORT_PATH" \
    -exportOptionsPlist "$EXPORT_OPTIONS" \
    | xcpretty 2>/dev/null || true

  echo ""
  echo "✅ iOS build complete!"
  echo ""
  echo "📦 IPA: $EXPORT_PATH/Axiom.ipa"
  echo ""

  if [ "$DISTRIBUTION" = "testflight" ]; then
    echo "🚀 Uploading to TestFlight..."
    # Modern upload via xcrun altool (Xcode 13+)
    xcrun altool --upload-app \
      --type ios \
      --file "$EXPORT_PATH/Axiom.ipa" \
      --apiKey "$APP_STORE_API_KEY" \
      --apiIssuer "$APP_STORE_API_ISSUER" \
      2>&1 | grep -v "^$" || {
        echo ""
        echo "⚠️  Automatic upload requires App Store Connect API keys."
        echo "   Set these env vars or upload manually via Transporter app:"
        echo "   APP_STORE_API_KEY=your_key_id"
        echo "   APP_STORE_API_ISSUER=your_issuer_id"
        echo ""
        echo "   Or drag $EXPORT_PATH/Axiom.ipa into Transporter:"
        echo "   https://apps.apple.com/app/transporter/id1450874784"
      }
  fi
else
  # Just export locally
  xcodebuild -exportArchive \
    -archivePath "$ARCHIVE_PATH" \
    -exportPath "$EXPORT_PATH" \
    -exportOptionsPlist "ios/ExportOptions-TestFlight.plist" \
    | xcpretty 2>/dev/null || true

  echo ""
  echo "✅ IPA exported to: $EXPORT_PATH/"
fi
