# BS Chat Android wrapper

Dedicated application ID: `com.stehouwerpublishing.bschat`. Opens `https://ai-bs-dashboard.web.app/chat` in an isolated Android WebView cookie store. No relationship to the existing storefront APK, provider configuration or browser credentials is implied.

Built with recovered Java 17.0.19, Gradle 8.14.3, Android SDK platform 36 and AGP 8.13.0; target SDK remains 35. Run `gradlew.bat --no-daemon assembleDebug` with Java 17 and a configured SDK through local.properties or ANDROID_HOME. SDK automatic downloads are disabled. The successful build used owned copies of the retained SDK/cache, preserving the Windows.old originals and existing license file without accepting new licenses. Release signing remains separately configured; this project contains no signing credentials.

The app supports JavaScript, DOM storage and persistent first-party cookies for the site's login flow; Android backup is disabled. HTTPS links to the dashboard remain inside the app; other HTTPS navigation opens the browser. Other schemes are rejected. File/content access, mixed content, third-party cookies and native JavaScript bridges are disabled. TLS errors are cancelled. Loading and main-page errors have a retry control; Android back traverses WebView history before exiting.

Google and other identity providers may reject embedded WebView login. Browser sign-in does not automatically transfer cookies to the app. No OAuth callback/token exchange or device authentication has been implemented or qualified. Actual Galaxy S25 Ultra layout, authentication, streaming, offline recovery and installation remain device qualification gates; source smoke checks do not establish those behaviors.

Build logs remain local under verification/*.log (ignored by Git). See verification/build-receipt.json for actual build outcome. No APK installation or app launch is performed by the build.
