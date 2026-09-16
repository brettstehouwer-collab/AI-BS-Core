# Live Stream Integration & Ingestion (xZ9FOZ2g878) Plan

Integrate the requested YouTube live stream (`https://www.youtube.com/live/xZ9FOZ2g878`) across all three core AI-BS modules: (1) DAW Video Preview Monitor & Broadcast Studio, (2) Stream Reflex Teleprompter with lower-third shoutout triggers, and (3) Media Vault & ChromaDB vector database ingestion.

## Proposed Changes

### 1. DAW Video Preview Monitor & Broadcast Studio
#### [MODIFY] [VideoPreviewMonitor.jsx](file:///C:/AI-BS/frontend/src/components/daw/VideoPreviewMonitor.jsx)
- Add stream URL player mode supporting YouTube iframe embeds (`https://www.youtube.com/embed/xZ9FOZ2g878`) alongside HTML5 MP4 videos.
- Add stream preset `🔴 YouTube Live: xZ9FOZ2g878` with custom URL input box for live DAW audio scoring.

#### [MODIFY] [BroadcastStudio.jsx](file:///C:/AI-BS/frontend/src/components/BroadcastStudio.jsx)
- Embed live stream preview monitor option in the multi-camera switcher deck.

---

### 2. Autonomous Stream Reflex & Theatrical Teleprompter
#### [MODIFY] [aibs_broadcast_daemon.py](file:///C:/AI-BS/backend/aibs_broadcast_daemon.py)
- Add `/api/broadcast/stream/shoutout` endpoint on Port 8005 to dispatch real-time lower-third graphics ("Shoutout to the Live Stream!") to OBS.

#### [MODIFY] [TheatricalTeleprompter.jsx](file:///C:/AI-BS/frontend/components/TheatricalTeleprompter.jsx)
- Add a 1-click "📢 Broadcast Live Stream Shoutout" action pushing lower-third telemetry across `/ws/matrix`.

---

### 3. ChromaDB & Media Vault Ingestion
#### [NEW] [ingest_livestream_metadata.py](file:///C:/AI-BS/backend/scripts/ingest_livestream_metadata.py)
- Vectorize stream metadata, tags, and shoutout notes using `nomic-embed-text` into ChromaDB (`aibs_media_vault`) and persist to SQLite with `client_id: 'stehouwer_publishing'`.

---

## Verification Plan

### Automated Tests
- Run `ingest_livestream_metadata.py` to verify ChromaDB embedding and SQLite persistence.
- Test `http://127.0.0.1:8005/api/broadcast/stream/shoutout` endpoint.

### Manual Verification
- Deploy frontend to Firebase Hosting (`ai-bs-dashboard.web.app`).
- Verify stream embed and lower-third shoutout buttons in DAW Video Preview Monitor and Teleprompter.
