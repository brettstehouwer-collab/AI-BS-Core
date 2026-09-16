# Add Advanced Settings to Broadcast Studio

This plan introduces an OBS-style **Advanced Settings** interface to the Broadcast Studio, allowing the user to precisely customize Video Bitrate, Audio Bitrate, and Keyframe Interval for their streams rather than relying on hardcoded defaults.

## User Review Required
No major architectural shifts, just UI additions and API payload expansions.

## Proposed Changes

### 1. `C:\AI-BS\frontend\src\components\BroadcastStudio.jsx`
- **State Initialization**: Add React state variables for `targetVideoBitrate` (6000k), `targetAudioBitrate` (160k), and `keyframeInterval` (2s).
- **Settings Modal Update**: In the `Hardware Encoder` tab, add input fields and dropdowns for these advanced settings.
- **API Payload Update**: Modify the `startStream` function to send the new bitrate and keyframe parameters in the JSON body to the backend daemon.

### 2. `C:\AI-BS\backend\aibs_broadcast_daemon.py`
- **Pydantic Model Update**: Expand the `StreamConfig` model to accept `video_bitrate`, `audio_bitrate`, and `keyframe_interval`.
- **Method Signature Update**: Update `daemon.start_stream()` to ingest these new arguments.
- **FFmpeg Command Generation**: Swap out the hardcoded `-b:v 6000k` and `-b:a 160k` arguments with the dynamic values passed from the UI. Calculate the `-g` (GOP/Keyframe interval) dynamically based on `FPS * keyframe_interval`.

## Verification Plan
### Manual Verification
1. I will rebuild the `AI-BS Matrix.exe` executable and deploy the frontend.
2. I will restart the backend Python broadcast daemon.
3. You can verify that the UI contains the new Advanced Settings in the A/V Settings Modal under the Encoder tab, and that changing them properly reflects in your stream quality.
