# Implementation Plan - BS-Chat Context Window Expansion & Stress Test Benchmark

Expand the maximum context window capacity of BS-Chat to **8,192 tokens (~32,768 characters)** and provide a live **Context Window Stress Test & Token Gauge** tool to test context payload boundaries.

## Proposed Changes

### Backend Gateway Layer

#### [MODIFY] [gateway_router.py](file:///C:/AI-BS/backend/commercial_gateway/gateway_router.py)
1. **Dynamic Context Scaling (`num_ctx`)**:
   - Inject `"options": {"num_ctx": max(8192, min(16384, estimated_tokens + 1024)), "temperature": 0.3}` into all `http://127.0.0.1:11434/api/chat` calls in non-streaming and streaming handlers.
2. **Context Stress Test Endpoint**:
   - Create `POST /api/v1/chat/stress-test`: Accepts target token tier (`1k`, `2k`, `4k`, `8k`, `16k`), generates synthetic long-context document embedding hidden key facts at needle-in-haystack positions (beginning, middle, end), sends to BS-Chat, and measures accuracy, latency, and context retention.

---

### Frontend UI Layer

#### [MODIFY] [ChatTab.jsx](file:///C:/AI-BS/frontend/components/ChatTab.jsx)
1. **Live Context Token Gauge**:
   - Render a live token estimation badge in the input bar showing character count, estimated tokens, and percentage of 8,192 token limit used.
   - Highlight warning if input exceeds 8,192 tokens.
2. **"📊 Run Context Stress Test" Tool Button**:
   - Added to the Chat Action Bar. Clicking opens an interactive Context Stress Test Modal or runs a live 8k token context benchmark test, outputting exact latency, throughput, and context retrieval accuracy.

---

## User Review Required

> [!NOTE]
> Setting `num_ctx: 8192` utilizes ~4.2 GB VRAM on the local RTX 4090 GPU, ensuring zero external API cost and full local hardware acceleration.

## Verification Plan

### Automated Tests
- Test 8,192 token payload via stress test endpoint:
  ```powershell
  powershell -Command "C:\AI-BS\pyppeteer_env\Scripts\python.exe -c 'import requests; r = requests.post(\"http://127.0.0.1:8000/api/v1/chat/stress-test\", json={\"target_tier\":\"4k\"}); print(r.json())'"
  ```

### Manual Verification
- Open `ChatTab` in `http://localhost:5173`.
- Type or paste a large multi-paragraph text (e.g. 10,000+ characters), observe live Token Gauge update, click send, and verify complete response without truncation or 500 error.
