import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.rcullens.taxtrouble',
  appName: 'TaxTrouble',
  webDir: 'build',
  server: {
    androidScheme: 'https'
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: "#1a1a2e",
      androidSplashResourceName: "splash",
      showSpinner: false
    }
  }
};

export default config;