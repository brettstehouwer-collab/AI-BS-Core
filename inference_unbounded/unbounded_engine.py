"""
unbounded_engine.py — AI-BS Continuous Streaming & Perpetual Token Decoder.
Wraps vLLM + LMCache with Server-Sent Events (SSE), transparent context continuation,
and disk swap caching for infinite output streams.
"""

import os
import json
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

router = APIRouter(prefix="", tags=["Unbounded Perpetual Streaming"])

# Port 8009 default to avoid collision with Go Gateway on 8000
VLLM_API_URL = os.getenv("VLLM_API_URL", "http://127.0.0.1:8009/v1")
DISK_STREAM_PATH = os.getenv("DISK_STREAM_PATH", "/tmp/ai_bs_active_stream.bin")

async def perpetual_generator(
    prompt: str, 
    model: str = "meta-llama/Llama-3.1-8B-Instruct",
    chunk_tokens: int = 4096
) -> AsyncGenerator[str, None]:
    """
    Decodes tokens continuously. If a turn hits max_tokens, it transparently
    chains the output to the prompt and continues generation without drop.
    """
    accumulated_context = prompt
    is_complete = False
    
    timeout_policy = httpx.Timeout(connect=15.0, read=None, write=30.0, pool=None)
    os.makedirs(os.path.dirname(os.path.abspath(DISK_STREAM_PATH)), exist_ok=True)
    
    async with httpx.AsyncClient(base_url=VLLM_API_URL, timeout=timeout_policy) as client:
        with open(DISK_STREAM_PATH, "ab", buffering=0) as swap_disk:
            while not is_complete:
                payload = {
                    "model": model,
                    "prompt": accumulated_context,
                    "max_tokens": chunk_tokens,
                    "stream": True,
                    "temperature": 0.7
                }
                
                try:
                    async with client.stream("POST", "/completions", json=payload) as response:
                        if response.status_code != 200:
                            yield f"data: {json.dumps({'error': 'Upstream runtime error', 'code': response.status_code})}\n\n"
                            return

                        finish_reason = None
                        cycle_text = ""

                        async for line in response.aiter_lines():
                            if not line.strip():
                                # Heartbeat ping to prevent reverse-proxy timeout
                                yield ": keep-alive\n\n"
                                continue
                                
                            if line.startswith("data: "):
                                raw_str = line[6:].strip()
                                if raw_str == "[DONE]":
                                    break

                                data = json.loads(raw_str)
                                choice = data["choices"][0]
                                token_delta = choice.get("text", "")
                                finish_reason = choice.get("finish_reason")

                                if token_delta:
                                    cycle_text += token_delta
                                    swap_disk.write(token_delta.encode("utf-8"))
                                    yield f"data: {json.dumps({'token': token_delta})}\n\n"

                        # Check for token window exhaustion and auto-chain
                        if finish_reason == "length":
                            accumulated_context += cycle_text
                            await asyncio.sleep(0.01)  # Context switch break
                        else:
                            is_complete = True
                            yield "data: [DONE]\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    return

@router.post("/v1/chat/unbounded")
@router.post("/api/chat/unbounded")
async def chat_unbounded_endpoint(request: Request):
    payload = await request.json()
    prompt = payload.get("prompt", "")
    model = payload.get("model", "meta-llama/Llama-3.1-8B-Instruct")
    chunk_tokens = int(payload.get("chunk_tokens", 4096))
    
    return StreamingResponse(
        perpetual_generator(prompt=prompt, model=model, chunk_tokens=chunk_tokens),
        media_type="text/event-stream"
    )

app = FastAPI(title="AI-BS Unbounded Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    # Standalone port 8089 avoids collision with AI_BS_Backend.py on port 8080
    port = int(os.getenv("UNBOUNDED_ENGINE_PORT", "8089"))
    print(f"[AI-BS Unbounded Engine] Listening on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
