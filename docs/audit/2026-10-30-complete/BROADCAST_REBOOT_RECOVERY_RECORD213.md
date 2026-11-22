# Broadcast restart and preview recovery — Record213

October 31, 2026, America/New_York. Studio: AI-BS v5.329.86.

The screenshot's `owner unverified` hold came from a stale private IPC record. Its coordinator and encoder process creation times were both earlier than the current Windows boot, yet the record still said running. No matching coordinator was present. The installed client refused both Start and preview because it could not verify those dead processes.

The source client now recognizes a proven previous-boot session and permits a fresh start through its existing mutex and process-identity checks. Current-boot, missing or invalid identity metadata remains held. The core startup script also archives and resets proven previous-boot IPC, which lets the existing installed v5.329.86 client recover after the next reboot without bypassing ownership checks. It starts no broadcast automatically and never kills an unverified PID. No recording, archive or stream credential was deleted.

The requested broadcast was started using the saved enabled Twitch, YouTube, Kick and Facebook destinations, automatic game selection and generated silence. A fresh coordinator verified a game source, encoded-frame counts advanced, and the local HLS preview URL returned HTTP 200. A frame decoded from that URL showed Fortnite, rather than the desktop or a placeholder. The source and installed GUI are separate: the physical pixels currently displayed in Studio and remote platform acceptance were not observed through computer control and are not claimed verified.

Local evidence: `record213/broadcast_recovery213.json`, `record213/preview_frame213.jpg`, the original screenshot (where available), and the shared `record212/final_verification212_213.xml`. The focused coordinator/reboot suite passed 40 tests plus 13 subtests. The full October7/core/broadcast suite passed 131 tests plus 18 subtests; browser checks passed seven tests.

Core services on 8080, 8000, 11434, 5173 and 20243 returned HTTP 200. Their existing process identities were preserved. Live trading dispatch remains disabled; its two control files and two protected ledgers retain their recorded hashes. Audio and microphones were not configured.

All records remain local at the user's request. Future Drive uploads must use the existing audit folder; no alternate folder was created.
