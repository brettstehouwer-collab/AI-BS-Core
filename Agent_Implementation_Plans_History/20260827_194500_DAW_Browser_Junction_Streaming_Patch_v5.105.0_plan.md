# DAW Browser Junction Streaming Patch Plan (v5.105.0)

## Overview
Resolved drive loading failure when accessing Cymatics and Muse Hub sound bank junctions in the DAW Studio Browser from Firebase Hosting and local instances.

## Fix Details
1. **Host Fallback:** `Browser.jsx` queries candidates `http://127.0.0.1:8080`, `http://localhost:8080`, `http://127.0.0.1:8000`, and relative.
2. **Backend Restart:** Reloaded FastAPI backend on port 8080.
3. **Audition URL Routing:** Dynamic backend base prefix for `/api/drive/stream`.
