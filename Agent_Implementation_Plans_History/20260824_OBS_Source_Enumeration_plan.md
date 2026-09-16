# Functional OBS-Style Sources & Scene Compositing

The goal is to upgrade the AI-BS Broadcast Daemon to support fully dynamic, modular sources just like OBS and Streamlabs, allowing you to compose a stream out of multiple capture devices, windows, and desktop feeds simultaneously.

## User Review Required

> [!WARNING]
> **FFmpeg Filtergraph Complexity**
> Dynamically composing multiple video feeds (e.g., Picture-in-Picture) and audio streams requires generating complex FFmpeg filtergraphs on the fly. Since we are using headless FFmpeg rather than a heavy compositor like OBS, layering too many 4K video sources might impact system performance. I will optimize the FFmpeg scaling filters. 

## Proposed Changes

### Backend (Python Daemon)
#### [MODIFY] [aibs_broadcast_daemon.py](file:///C:/AI-BS/backend/aibs_broadcast_daemon.py)
- **New API `GET /system/devices`**: Programmatically parses FFmpeg's `dshow` output to list all hardware video (e.g., Logitech BRIO, Cam Link) and audio inputs.
- **New API `GET /system/windows`**: Uses `win32gui` to enumerate all currently open, visible applications (e.g., Call of Duty, Chrome) so you can capture specific windows without capturing the whole desktop.
- **Dynamic FFmpeg Engine**: Modify the `/stream/start` endpoint to accept a list of sources. Instead of the hardcoded `[0:v]scale=1920:1080`, it will dynamically map `gdigrab` and `dshow` inputs into a layered `filter_complex` pipeline (e.g., Background Desktop + Picture-in-Picture Webcam + Multiple Audio Mixes).

### Frontend (React UI)
#### [MODIFY] [BroadcastStudio.jsx](file:///C:/AI-BS/frontend/src/components/BroadcastStudio.jsx)
- **Interactive Source Selection**: When clicking "Add Source", instead of instantly adding a generic placeholder, it will open a sub-menu to select the specific hardware device or application window using the new backend APIs.
- **Payload Updates**: When clicking "Start Streaming", the active `sources` list (along with their volume/opacity settings) will be serialized and sent to the backend to generate the exact layout.

## Verification Plan
1. **Device Enumeration**: Verify `/system/devices` and `/system/windows` correctly list the Logitech BRIO, USB microphones, and open apps.
2. **Dynamic UI**: Ensure the "Add Source" button provides dropdowns populated by the APIs.
3. **Stream Testing**: Add a "Desktop Capture", a "Video Capture Device", and a "Microphone". Start the stream and verify that FFmpeg boots successfully with the combined layout and audio mix.
