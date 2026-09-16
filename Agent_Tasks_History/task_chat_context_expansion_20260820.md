# Task: BS-Chat Context Window Capacity Expansion & Stress Test Benchmark

- [ ] Task 1: Expand Ollama Context Window in Backend (`gateway_router.py`) <!-- id: 0 -->
  - Explicitly inject `"options": {"num_ctx": 8192}` (and dynamic scaling up to 16,384 tokens for RTX 4090) into Ollama POST requests
  - Add graceful error handling and token budget warnings if payload exceeds maximum VRAM context limit
- [ ] Task 2: Build Context Stress Test Endpoint `POST /api/v1/chat/stress-test` <!-- id: 1 -->
  - Benchmarks context retention across 1k, 2k, 4k, 8k, and 16k token payloads
  - Calculates retrieval precision for facts placed at start, middle, and end of massive prompt
- [ ] Task 3: Upgrade `ChatTab.jsx` with Live Token Gauge & Context Stress Test HUD <!-- id: 2 -->
  - Real-time token counter & context progress bar (0 / 8,192 tokens)
  - 1-Click "📊 Run Context Stress Test" button to benchmark BS-Chat context limits live
- [ ] Task 4: Version Bump, Build & Firebase Deployment <!-- id: 3 -->
  - Bump system version to `v5.36.0 (Phase 45)`
  - Deploy to Firebase Hosting and update ledgers
