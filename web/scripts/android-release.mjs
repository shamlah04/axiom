#!/usr/bin/env node
// scripts/android-release.mjs
// Builds a signed Android release APK and AAB ready for:
//   - Direct distribution (APK)
//   - Google Play Store (AAB)
//
// FIRST TIME SETUP:
//   node scripts/android-release.mjs --create-keystore
//
// BUILD RELEASE:
//   node scripts/android-release.mjs
//
// REQUIREMENTS:
//   - Android Studio installed with SDK
//   - JAVA_HOME set (Android Studio bundles a JDK)
//   - Run `npm run build:mobile` first (or let this script do it)

import { execSync, spawnSync } from 'child_process'
import { existsSync, mkdirSync, writeFileSync, readFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import readline from 'readline'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT      = join(__dirname, '..')
const KEYSTORE_DIR  = join(ROOT, '.keystore')
const KEYSTORE_FILE = join(KEYSTORE_DIR, 'axiom-release.keystore')
const KEYSTORE_PROPS = join(ROOT, 'android', 'keystore.properties')

// ── Helpers ────────────────────────────────────────────────────────────────
function run(cmd, opts = {}) {
  console.log(`\n▶ ${cmd}\n`)
  execSync(cmd, { stdio: 'inherit', cwd: ROOT, ...opts })
}

function ask(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout })
  return new Promise(resolve => rl.question(question, ans => { rl.close(); resolve(ans) }))
}

// ── Create keystore (one time) ─────────────────────────────────────────────
async function createKeystore() {
  console.log('\n🔐 Creating Android release keystore...')
  console.log('   IMPORTANT: Keep this file safe — you need it for every future update!\n')

  mkdirSync(KEYSTORE_DIR, { recursive: true })

  const alias    = await ask('Key alias (e.g. axiom-key): ') || 'axiom-key'
  const password = await ask('Keystore password (min 6 chars): ')
  const name     = await ask('Your name: ')
  const org      = await ask('Organisation: ')
  const city     = await ask('City: ')
  const country  = await ask('Country code (e.g. DK, US, GB): ')

  // Find keytool — bundled with Android Studio JDK
  let keytool = 'keytool'
  const studioJdk = process.env.JAVA_HOME
    ? join(process.env.JAVA_HOME, 'bin', 'keytool')
    : null
  if (studioJdk && existsSync(studioJdk)) keytool = `"${studioJdk}"`

  run(
    `${keytool} -genkey -v ` +
    `-keystore "${KEYSTORE_FILE}" ` +
    `-alias ${alias} ` +
    `-keyalg RSA -keysize 2048 -validity 10000 ` +
    `-storepass "${password}" -keypass "${password}" ` +
    `-dname "CN=${name}, O=${org}, L=${city}, C=${country}"`
  )

  // Write keystore.properties for Gradle
  const props = [
    `storeFile=${KEYSTORE_FILE.replace(/\\/g, '/')}`,
    `storePassword=${password}`,
    `keyAlias=${alias}`,
    `keyPassword=${password}`,
  ].join('\n')

  writeFileSync(KEYSTORE_PROPS, props)

  console.log('\n✅ Keystore created!')
  console.log(`   📁 File:  ${KEYSTORE_FILE}`)
  console.log(`   📄 Props: ${KEYSTORE_PROPS}`)
  console.log('\n⚠️  BACK UP the .keystore file now — losing it means you can never')
  console.log('   update your app on Google Play.\n')
}

// ── Patch build.gradle to use keystore ────────────────────────────────────
function patchGradle() {
  const gradlePath = join(ROOT, 'android', 'app', 'build.gradle')
  if (!existsSync(gradlePath)) {
    console.error('❌ android/app/build.gradle not found — run `npx cap add android` first')
    process.exit(1)
  }

  let gradle = readFileSync(gradlePath, 'utf8')

  // Skip if already patched
  if (gradle.includes('keystorePropertiesFile')) {
    console.log('   build.gradle already patched ✓')
    return
  }

  const signingBlock = `
    // ── Release signing (added by scripts/android-release.mjs) ──
    def keystorePropertiesFile = rootProject.file("keystore.properties")
    def keystoreProperties = new Properties()
    if (keystorePropertiesFile.exists()) {
        keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
    }

    signingConfigs {
        release {
            if (keystorePropertiesFile.exists()) {
                storeFile file(keystoreProperties['storeFile'])
                storePassword keystoreProperties['storePassword']
                keyAlias keystoreProperties['keyAlias']
                keyPassword keystoreProperties['keyPassword']
            }
        }
    }
`

  // Insert after 'android {' line
  gradle = gradle.replace('android {', `android {\n${signingBlock}`)

  // Set release buildType to use signingConfig
  gradle = gradle.replace(
    /buildTypes\s*\{[^}]*release\s*\{/,
    match => match + '\n            signingConfig signingConfigs.release'
  )

  writeFileSync(gradlePath, gradle)
  console.log('   build.gradle patched for release signing ✓')
}

// ── Main build ─────────────────────────────────────────────────────────────
async function buildRelease() {
  if (!existsSync(KEYSTORE_FILE)) {
    console.error('❌ Keystore not found. Create it first:')
    console.error('   node scripts/android-release.mjs --create-keystore\n')
    process.exit(1)
  }

  console.log('\n🏗️  Building Axiom Android release...\n')

  // 1. Build Next.js static export
  console.log('1/4  Building Next.js...')
  run('npm run build:mobile')

  // 2. Sync to Android
  console.log('2/4  Syncing to Android...')
  run('npx cap sync android')

  // 3. Patch Gradle for signing
  console.log('3/4  Configuring release signing...')
  patchGradle()

  // 4. Build with Gradle
  console.log('4/4  Building with Gradle...')
  const gradlew = process.platform === 'win32'
    ? join(ROOT, 'android', 'gradlew.bat')
    : join(ROOT, 'android', 'gradlew')

  // APK — for direct distribution
  run(`"${gradlew}" assembleRelease`, { cwd: join(ROOT, 'android') })

  // AAB — for Google Play
  run(`"${gradlew}" bundleRelease`, { cwd: join(ROOT, 'android') })

  const apkPath = join(ROOT, 'android', 'app', 'build', 'outputs', 'apk',    'release', 'app-release.apk')
  const aabPath = join(ROOT, 'android', 'app', 'build', 'outputs', 'bundle', 'release', 'app-release.aab')

  console.log('\n✅ Android release build complete!\n')
  console.log('📱 APK (direct install):')
  console.log(`   ${apkPath}`)
  console.log('\n🏪 AAB (Google Play Store):')
  console.log(`   ${aabPath}`)
  console.log('\nNext steps:')
  console.log('  Direct: share the .apk file — recipients tap to install')
  console.log('  Play Store: upload the .aab at https://play.google.com/console\n')
}

// ── Entry point ────────────────────────────────────────────────────────────
const args = process.argv.slice(2)
if (args.includes('--create-keystore')) {
  await createKeystore()
} else {
  await buildRelease()
}
