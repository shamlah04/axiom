# GitHub Secrets Setup
# Add these at: GitHub repo → Settings → Secrets and variables → Actions → New repository secret

# ─────────────────────────────────────────────────────────────────────────────
# SHARED
# ─────────────────────────────────────────────────────────────────────────────

NEXT_PUBLIC_API_URL
  Value:   Your deployed backend URL, e.g. https://axiom-api.railway.app
  Used by: Both platforms — embedded into the static build

# ─────────────────────────────────────────────────────────────────────────────
# ANDROID SECRETS
# ─────────────────────────────────────────────────────────────────────────────

ANDROID_KEYSTORE_BASE64
  How to get:
    1. Generate a keystore (DO THIS ONCE — keep the file forever):
         cd web/android
         keytool -genkey -v \
           -keystore axiom-release.jks \
           -keyalg RSA -keysize 2048 -validity 10000 \
           -alias axiom-key
         (fill in the prompts — save all passwords securely)
    2. Convert to base64:
         base64 -i axiom-release.jks | tr -d '\n'   # Mac/Linux
         [Convert]::ToBase64String([IO.File]::ReadAllBytes("axiom-release.jks"))  # Windows PowerShell
  Value:   The base64 string output

ANDROID_KEYSTORE_PASSWORD
  Value:   The password you set when running keytool (-storepass)

ANDROID_KEY_ALIAS
  Value:   axiom-key  (or whatever alias you used in keytool)

ANDROID_KEY_PASSWORD
  Value:   The key password you set when running keytool (-keypass)

GOOGLE_PLAY_SERVICE_ACCOUNT_JSON
  How to get:
    1. Go to Google Play Console → Setup → API access
    2. Link to a Google Cloud project
    3. Create a Service Account with "Release manager" role
    4. Download the JSON key file
    5. Copy the entire JSON file contents as the secret value
  Value:   Full contents of the service account JSON file

# ─────────────────────────────────────────────────────────────────────────────
# iOS SECRETS
# ─────────────────────────────────────────────────────────────────────────────

IOS_CERTIFICATE_BASE64
  How to get:
    1. In Xcode → Settings → Accounts → Manage Certificates
    2. Create "Apple Distribution" certificate
    3. Export it: right-click → Export Certificate → save as .p12
    4. Convert: base64 -i certificate.p12 | tr -d '\n'
  Value:   Base64 of the .p12 file

IOS_CERTIFICATE_PASSWORD
  Value:   Password you set when exporting the .p12

IOS_PROVISIONING_PROFILE_BASE64
  How to get:
    1. Go to developer.apple.com → Certificates, IDs & Profiles
    2. Create an App ID: com.axiom.fleet
    3. Create a Distribution provisioning profile (App Store)
    4. Download the .mobileprovision file
    5. Convert: base64 -i profile.mobileprovision | tr -d '\n'
  Value:   Base64 of the .mobileprovision file

KEYCHAIN_PASSWORD
  Value:   Any strong random password — used only in CI to create a temp keychain
  Example: openssl rand -base64 32

APP_STORE_CONNECT_KEY_ID
  How to get:
    1. Go to appstoreconnect.apple.com → Users and Access → Keys
    2. Create a new key with "App Manager" role
    3. Note the Key ID (shown in the key list)
  Value:   The Key ID string (e.g. ABC123DEFG)

APP_STORE_CONNECT_ISSUER_ID
  How to get:
    Same page as above — "Issuer ID" shown at the top of the Keys page
  Value:   UUID format (e.g. 12345678-1234-1234-1234-123456789012)

APP_STORE_CONNECT_API_KEY_BASE64
  How to get:
    1. Download the .p8 key file from App Store Connect (same Keys page)
       NOTE: You can only download it ONCE — save it securely
    2. Convert: base64 -i AuthKey_KEYID.p8 | tr -d '\n'
  Value:   Base64 of the .p8 file
