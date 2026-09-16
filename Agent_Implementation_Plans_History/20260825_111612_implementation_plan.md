# Implementation Plan: Mega-Upgrade Phase 5 (Streaming Core & UX)

This plan outlines the architecture for implementing the massive feature list you requested, including fixing the Facebook Live stream pipeline.

## 1. Facebook Live Streaming Fix (Tee Muxer Escaping)
**Issue:** The local FFmpeg `tee` muxer engine crashes or fails to connect to Facebook (`rtmps://`) and YouTube (`https://...&cid=...`) because it interprets special characters (`:`, `=`, `&`) as muxer syntax rather than URL strings.
**Fix:** Implement a robust `escape_tee_url` function in `aibs_broadcast_daemon.py` to escape `|`, `[`, `]`, `\`, `:`, `=`, `,`, `%` using backslashes, ensuring stable multi-casting to all endpoints.

## 2. 6-Track Isolated Audio Stem Recording & Hybrid MP4
**Implementation:** Rewrite the FFmpeg command generation in `aibs_broadcast_daemon.py` to use a `-filter_complex` graph.
- We will mix all inputs down to a Master Stereo track (Stream 0) for the `tee` RTMP live broadcast.
- We will use `-map` to route the individual `dshow` audio inputs into Tracks 2 through 6 of the archive file.
- We will append `-movflags +faststart+frag_keyframe+empty_moov+default_base_moof` to the archive output options to guarantee crash resilience.

## 3. NVENC Next-Gen Codecs & Tuning Presets
**Implementation:** 
- **Frontend (`BroadcastStudio.jsx`):** Add a dropdown for Video Codec (`h264_nvenc`, `hevc_nvenc`, `av1_nvenc`) and a dropdown for Tuning Preset (`p1` through `p7`).
- **Backend (`aibs_broadcast_daemon.py`):** Dynamically swap the `-c:v` parameter and add `-preset {p_value}` based on the incoming JSON payload.

## 4. Vertical 9:16 Shorts/TikTok Canvas Mode
**Implementation:**
- **Frontend:** Add a "Canvas Orientation" toggle button (Landscape 16:9 / Vertical 9:16). When toggled, swap the target resolution state from `1920x1080` to `1080x1920`.
- **Backend:** The existing scaling filter (`scale={w}:{h}`) will naturally handle the new resolution. However, we will add smart auto-cropping (`crop=...`) to ensure 16:9 sources are center-cropped into 9:16 rather than squished.

## 5. DirectShow Virtual Webcam Output
**Implementation:**
- Add a toggle for "Virtual Camera Output". 
- When enabled, append a secondary video output to the FFmpeg command using `dshow` or `v4l2` (since this is Windows, we use `dshow` and output to a registered virtual camera).
*Wait:* Natively, FFmpeg on Windows cannot output *to* a dshow virtual camera unless a driver like OBS Virtual Camera or e2eSoft VCam is installed.

## 6. Global Hotkeys & In-Game Controls
**Implementation:**
- Add a global `keydown` event listener in `BroadcastStudio.jsx` (and potentially `App.jsx` for the Electron wrapper).
- Map `Ctrl+Shift+S` (Start/Stop Stream), `Ctrl+Shift+M` (Mute Mic), `Ctrl+Shift+O` (Toggle Overlay), and `Ctrl+Shift+J` (Sidekick Joke/Hype payload).

---

## Open Questions
> [!IMPORTANT]
> 1. **Virtual Camera Driver:** Do you already have OBS Studio installed on this machine? If so, we can natively pipe our FFmpeg video output directly into the `OBS Virtual Camera` driver so it appears in Discord/Zoom.
> 2. **Audio Track Sources:** For the 6-track stems, do you have specific Windows device names (e.g. "Microphone (Yeti)", "VB-Audio Cable") you want hardcoded for Tracks 2-6, or should I create UI dropdowns so you can assign them manually?

Please review this architecture and provide feedback to the open questions so I can execute the code!
