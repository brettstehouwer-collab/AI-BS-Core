---
name: aibs-cluster-engine
description: >-
  Enterprise distributed computing, zero-loss durable workflow orchestration,
  Rust ASGI acceleration, multi-threaded caching, binary gRPC IPC, and WebRTC SFU media
  streaming for the AI-BS Sovereign Intelligence Ecosystem.
---

# AI-BS Sovereign Cluster & High-Performance Distributed Engine

This skill provides the operational blueprints, execution procedures, and diagnostics for the
6-tier distributed computing, streaming, and durable execution architecture of AI-BS:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AI-BS CLUSTER TOPOLOGY                         │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Rust ASGI Core         : Granian (Port 8080) with Uvicorn fallback  │
│ 2. High-Throughput Stream : NATS JetStream (Port 4222 / in-process)    │
│ 3. Zero-Loss Durability   : Temporal.io (Port 7233 / state machine)    │
│ 4. Multi-Threaded Cache   : Dragonfly (Port 6379 / Direct RAM SHM)     │
│ 5. Binary Serialization   : gRPC & Protocol Buffers (backend/proto/)   │
│ 6. WebRTC SFU Media Relay : Mediasoup C++ Core (Port 3001 Node Gateway)│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Architectural Components & Port Matrix

| Tier | Component | Protocol / Port | Primary Role |
| :--- | :--- | :--- | :--- |
| **ASGI Engine** | `Granian (Rust/Tokio)` | HTTP/2, WS / `:8080` | High-RPS execution of FastAPI Core with Uvicorn fallback. |
| **Stream Broker** | `NATS JetStream` | NATS / `:4222` | Sub-millisecond pub/sub, sequence tracking, and cross-node streams. |
| **Durable Tasks** | `Temporal.io` | gRPC / `:7233` | Zero-loss stateful execution for Wan2.1 rendering and audio DSP. |
| **In-Memory Store**| `Dragonfly` | Redis / `:6379` | Multi-threaded vector cache & session state across 32 cores. |
| **Direct Hardware**| `SHM Ring Buffer` | Direct RAM / `:8010`| 740,000 pkts/sec raw hardware telemetry without serialization. |
| **Binary IPC** | `gRPC Protobuf` | HTTP/2 / `:8000` | Microsecond daemon-to-daemon calls between Go and Python. |
| **Media SFU** | `Mediasoup C++` | WebRTC / `:3001` | Multi-party audio/video routing & Omnistudio camera feeds. |

---

## 2. Python Engine Integration

All cluster services are accessible in-process through singletons in `backend/core/`:

```python
# 1. NATS JetStream Messaging
from backend.core.aibs_nats_broker import nats_broker
await nats_broker.publish("telemetry.rtx4090", {"temp": 32, "vram_mb": 10520})

# 2. Dragonfly Multi-Threaded Cache
from backend.core.aibs_dragonfly_cache import dragonfly_cache
dragonfly_cache.set("session:token", {"user": "stehouwer", "role": "admin"}, ttl_seconds=3600)
cached_user = dragonfly_cache.get("session:token")

# 3. Temporal Durable Workflows
from backend.core.aibs_temporal_orchestrator import temporal_orchestrator
result = await temporal_orchestrator.execute_durable_workflow(
    workflow_type="wan2.1_render",
    params={"prompt": "Dr. Vance blast doors", "duration": 5}
)
```

---

## 3. Launch & Verification Procedures

1. **Launch Granian Rust ASGI Core:**
   ```powershell
   python backend/granian_launcher.py
   ```
2. **Verify NATS JetStream & Dragonfly Cache:**
   ```powershell
   python -c "from backend.core.aibs_nats_broker import nats_broker; from backend.core.aibs_dragonfly_cache import dragonfly_cache; print('NATS:', nats_broker.get_stats()); print('Dragonfly:', dragonfly_cache.get_stats())"
   ```
3. **Verify Standalone Pytest Suite:**
   ```powershell
   pytest native_studio/test_native_studio.py -v
   ```
