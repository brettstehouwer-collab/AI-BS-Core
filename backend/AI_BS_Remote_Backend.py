import json
import os
import sys
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
from bullshit_orchestrator import NeuralRouter

app = FastAPI(title="AI-BS Airgapped Remote Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# =================================================================
# SAFE / AIRGAPPED ENDPOINTS ONLY
# =================================================================


# 1. Telemetry Monitoring (Read Only)
@app.get("/telemetry/status")
async def proxy_telemetry():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:8000/telemetry/status")
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except:
        return {"status": "error", "message": "Primary backend unreachable"}


# 2. Omni-Drive Database Search (Read Only)
@app.post("/api/omnidrive/search")
async def proxy_omnidrive_search(request: Request):
    try:
        body = await request.json()
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://localhost:8000/api/omnidrive/search", json=body
            )
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return {"status": "error", "message": str(e)}


# 3. Knowledge Base Vector Search (Read Only)
@app.post("/kb/search")
async def proxy_kb_search(request: Request):
    try:
        body = await request.json()
        async with httpx.AsyncClient() as client:
            r = await client.post("http://localhost:8000/kb/search", json=body)
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except Exception as e:
        return {"status": "error", "message": str(e)}


# 4. LLM Chat Streaming Proxy (Generation Model)
@app.api_route("/{full_path:path}", methods=["GET", "POST", "OPTIONS"])
async def catch_all_proxy(request: Request, full_path: str):
    if "chat/completions" in full_path:
        body = await request.body()
        req_json = json.loads(body) if body else {}

        if req_json.get("stream", False):

            async def stream_generator():
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        "http://localhost:8000/v1/chat/completions",
                        json=req_json,
                        timeout=300.0,
                    ) as r:
                        async for chunk in r.aiter_bytes():
                            yield chunk

            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "http://localhost:8000/v1/chat/completions",
                    json=req_json,
                    timeout=300.0,
                )
                return JSONResponse(status_code=r.status_code, content=r.json())
    elif "models" in full_path:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:8000/v1/models", timeout=10.0)
            return JSONResponse(status_code=r.status_code, content=r.json())

    return {
        "status": "blocked",
        "message": "Airgapped Remote Node blocks this execution path.",
    }


def main():
    print("============================================================")
    print("   [AIRGAPPED NODE] AI-BS Remote Backend Initializing...")
    print("============================================================")
    print("WARNING: This instance is running on Port 8010 for remote access.")
    print("SECURITY: Polyglot Execution and UI Mutations are HARD-BLOCKED.")
    print("============================================================")
    uvicorn.run(app, host="0.0.0.0", port=8010, log_level="warning")


if __name__ == "__main__":
    main()
