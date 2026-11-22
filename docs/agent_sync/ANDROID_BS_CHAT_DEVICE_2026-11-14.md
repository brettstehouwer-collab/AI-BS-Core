# BS-Chat device installation

The user authorized deployment to the connected Android device. Initial ADB
enumeration required device-side USB debugging authorization. After the user
accepted that prompt, installation succeeded on Samsung **SM-S938U**
(Galaxy S25 Ultra).

- Application: `com.stehouwerpublishing.bschat`, label **BS Chat**.
- Version: **1.0**, build **1**, debug signature.
- APK: 12,617 bytes; SHA-256
  `f258061d89974efc08fa1fc4c71111a99f93f0dfe599e37a88e057678eacfe83`.
- `adb install -r --no-incremental` returned Success; Android package-manager
  readback confirmed the package, version name and version code.
- This package was not previously installed. No uninstall, downgrade, app-data
  clearing or credential change occurred. The app was not automatically opened.

This proves installation and package identity. It does not establish Google
WebView sign-in, authenticated chat, streaming or device-layout acceptance. The
wrapper still targets the verified Hosting146 `/chat` entry; the separate FE
Express source candidate is not part of this APK or a new hosted deployment.

Private ADB identifiers and package-manager logs remain local under
`backups/android_device_install_20261114_v02/`. Prior unauthorized-device evidence
is preserved under the corresponding v01 folder. Shared checkpoint derivatives
omit device serials and identifier hashes.

Later explicit user report: **installation and login work**. Installation remains
package-manager verified, and login is now USER_REPORTED_PASS. The assistant did
not observe that authenticated screen or test chat replies/streaming/reconnect.
The accepted1.0/build1 APK and source remain byte-identical. An optional1.0.1
native-browser-handoff build was retained privately but was not installed or
promoted after this report. See ANDROID_BS_CHAT_USER_ACCEPTANCE_2026-11-14.json.
