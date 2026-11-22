# October 7 security, installation and data integrity audit

Scope: read-only inspection of the original installed package and the separately recovered editable source. Installer fixes, when applied, belong only to the AI-BS working copy. No installer, uninstaller, app, server, audio device, microphone, certificate-import or registry operation was executed by this audit. Live trading was not enabled.

## Verified original installer defects

| ID | Severity | Original evidence | Consequence / reproduction |
|---|---|---|---|
| O7-S01 | High | `C:/Program Files/October7_VocalStudio_DAW/setup_installer.py:27`, `:439`, `:449`, `:453` | Source falls back to the installed folder; default target is that same folder. Existing destination directories are recursively removed before copying. Installing over itself can delete the source. Separate-source upgrades can delete recordings in `takes` or `stems`. The AST-only regression intercepts deletion before any real removal. |
| O7-S02 | High | Original Python `:515–528`; PowerShell `:441–451`; BAT `:102–111`; installed `Uninstall_October7_DAW.bat:8` | Generated and installed uninstallers recursively remove the entire app folder, including recordings and stems. No per-file ownership manifest or backup check is present. Static regression checks all four entry points; uninstall was never run. |
| O7-S03 | High | Original Python `:112`, `:368`, `:471`; PowerShell `:276`, `:412`; BAT `:78` | Certificate installation to the machine Root store is selected by default or unconditional. There is no expected signer/fingerprint check before that trust change. SmartScreen guarantees are unsupported. Both installed executables currently have Valid Authenticode signatures; the public certificate is self-signed with Code Signing EKU, not a proven general-purpose TLS CA. |
| O7-S04 | Medium | Original Python `:479–515`, `:525` | `desktop` and `start_dir` are assigned only inside optional shortcut branches and used unconditionally later. Deselecting either option can terminate installation. Both checkbox combinations reproduce offline. |
| O7-S05 | Medium | Original Python `:484–492`, `:502–509`; BAT `:16`, `:86–99` | Apostrophes in paths break the generated PowerShell literals. User-selected paths are interpolated as script text. The regression uses a legitimate `O'Brien` directory, not an attack payload. Shortcut process failure also reports success because return codes are ignored. |
| O7-S06 | Medium | Original Python `:432–546` | Worker-thread code directly changes Tk widgets and invokes message boxes. This is a static threading risk, not a reproduced app crash. A queue processed on the GUI thread is the follow-up remedy. |
| O7-S07 | Medium | Original Python `:369`, `:568–571`; PowerShell `:283`, `:382–386`; BAT `:122–123` | MMCSS installation options have no corresponding setup action. Finish pages claim trusted signatures, SmartScreen verification, WASAPI activation and AI fallbacks without runtime verification. Installation success is being conflated with device/runtime readiness. |

## Verified legacy server source boundaries

Authoritative recovered source folder: `C:/Users/footb/OneDrive/Desktop/carrytodex/VOICECOACHF`. These are source findings; this audit has **not established that the current Native executable launches these servers**.

| ID | Severity | Source evidence | Consequence / verification |
|---|---|---|---|
| O7-S08 | High | `october7_core.py:912–924`, `:1101` | HTTP server binds all interfaces and resolves raw requested paths without a containment check. The AST-extracted original GET method returned status 200 and exact contents of a harmless `../outside_test_record.txt` fixture outside the app folder. No real server was started. See `http_boundary_proof.json`. Reachability still depends on whether this legacy entry point is used and Windows firewall policy. |
| O7-S09 | High | `october7_core.py:810–819`, `:869–879`, `:985–1029` | Wildcard CORS, no authentication/origin guard, and a GET calibration endpoint expose hardware work and state-changing API operations if this server runs. POST operations write generated MIDI and stem files. Input body limits, a request timeout and job isolation are absent; single-threaded `HTTPServer` can be blocked by one request. No hardware or endpoint was invoked. |
| O7-S10 | Medium | `october7_core.py:479–488`, `:1028` | Stem input filenames can be absolute paths or contain traversal. Reads are not restricted to an approved media root. The downstream command uses an argument list, so this finding is filesystem scope, not demonstrated shell injection. |
| O7-S11 | High | `server.js:29–32`, `:77` | Node server binds without a loopback host and authorizes paths using `startsWith(root)`. Windows path algebra proves an adjacent `VOICECOACHF_private` path passes that check. See `node_prefix_proof.json`; no real server or outside file was accessed. |
| O7-S12 | Medium | `server.js:19`, `:49–65`, `:72` | Malformed URI decoding, invalid byte ranges and stream read errors lack bounds/error handling and can throw or leave requests incomplete. Inspection only, no network requests were sent. |

## Additional state issues handed to the workflow owner

- `VOICECOACH PROGRAM.html:2248` parses saved localStorage JSON without recovery. Malformed saved state can interrupt initialization.
- `:2660`, `:2683–2688`, `:5343–5347` interpolate editable cue section/text into `innerHTML`. Stored markup can execute in that document context. No remote exploit or privileged bridge execution was demonstrated.
- Native application source auto-elevates and starts audio before opening the window (package agent evidence). Third-party plugins then share that elevated process. Follow-up: default to a standard-user app, explicitly opt into audio start, store sessions under the user profile, and isolate plugin scanning/hosting. This agent did not start the app or inspect a microphone.

## Evidence and limits

- `scripts/tests/test_october7_installer212.py`: 13 passing offline regressions. The initial 9 tests failed against the original installed source as expected (`red_installer212.log`); 3 additional tests reproduced unsafe source duplicates, and one preserved the newer Native shortcut preference before reconciliation. Tests extract only the installer method or wrapper AST and substitute UI, process, copy and deletion boundaries. All generated fixtures remain under this audit folder. They never import or run the installer module.
- `powershell_copy_fixture212.json`: four assertions passed when only the extracted file-copy helper operated on dedicated fixture files. Resource upgrades succeeded while recording and existing media hashes stayed unchanged. No full installer, GUI, COM, elevation, registry or audio action was invoked. The two installer PowerShell entry points also parse without errors.
- `prove_server_boundaries.py`: extracts only the original legacy GET handler; a fake request and in-memory response prove containment failure using a non-secret C-drive fixture.
- `node_prefix_proof.json`: pure Node Windows-path calculation; no filesystem access or listener.
- No end-to-end installation, uninstallation, elevated trust-store, GUI, audio or live server validation is claimed. Patches to loose installers do not rewrite already compiled executables or the separately recovered source tree.

## Applied working-copy repairs

The four root installer files now reject same/nested/root destinations before writes, preserve recordings/session folders and existing media, and never recursively delete an app tree. Optional shortcut choices no longer reference unassigned paths; generated PowerShell path literals handle apostrophes, and failures prevent a success screen. Root trust imports and unverified SmartScreen/audio completion claims were removed. Certificate fingerprint review and application auto-launch default to off. The BAT entry point delegates to the repaired wizard without an unsafe fallback. Uninstall explicitly refuses automatic removal until a reviewed ownership manifest can distinguish application resources from user data.

The three `source/` installer variants now delegate to the repaired package-root installers, preserving the Native executable preference from the newer source. Their original full source remains in the external recovery archive. Do not distribute these small wrappers independently of their parent package. Original Program Files and OneDrive sources were hash-checked unchanged after repair.

Remaining installation work: transactional resource updates/rollback, a safe per-file uninstall manifest, and main-thread Tk UI dispatch. The legacy HTTP server boundaries above remain open source findings; they have not been repaired or launched in this installer batch.
