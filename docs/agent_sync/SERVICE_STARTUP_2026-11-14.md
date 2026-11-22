# AI-BS service startup checkpoint

The user requested all services and explicitly included business automation.
Existing core services were preserved. Missing existing listeners were started
individually rather than running historical fleet launchers that mix services,
campaign dispatch, trading, plotting and compute workloads.

Running listeners include Nginx80, staged static3000, held Node3001, Studio5173,
Broadcast UI5174, Go8000, Chroma8002, Broadcast8005/4455, Social8006, SHM8010,
VST8013, backend8080, Bio8085, Broadcast kernel8088, Gemini MCP8099, ComfyUI8189,
Unreal signaling8888 and Ollama11434/11435. MinerWatch is running read-only
telemetry. New listeners are loopback; the existing primary Ollama binding was
preserved. Broadcast/recording/virtual-camera flags remain off, Social has no
configured Twitch token/channel, and no inference, mining or plotting was run.

Fourteen bounded HTTP assertions passed, including the expected Node503 hold.
That is thirteen ready endpoints plus one observed hold, not fourteen fully
qualified workflows. Additional listeners have their own startup receipts.
Bio initially failed closed503; the exact newly owned idle process was replaced
using the existing vault credential in child environment only. Ping200,
invalid-key401 and valid-key405 on a nonexecuting GET prove its auth boundary
without invoking a command. Existing credentials were not replaced or logged.

Chroma startup was initially held because the original store and exact copied
snapshot both reported a malformed FTS5 inverted index. A separate shadow rebuild
passed before canonical repair. The canonical FTS rebuild used FULL durability
inside an exclusive transaction, with all18 authoritative table/document hashes
unchanged before commit. All15,633 documents and302 vector files were retained.
The existing server now runs on8002 against the original E-drive storage bin,
with migrations set to validate only. Its startup added one expected acquire_write
lock row;17/18 ordinary tables remain identical and no prior lock rows changed
or disappeared. Integrity passes. Original snapshots, shadow and the overly strict
post-start quarantine receipt remain locally preserved; the separate interpreted
acceptance records the precise bookkeeping delta.

Remaining holds and limits:

- Node3001 intentionally returns503 because its distinct local owner token is
  absent; it is not a healthy replacement for the main backend.
- RecDebut retains its existing hard review hold; no campaign dispatch occurred.
- Live financial trading was not started. MinerWatch does not start miners.
- WSL HLS8089 cannot start: current `wsl.exe --list --quiet` exited-1 with
  `Wsl/CallMsi/Install/REGDB_E_CLASSNOTREG`. No WSL installer or distro reset ran.
- VST listener is available but optional pedalboard processing is unavailable.
- Broadcast kernel is online and idle; encoder qualification remains unverified.
- Authenticated user workflows, loaded models, actual capture/streaming and reboot
  persistence are separate gates. No blanket all-services acceptance is claimed.

Current receipts: `SERVICE_STARTUP_2026-11-14.json` and
`SERVICE_STARTUP_SUPPLEMENT_2026-11-14.json`. Private logs, original databases,
vector snapshots, credential handling and exact failure evidence remain under
`backups/services_start_20261114_v01/`; shared backups contain only reviewed
engineering summaries. The long-term goal remains ACTIVE and incomplete.
