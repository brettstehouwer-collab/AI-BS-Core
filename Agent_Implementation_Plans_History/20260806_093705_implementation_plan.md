# Architectural Integration: Unreal Engine Pixel Streaming in AI-BS

This plan outlines the architecture and integration steps for embedding live, interactive 3D environments from Unreal Engine directly into the AI-BS React dashboard using Pixel Streaming and WebRTC. This will allow us to use a live 3D viewport for multiple clients and tools (e.g., Banquet Architect, generic 3D model design).

## User Review Required

> [!WARNING]
> This requires running a compiled Unreal Engine project locally on the RTX 4090 alongside the Python backend. To conserve VRAM and CPU overhead, we should maintain a single Unreal Engine "Master Hub" project that contains multiple levels (Banquet Hall, Product Studio, etc.). We will switch levels dynamically via API rather than launching multiple `.exe` instances.

## Open Questions Resolved

- **Unreal Project Status:** We are starting from scratch. You only have the engine installed at `C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64`.
- **Signaling Server:** Since we are using UE 5.8, the signaling server is bundled within the engine installation directory (typically under `Samples/PixelStreaming/WebServers/SignallingWebServer`).

## Division of Labor & User Review Required

> [!CAUTION]
> Because we do not have an existing Unreal project, we must establish a clear division of labor:
> 
> **My Role (AI Backend/Frontend):**
> 1. I will build the React `UnrealPixelStreamBridge.jsx` component.
> 2. I will update `AI_BS_Backend.py` and `Launch_AI_BS.bat` to automatically launch the Unreal Signaling Server and route traffic.
> 3. I will create a python script that you can run to automatically generate a basic `.uproject` with the Pixel Streaming plugin pre-enabled.
>
> **Your Role (Human/3D Design):**
> 1. You will need to open the generated project in the Unreal Editor (GUI).
> 2. You will need to physically design/import the 3D assets for the "Banquet Room" or "Light Visual Studio". I cannot autonomously sculpt or import 3D meshes to make it look like Noto's.
> 3. You will click "File -> Package Project -> Windows" to generate the final `.exe` that our backend will launch.

## Proposed Changes

### 1. Project Scaffolding
#### [NEW] `C:\AI-BS\scratch\create_unreal_project.py`
- A script to programmatically generate an `AI_BS_Hub.uproject` file in a new directory with the `"PixelStreaming"` plugin enabled in the JSON manifest.

### 2. Frontend Architecture
#### [NEW] `UnrealPixelStreamBridge.jsx`
- Implement a reusable React component using WebRTC to attach to the local signaling server feed.

#### [MODIFY] `HospitalityDemoSuiteTab.jsx`
- Add the "Launch Interactive 3D Studio" button inside the Banquet Architect module alongside the 2D ComfyUI generator.

### 3. Backend Orchestration
#### [MODIFY] `Launch_AI_BS.bat`
- Add execution logic to launch the Epic Games WebRTC Signaling Server from `C:\Program Files\Epic Games\UE_5.8\Engine\...`.

#### [MODIFY] `AI_BS_Backend.py`
- Register the Unreal Engine executable into the `DaemonManager`.

## Verification Plan

### Manual Verification
1. Boot the complete AI-BS ecosystem.
2. Verify that the Signaling Server and Unreal Engine processes boot successfully in the background.
3. Open the Noto Hospitality OS, navigate to Banquet Architect, and click "Launch Interactive 3D Studio".
4. Confirm the live video stream from Unreal Engine appears within the React component.
5. Verify bidirectional latency (e.g., clicking on the video feed correctly interacts with the 3D scene).
