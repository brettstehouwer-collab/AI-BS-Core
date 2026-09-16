# Task List: AI-BS Boot Sequence & Subsystem Port Binding Diagnostics

- [x] Comprehensive root-cause discovery across all 5 reported port binding warnings (8008, 1935, 8089, 4455, 8085) and launcher errors <!-- id: 0 -->
- [x] Present Interactive Implementation Plan for user review and line-by-line commenting <!-- id: 1 -->
- [x] Await explicit manual user confirmation before executing any modifications <!-- id: 2 -->
- [x] Apply Launch_AI_BS.bat fixes (unescape `&` on line 20, update `:WaitForPort` for mirrored WSL2 socket detection, remove obsolete 8008 & 4455 probes, fix WSL bio bridge daemon spawn) <!-- id: 3 -->
- [x] Update Electron Main (`frontend/electron/main.js`) to probe existing ports 8000 and 8080 before spawning child backend binaries <!-- id: 4 -->
- [x] Verify clean system boot and port probe execution <!-- id: 5 -->
- [x] Synchronize Master Architectural Ledger, Ecosystem Manual, version bumps, and historical archives <!-- id: 6 -->
