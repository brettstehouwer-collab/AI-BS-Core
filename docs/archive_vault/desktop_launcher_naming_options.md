# Desktop Launcher Naming Proposals (Unambiguous Differentiation)

To eliminate ambiguity between the full desktop application, the dedicated live video streaming tool, and the master daemon boot script, review the following proposed naming topologies.

---

## Current Shortcuts vs. Ambiguity Points

| Current Desktop Name | Target Path | Workload & Port | Why It Causes Confusion |
| :--- | :--- | :--- | :--- |
| **`AI-BS Sovereign Studio.lnk`** | `AI-BS Sovereign Studio.exe` (Port 5173) | Full Suite (DAW, Chat, CRM, Accounting) | Both this and Broadcast use the word "Studio". |
| **`AI-BS Broadcast Studio.lnk`** | `Launch_Broadcast_Studio.bat` (Port 5174 / 8088) | Dedicated Live Video, Cameras, Mic, NVENC | Shares the word "Studio"; purpose not immediately obvious. |
| **`AI-BS Matrix Boot.lnk`** | `Launch_AI_BS.bat` (All 18 ports) | Master background daemons, WSL2, Ollama, ComfyUI | "Matrix Boot" sounds like a game or movie rather than "Start All Servers". |

---

## Proposed Naming Topologies

### Option A: Role & Workload-Specific (Recommended)
Clearly describes the exact daily function of each icon:
1. **`AI-BS Main Workstation (Full Suite & DAW).lnk`**
   * *Opens:* Full application (Wave Studio DAW, Stehouwer LLM, Treasury, CRM) on Port 5173.
2. **`AI-BS Live Streaming & Video Stage.lnk`**
   * *Opens:* Dedicated video broadcast, virtual camera, NVENC streaming, and audio kernel on Port 5174 / 8088.
3. **`AI-BS Master Server Boot (All 18 Engines).lnk`**
   * *Runs:* Master orchestrator starting Ollama, ComfyUI, FastAPI, Go, ChromaDB, and WSL2.

---

### Option B: Clean & Direct (Concise)
Short, high-contrast labels without parentheses:
1. **`AI-BS Primary Desktop.lnk`** (Main app on Port 5173)
2. **`AI-BS Live Broadcast.lnk`** (Video & streaming station on Port 5174)
3. **`AI-BS Engine Start.lnk`** (Background servers boot)

---

### Option C: Numerical Workflow Sequence
Orders the icons so you know what order to use them:
1. **`1 - Start AI-BS Background Servers.lnk`** (Run this first when booting up)
2. **`2 - Open AI-BS Sovereign Studio.lnk`** (Run this for daily work & DAW)
3. **`3 - Open AI-BS Live Streamer.lnk`** (Run this when doing live broadcasts/podcasts)
4. **`4 - Stop All AI-BS Engines.lnk`** *(Renamed `AI-BS Shutdown.lnk`)*

---

## Action Plan Upon Confirmation
Once you select your preferred option (or specify custom names):
1. Rename the physical `.lnk` shortcut files on `C:\Users\footb\OneDrive\Desktop`.
2. Verify target paths, working directories, and icons remain 100% intact.
3. Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.
