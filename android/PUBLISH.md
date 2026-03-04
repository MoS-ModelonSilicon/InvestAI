# Publishing InvestAI to Google Play

## Prerequisites

You need **one** of these installed:
- **Android Studio** (recommended) — https://developer.android.com/studio  
- **Command-line only**: JDK 17 + Android SDK command-line tools

---

## Step 1 · Install Android Studio

1. Download from https://developer.android.com/studio
2. Run the installer → choose **Standard** setup
3. Wait for it to download the Android SDK (takes ~5 min)
4. Once done, **File → Open** → select:
   ```
   C:\Users\yklein3\OneDrive - Intel Corporation\PycharmProjects\cursor\finance-tracker\android
   ```
5. Android Studio will auto-generate the **Gradle wrapper JAR** and sync — wait for it to finish (first sync downloads ~500MB of dependencies)

> **Intel proxy?** If Gradle can't download, add to `gradle.properties`:
> ```properties
> systemProp.http.proxyHost=proxy-dmz.intel.com
> systemProp.http.proxyPort=911
> systemProp.https.proxyHost=proxy-dmz.intel.com
> systemProp.https.proxyPort=912
> ```

---

## Step 2 · Generate a Signing Key

Open a terminal **inside Android Studio** (View → Tool Windows → Terminal):

```bash
mkdir keystore

keytool -genkey -v \
  -keystore keystore/investai-release.jks \
  -alias investai \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -storepass YOUR_PASSWORD_HERE \
  -keypass YOUR_PASSWORD_HERE \
  -dname "CN=InvestAI, O=YKlein, L=Haifa, C=IL"
```

Or on **Windows PowerShell** (one line):
```powershell
keytool -genkey -v -keystore keystore\investai-release.jks -alias investai -keyalg RSA -keysize 2048 -validity 10000 -storepass YOUR_PASSWORD_HERE -keypass YOUR_PASSWORD_HERE -dname "CN=InvestAI, O=YKlein, L=Haifa, C=IL"
```

> **IMPORTANT:** Replace `YOUR_PASSWORD_HERE` with a strong password. Save it somewhere safe — you need it every time you update the app.

---

## Step 3 · Configure the Signing Key

1. Copy `keystore.properties.template` → `keystore.properties`
2. Fill in your real password:
   ```properties
   storeFile=keystore/investai-release.jks
   storePassword=YOUR_ACTUAL_PASSWORD
   keyAlias=investai
   keyPassword=YOUR_ACTUAL_PASSWORD
   ```

> ⚠️ **Never commit `keystore.properties` or `*.jks` to git** — they're in `.gitignore`

---

## Step 4 · Build the Release AAB

### Option A: Android Studio GUI
1. **Build → Generate Signed Bundle/APK**
2. Choose **Android App Bundle**
3. Select your keystore + alias + passwords
4. Choose **release** build variant
5. Click **Create**
6. Find the AAB at: `app/build/outputs/bundle/release/app-release.aab`

### Option B: Command line
```bash
# From the android/ directory:
./gradlew bundleRelease
```
Output: `app/build/outputs/bundle/release/app-release.aab`

---

## Step 5 · Create Your Store Listing

Go to https://play.google.com/console and create a new app.

### App Details
| Field | Value |
|-------|-------|
| **App name** | InvestAI – Smart Portfolio & Market Tracker |
| **Default language** | English (United States) |
| **App category** | Finance |
| **Free / Paid** | Free |

### Short Description (80 chars max)
```
AI-powered stock screener, portfolio tracker & smart investing assistant.
```

