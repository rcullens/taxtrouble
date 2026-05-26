# TaxTrouble - Desktop & Android Apps

## 🚀 Linux Desktop App (PyWebView)

### Quick Start
```bash
cd desktop
pip install -r requirements.txt
python app.py
```

### Build Standalone AppImage
```bash
cd desktop
chmod +x build_linux.sh
./build_linux.sh
```

Output: `dist/taxtrouble` (single executable)

---

## 📱 Android APK (Capacitor)

### Step-by-step Build

```bash
cd frontend

# 1. Install Capacitor
npm install @capacitor/core @capacitor/cli @capacitor/android --save-dev
npx cap init TaxTrouble com.rcullens.taxtrouble --web-dir build

# 2. Add Android platform
npx cap add android

# 3. Build web app + sync
npm run build
npx cap sync android

# 4. Open in Android Studio
npx cap open android
```

Then in Android Studio:
**Build → Build Bundle(s) / APK(s) → Build APK(s)**

---

## Features
- Full Texas tax/lien scraping
- AI property insights
- Natural language search
- Deal leaderboard
- Live balance checks
- Export to CSV

Built with FastAPI + React + MongoDB