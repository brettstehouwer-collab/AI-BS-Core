# Mission Specification: 1:1 Universal Screenwriting Parity, Cross-Tool Pipeline Dispatch & v5.321.0 Standalone Executable Release

**Date:** 2026-10-15  
**Target Version:** v5.321.0  
**Scope:** Native Studio Screenwriting 1:1 Parity, Direct Headless Script-to-Chunk Dispatch, Full PyInstaller/Inno Setup Build & Authenticode Signing  

---

## 1. Resolved Architectural Decisions (Grill Session Findings)

### Branch 1: Deep Subsystem Interaction & Data Flow
- **Decision:** Direct Headless Script-to-Chunk Parser.
- **Implementation:**
  - `ScreenwritingNativeView._jump_to_scene_beat(beat)`: Immediately scrolls and highlights the active scene heading in Editor and Paginated Page View.
  - `ScreenwritingNativeView._animate_scene_beat(beat)`: Packages the scene slug and action beats directly into `video_page.txt_scene_prompt`, switches subtab to Video Studio, and logs execution.
  - `ScreenwritingNativeView._parse_active_editor_into_comfy()`: Parses the active screenplay into 130 WPM pacing chunks for Port 8189/8188 ComfyUI pipeline execution.
  - Table Read Multi-Voice Studio: Maps character dialogue blocks directly into WASAPI audio synthesis buffers with pitch-shifted neural voice profiles.

### Branch 2: Milestone Versioning & Ledger Parity
- **Decision:** Incremental Patch Increment to `v5.321.0`.
- **Target Files:**
  - `frontend/package.json`
  - `version.txt`
  - `native_studio/__init__.py`
  - `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`
  - `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`
  - `SAVED_CHECKPOINT.md`
  - `MASTER_HISTORICAL_INDEX.md`
  - `MASTER_HANDOFF_CHRONOLOGY.md`

### Branch 3: Binary Compilation & Authenticode Code-Signing
- **Decision:** Full Production Pipeline.
- **Workflow:**
  1. Compile standalone 64-bit Direct2D executable: `dist/AI_BS_Studio.exe` via PyInstaller with `--windowed`, `--uac-admin`, and embedded asset bundle.
  2. Compile sovereign installer: `dist/AI_BS_Studio_Setup.exe` via Inno Setup (`ISCC.exe installer/setup_script.iss`).
  3. Apply Authenticode SHA-256 digital signature to both executables using `scripts/sign_authenticode.ps1` (`CN=Stehouwer Advertising`).
  4. Verify byte parity across all 4 frontend mirror directories.