### Full Description (4000 chars max)
```
InvestAI is your all-in-one investing companion that combines real-time market data with AI-powered analysis to help you make smarter investment decisions.

📊 REAL-TIME MARKET DATA
• Live stock prices with interactive charts (1D to 1Y)
• Market overview with major indices and trending stocks
• Detailed stock fundamentals: P/E, beta, dividend yield, 52-week range
• Analyst price targets and consensus ratings

🤖 AI-POWERED INSIGHTS
• Smart stock screener with sector, region, and asset-type filters
• Personalized AI recommendations based on your risk profile
• AutoPilot portfolio simulation with multiple strategy profiles
• Buy/Hold/Sell signal badges backed by technical analysis
• Value scanner to find undervalued opportunities

💼 PORTFOLIO MANAGEMENT
• Track all your holdings with real-time P&L
• Watchlist with live price updates
• Sector allocation breakdown
• Best and worst performer highlights
• Portfolio performance over time

🔔 SMART ALERTS
• Set price alerts for any stock
• Get notified when targets are hit
• Track triggered and active alerts

💰 BUDGET & EXPENSE TRACKING
• Log income and expenses
• Set monthly budget limits per category
• Visual progress rings showing spend vs. budget
• Dashboard with category breakdown and monthly trends

📰 MARKET INTELLIGENCE
• Curated financial news feed
• Stock-specific news on detail pages
• Compare multiple stocks side-by-side
• Israeli funds data

🔒 SECURE & PRIVATE
• Session-based authentication
• Your data stays on your account
• No ads, no selling your data

Whether you're a beginner learning to invest or an experienced trader looking for an edge, InvestAI gives you the tools and insights you need — all in one beautiful, fast app.

Disclaimer: InvestAI is for educational and informational purposes only. It does not constitute financial advice. Always do your own research before making investment decisions.
```

### Graphics Required
| Asset | Size | Notes |
|-------|------|-------|
| **App icon** | 512×512 PNG | Already generated as adaptive icon — export from Android Studio or use the foreground on indigo background |
| **Feature graphic** | 1024×500 PNG | Create in Canva/Figma: indigo (#6366F1) gradient background, phone mockup, "InvestAI" title |
| **Screenshots** | Min 2, phone size (1080×1920 recommended) | Run the app in emulator, take screenshots of Home, Stock Detail, Portfolio, Screener |

> **Quick screenshot tip:** In Android Studio emulator, click the camera icon in the toolbar or press `Ctrl+S` in the emulator window.

---

## Step 6 · Upload & Submit

1. In Google Play Console → **Production** → **Create new release**
2. Upload `app-release.aab`
3. Add release notes:
   ```
   Initial release of InvestAI:
   • Real-time stock prices and interactive charts
   • AI-powered stock screener and recommendations
   • Portfolio tracking with P&L
   • Price alerts
   • Budget tracking
   • Market news feed
   ```
4. **Save** → **Review release** → **Start rollout to Production**

### Required Declarations
During setup, Google will ask you to fill out:

- **Privacy Policy URL** — You need one. Use a free generator like https://app-privacy-policy-generator.firebaseapp.com/ or host a simple page on your Render backend
- **Content Rating** — Fill the IARC questionnaire (no violence, no gambling → rated "Everyone")
- **Target Audience** — Ages 18+ (finance app)
- **Data Safety** — Declare: collects account info (login key), financial data (portfolio/transactions). Data is not shared with third parties.
- **Ads** — No ads
- **COVID-19 contact tracing** — No

---

## Step 7 · Wait for Review

Google typically reviews new apps within **1-3 days**. You'll get an email when it's approved or if changes are needed.

---

## Quick Reference: Version Bumping

For future updates, in `app/build.gradle.kts`:
```kotlin
versionCode = 2        // Must increase every release
versionName = "1.1.0"  // Human-readable version
```

Then repeat Step 4 (build AAB) and Step 6 (upload).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Gradle sync fails behind proxy | Add proxy settings to `gradle.properties` (see Step 1) |
| `keytool` not found | Use the one bundled with Android Studio: `"C:\Program Files\Android\Android Studio\jbr\bin\keytool"` |
| AAB too large | Already configured with `minifyEnabled = true` and `shrinkResources = true` |
| Play Console rejects AAB | Make sure `versionCode` is higher than any previously uploaded version |
| "App not signed" error | Verify `keystore.properties` paths and passwords match |
