# AI-BS Music DAW 5-Phase Mega-Expansion Tasks

## Phase A: VST3 / Plugin Expansion (Port 8013)
- [x] **Task A.1**: Expose `/api/vst/parameters/{plugin_id}` and `/api/vst/set-param` in `backend/aibs_vst_daemon.py`.
- [x] **Task A.2**: Implement VST3 Channel FX Rack in `frontend/src/components/daw/Mixer.jsx` with real-time knob parameter mutation.

## Phase B: AI Music & Stem Generation
- [x] **Task B.1**: Implement Suno prompt structuring and local 4-stem separation in `backend/routers/ai_audio_router.py`.
- [x] **Task B.2**: Add Neural Stem Splitter & Suno AI drawer in `frontend/src/components/daw/Browser.jsx`.

## Phase C: MIDI & Piano Roll Upgrades
- [x] **Task C.1**: Wire Web MIDI API controller listener in `frontend/src/components/daw/PianoRoll.jsx` for hardware recording.
- [x] **Task C.2**: Add Chord Helper Matrix, scale quantization, and note velocity bar editor.

## Phase D: Arrangement & Mixing Workflow
- [x] **Task D.1**: Build 4-band Parametric Mastering EQ, Stereo Widener & LUFS Analyzer in `frontend/src/components/daw/audioMasteringChain.js`.
- [x] **Task D.2**: Add Track Automation Lanes in `frontend/src/components/daw/Playlist.jsx` and Sub-Mix Buses in `Mixer.jsx` / `dawStore.js`.

## Phase E: Live Performance & Theatrical Stream Sync
- [x] **Task E.1**: Connect DAW transport to `/ws/matrix` EventBus in `frontend/src/components/daw/MusicDAWStudioTab.jsx` for OBS camera cuts and UE5 DMX stage lighting triggers.
- [x] **Task E.2**: Compile frontend `npm run build`, deploy to Firebase Hosting, bump version to `v5.103.0`, and update master architectural ledgers.
