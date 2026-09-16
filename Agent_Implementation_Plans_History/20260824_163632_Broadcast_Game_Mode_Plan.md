# Add Game Mode to Stream Broadcast Studio

The goal of this implementation is to introduce a **"Game Mode" (Efficiency Mode)** into the AI-BS Stream Broadcast setup. When enabled, this mode will aggressively kill background AI rendering daemons (Ollama and ComfyUI) to free up VRAM and reduce the baseline GPU power draw, thereby preventing the RTX 4090 transient power spikes that are tripping your PSU's Over-Current Protection. When disabled, it will cleanly relaunch the daemons.

## User Review Required
> [!IMPORTANT]
> The backend Python script will now use aggressive OS-level process management (`psutil` and `taskkill`) to shut down ComfyUI and Ollama. When you turn Game Mode **off**, the backend will spawn them silently in the background again. 
> 
> Please confirm if you want the toggle to be located in the **Stream Deck Quick Actions** panel of the Broadcast Studio.

## Proposed Changes

---

### Backend System Enhancements

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- **Enhance the `/api/system/efficiency-mode` endpoint:**
  - **Enable Mode (Kill):** 
    - Execute `taskkill /F /IM ollama.exe` to instantly kill local LLM inference.
    - Use Python's `psutil` to iterate through running processes and kill the specific `python.exe` instance that is running `ComfyUI\main.py` (leaving the FastAPI backend unharmed).
  - **Disable Mode (Relaunch):**
    - Launch `ollama serve` in the background (`CREATE_NO_WINDOW`).
    - Launch `C:\AI-BS\ComfyUI\run_nvidia_gpu.bat` in the background (`CREATE_NO_WINDOW`).

---

### Frontend UI Integrations

#### [MODIFY] [BroadcastStudio.jsx](file:///C:/AI-BS/frontend/src/components/BroadcastStudio.jsx)
- Add React state `gameModeEnabled` to track the status.
- Add an API function `toggleGameMode` to send the `POST` request to `http://127.0.0.1:8000/api/system/efficiency-mode`.
- Add a highly visible **"Game Mode (Eco)"** toggle button in the `deck` view (Stream Deck Quick Actions) alongside the Scene switchers.
- Style the button to light up Green or Red so you know when it's safe to launch Call of Duty.

## Verification Plan

### Automated Tests
None required for UI addition.

### Manual Verification
1. Open the AI-BS Desktop app.
2. Navigate to the Stream Broadcast studio.
3. Click the new **Game Mode** button in the Stream Deck section.
4. Verify via Task Manager that `ollama.exe` and ComfyUI's `python.exe` drop out of memory.
5. Launch `cod.exe` to confirm the PC does not crash.
6. Toggle Game Mode back off and verify Ollama and ComfyUI reload successfully.
