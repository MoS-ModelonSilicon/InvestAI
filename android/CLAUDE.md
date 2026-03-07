# android/ — Android App Gotchas

## Architecture

Kotlin + Jetpack Compose app that wraps the web app in a WebView. It is NOT a native reimplementation — it loads `https://investai-utho.onrender.com` inside a WebView.

## Key Files

- `app/build.gradle.kts` — dependencies, versioning, signing config
- `keystore.properties` — signing key references (DO NOT COMMIT actual keystore)
- `app/src/main/` — Kotlin source code

## Gotchas

- **Signing**: `keystore.properties` must point to actual `.jks` file — see `keystore.properties.template`
- **Play Store**: See `PUBLISH.md` for release process
- **Service account**: `play-service-account.json` is for Play Store API — SENSITIVE, do not expose
- **WebView cookies**: Session cookie from the web app must persist in WebView — check `CookieManager` config
- **Offline**: No offline mode — app requires internet connection to load web app
- **Version bumps**: Update `versionCode` AND `versionName` in `app/build.gradle.kts` for each release

## DO NOT

- Commit actual keystore files (`.jks`) to git
- Expose `play-service-account.json` contents
- Change the WebView URL without updating both `local.properties` and the Kotlin source
- Build without proper signing config (debug builds work, release needs keystore)
