import os
import sys
import time
import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from core.lexicon_service import LexiconService

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "sandbox_scratch", "ipc_benchmark"
    )
)

try:
    from shm_bridge import ShmBridge, TOPIC_ZERO_COPY_VECTOR_TENSORS, FLAG_HIGH_PRIORITY
except ImportError:
    TOPIC_ZERO_COPY_VECTOR_TENSORS = 0x0005
    FLAG_HIGH_PRIORITY = 0x02

    class ShmBridge:
        def init_shm_bridge(self):
            return 0

        def push_topic_event(self, topic, flags, data):
            return 0

        def close_shm_bridge(self):
            pass


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [ChromaVaultService] - %(message)s"
)

app = FastAPI(title="AI-BS ChromaDB Vector Vault Service", version="1.0.0")
bridge = ShmBridge()
bridge.init_shm_bridge()


class VectorQueryRequest(BaseModel):
    collection_name: str = "stehouwer_vector_memory"
    query_text: str
    top_k: int = 5


@app.get("/api/v1/vault/collections")
def list_collections():
    return {
        "collections": [
            {"name": "stehouwer_vector_memory", "count": 1420, "dimensions": 1536},
            {"name": "web_research_vault", "count": 850, "dimensions": 1536},
            {"name": "ast_codebase_embeddings", "count": 3200, "dimensions": 1536},
        ]
    }


@app.post("/api/v1/vault/query")
def query_vector_vault(req: VectorQueryRequest):
    start = time.time()
    
    # Lexicon Expansion
    expanded_terms = LexiconService.bulk_expand(req.query_text)
    enhanced_query = req.query_text
    if expanded_terms:
        all_syns = []
        for syns in expanded_terms.values():
            all_syns.extend(syns)
        enhanced_query = f"{req.query_text} (Synonyms: {', '.join(all_syns)})"
    
    # Mock high-velocity similarity search result
    results = [
        {
            "id": "doc_101",
            "distance": 0.12,
            "content": f"Matched context for query '{req.query_text}': Sub-microsecond SHM ring buffer architecture...",
            "metadata": {"source": "ringbuffer_multitopic.h"},
        },
        {
            "id": "doc_102",
            "distance": 0.18,
            "content": f"Secondary context: FastAPI WebSocket Gateway streaming at 20 Hz...",
            "metadata": {"source": "shm_websocket_gateway.py"},
        },
        {
            "id": "doc_103",
            "distance": 0.24,
            "content": f"Tertiary context: ComfyUI SDXL & Wan2.1 pipeline hooks...",
            "metadata": {"source": "comfyui_workflow_trigger.py"},
        },
    ]
    latency_us = (time.time() - start) * 1e6

    # Stream query telemetry onto SHM Topic 0x0005
    payload = f"QUERY|COLL:{req.collection_name[:10]}|TOP:{req.top_k}|LAT:{latency_us:.1f}u|Q:{enhanced_query[:15]}"
    bridge.push_topic_event(TOPIC_ZERO_COPY_VECTOR_TENSORS, FLAG_HIGH_PRIORITY, payload)

    return {
        "collection": req.collection_name,
        "query": enhanced_query,
        "original_query": req.query_text,
        "latency_us": round(latency_us, 2),
        "results": results[: req.top_k],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
