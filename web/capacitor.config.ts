import { CapacitorConfig } from '@capacitor/cli';

const isMobileExport = process.env.NEXT_EXPORT === 'true';

const config: CapacitorConfig = {
  appId: 'com.axiom.fleet',
  appName: 'Axiom',
  webDir: isMobileExport ? 'out' : '.next',

  // When running as a native app, point to the deployed API
  server: isMobileExport
    ? undefined   // In production: bundled static assets, API via NEXT_PUBLIC_API_URL
    : {
      url: 'http://localhost:3000',
      cleartext: true,  // Allow HTTP in dev only
    },

  ios: {
    // Team ID — fill in after setting up your Apple Developer account
    // teamId: 'YOUR_TEAM_ID',
    contentInset: 'always',   // Respect safe areas (notch / Dynamic Island)
  },

  android: {
    allowMixedContent: false,
    captureInput: true,
    webContentsDebuggingEnabled: false,   // Set true only for dev builds
  },
};

export default config;
