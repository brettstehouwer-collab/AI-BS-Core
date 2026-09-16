# Banquet Architect - Phase 2 Implementation Plan

This plan addresses the next steps defined in the `RESUME_BANQUET_ARCHITECT_PHASE2` save point.

## Open Questions
> [!WARNING]
> Before proceeding, please confirm the following:
> 1. **Voice Transcription:** I plan to use the browser's native **Web Speech API** (SpeechRecognition) for the voice transcription layer to keep it lightweight and fast without needing a backend audio model. Is this acceptable, or do you prefer a backend transcription model (e.g., Whisper)?
> 2. **Actor/Material Spawning Defaults:** I will add `spawnActors` (list) and `materialOverride` (string) to the NLP schema. Are there any specific Actors (e.g., "Dance Floor", "Stage") or Materials (e.g., "Marble", "Hardwood") you want me to explicitly instruct the LLM about in the prompt?

## Proposed Changes

### Backend Updates

#### [MODIFY] [demo_noto.py](file:///C:/AI-BS/backend/demo_noto.py)
- **Extend NLP Orchestrator (`handle_media_assistant_nlp`):**
  - Update the `system_prompt` to include new actionable keys: `spawnActors` (array of strings, e.g., "dance_floor", "dj_booth", "stage") and `materialOverride` (string, e.g., "marble", "hardwood", "carpet").
  - Update the expected JSON schema to return these new fields in `state_updates`.
- **Handle Unreal Web Remote API Edge Cases (`handle_unreal_remote_control`):**
  - Add more specific error handling for `aiohttp.ClientConnectorError` (offline/connection refused).
  - Ensure the "warning" status is consistently returned with a clear "Unreal Engine Offline" message so the frontend can catch it and display a Toast or Banner.

### Frontend Updates

#### [MODIFY] [BanquetArchitectTab.jsx](file:///C:/AI-BS/frontend/components/BanquetArchitectTab.jsx)
- **Voice Transcription Integration:**
  - Add a microphone button next to the Chat Input.
  - Implement `window.webkitSpeechRecognition` to capture voice, transcribe it in real-time, and populate the `chatInput` field.
- **Unreal Engine Offline State Handling:**
  - Update `handleSyncToUnreal` to read the response from the backend.
  - If `data.status === 'warning'`, display a non-blocking toast/alert letting the user know Unreal Engine is disconnected but the frontend state is saved.
- **Support New 3D States (Actor/Material):**
  - Add React state for `spawnActors` (array) and `materialOverride` (string).
  - Update the AI Assistant response handler to auto-apply these new states.
  - Add UI controls (e.g., multi-select/checkboxes for Actors, dropdown for Materials) in the 3D Remote Control Panel.
  - Include these new states in the payload sent to `unreal-remote-control`.

## Verification Plan

### Manual Verification
1. Open the Banquet Architect Tab.
2. Click the Microphone icon and say "Set up a corporate gala with 25 tables, add a dance floor, and use marble flooring."
3. Verify the AI Assistant auto-updates the UI to select 25 tables, check the "Dance Floor" actor, and select "Marble" material.
4. Verify clicking "Push to 3D Studio" while Unreal is closed displays an "Unreal Engine Offline" warning banner, but the UI state remains intact.
