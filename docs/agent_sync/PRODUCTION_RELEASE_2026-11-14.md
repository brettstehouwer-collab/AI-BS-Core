# Hosting 146 and BS-Chat Android checkpoint

Firebase Hosting deployment exited 0 for project/site `ai-bs-dashboard`, version
`d3cda13a6ebc7a28`. Source and hosted web version are **5.329.146**; this checkpoint
does not increment the existing source baseline or qualify a new native release.

All 1,141 published files (922,179,349 bytes) match the staged manifest by SHA-256
and length, with no excluded inventory files. `/`, `/chat`, `/chat/` and
`/writer.html` match their local HTML exactly, including the existing CSP.
The final local release smoke profile passed 12/12 checks.

The first deployment command opened staged client `firebase.js` through Windows
file association instead of the CLI. Its owned waiting command was quarantined;
the editor was preserved. The successful command ran from `C:\AI-BS` with an
absolute staged Hosting configuration. The build used direct pinned Node/Vite
with `vite.bs-chat.config.mjs`, avoiding the default build's mirror writes.
Canonical Hosting rewrites now retain `/chat`; `npm run build:bs-chat` selects
the additive build configuration without syncing source mirrors.

The initial full hosted verifier remains FAILED because the public API returned
530, despite every static asset passing. The same saved tunnel was subsequently
reconnected without changing ingress, credentials, DNS, Access or firewall.
Post-reconnect API health returned 200; anonymous and invalid-token protected
requests returned 403. Firebase-origin CORS preflight returned valid 204 with the
expected origin and Authorization header. The raw follow-up's exact-200 CORS
assertion was too strict; retain it and use the separate release receipt's
interpretation. No repeat of the 922 MB asset download was necessary.

Local endpoints 8080/8000/5173 and the separate staged static server 3000 respond.
The supplied `http://localhost:5173/?tab=ide` returned 200. This is HTTP evidence,
not an authenticated interactive IDE session. Existing Ollama was preserved.
Ten SQLite backup/logical-equality results cover the scoped core restoration;
the authoritative backend master is WAL and the separate CDZ audit store remains
DELETE. No database merge or blanket connection migration occurred.

Dedicated Android application `com.stehouwerpublishing.bschat` built successfully:
version 1.0/build 1, debug signature verified, 12,617 bytes, SHA-256
`f258061d89974efc08fa1fc4c71111a99f93f0dfe599e37a88e057678eacfe83`.
Its Drive upload was downloaded and compared byte-for-byte. It uses HTTPS-only
WebView defaults, no native JavaScript bridge and no inference binaries. Device
installation, streaming, Google WebView sign-in and production signing remain
unqualified; browser and app sessions are separate. No unverified Tailscale IP
was embedded.

Open the hosted chat using `C:\AI-BS\Launch-BS-Chat-Web.cmd`. APK download:
[BS-Chat debug APK](https://drive.google.com/file/d/1i46AK3QZ6E4pWQvD-DPcyVygGFrIa7X_/view?usp=drivesdk).
Existing game/work launchers and retained native144/145 remain unchanged; held
native146 still contains an inconsistent144 executable and is not promoted.

BS-Chat diagnostics now have seven source registry declarations behind exact
`AI_BS_ENABLE_CHAT_TOOL_BRIDGE=1`; the flag was not activated. Bridge checks15/15
and registry checks12/12 passed synthetically. Task-approved diff scope remains
default-denied and process controller status remains unavailable until bound.
Inspect nested `result.status` in the existing tool endpoint envelope. This
backend source addition is not a claim about the already-running backend.

FE Express offline foundation passed14 synthetic checks; no route/UI registration,
employer integration, device reboot acceptance or personal-finance activation is
claimed. The original ten goals and six additions remain ACTIVE and incomplete.

Machine-readable receipt: `docs/agent_sync/PRODUCTION_RELEASE_2026-11-14.json`.
Detailed local evidence: `backups/production_release_20261114_v01/`. Private DB
snapshots, credentials, signing material, SDK/cache, personal intake and complete
historical ledgers are excluded from shared checkpoint uploads.
