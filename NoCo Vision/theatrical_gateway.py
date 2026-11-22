import asyncio
import logging
import json
import os
import requests
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import chromadb
from openai import AsyncOpenAI
import uuid

logger = logging.getLogger("TheatricalGateway")
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

app = FastAPI(title="Theatrical World Standalone Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://ai-bs-dashboard.web.app",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PlayCreateRequest(BaseModel):
    play_name: str

class ChatRequest(BaseModel):
    message: str

class TheatricalDirectorDaemon:
    def __init__(self):
        logger.info("Initializing Top-Level Theatrical Director Daemon...")
        self.chroma_db_path = r"C:\AI-BS\NoCo Vision\chroma_db"
        os.makedirs(self.chroma_db_path, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_db_path)
        
        self.comfyui_url = "http://127.0.0.1:8189/prompt"
        
        # We will use the OpenAI API interface. For Stehouwer LLM or Ollama, 
        # we point the base_url appropriately. Here we default to OpenAI for safety, 
        # but in a real setup this points to Stehouwer API or Local Ollama.
        self.llm_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", "dummy"))
        
        logger.info(f"Air-gapped ChromaDB initialized at {self.chroma_db_path}")

    def list_plays(self):
        collections = self.chroma_client.list_collections()
        # list_collections returns a list of Collection objects or names depending on version
        # Let's extract names safely.
        names = []
        for c in collections:
            if hasattr(c, 'name'):
                names.append(c.name)
            else:
                names.append(c)
        return names

    def create_play(self, play_name: str):
        try:
            self.chroma_client.create_collection(name=play_name)
            return True
        except Exception as e:
            logger.error(f"Error creating play {play_name}: {e}")
            return False

    async def upload_material(self, play_name: str, file_content: bytes, filename: str):
        try:
            collection = self.chroma_client.get_collection(name=play_name)
            # Naive chunking for text
            text = file_content.decode('utf-8', errors='ignore')
            chunk_size = 1000
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            
            ids = [str(uuid.uuid4()) for _ in chunks]
            metadatas = [{"source": filename} for _ in chunks]
            
            collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            return len(chunks)
        except Exception as e:
            logger.error(f"Error uploading material to {play_name}: {e}")
            raise e

    async def chat_with_play(self, play_name: str, message: str):
        try:
            collection = self.chroma_client.get_collection(name=play_name)
            # Query chroma
            results = collection.query(
                query_texts=[message],
                n_results=3
            )
            
            context = ""
            if results and 'documents' in results and len(results['documents']) > 0:
                context = "\n\n".join(results['documents'][0])
            
            system_prompt = f"You are a theatrical assistant. You only answer based on the context of the play provided. Context:\n{context}"
            
            response = await self.llm_client.chat.completions.create(
                model="gpt-4o-mini", # Fallback to standard OpenAI, can be swapped to stehouwer_llm
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error chatting with play {play_name}: {e}")
            raise e

    async def process_transcript(self, transcript: str):
        logger.info(f"Processing transcript: {transcript}")
        # Original logic for the Stage mic teleprompter/projector

daemon = TheatricalDirectorDaemon()

@app.get("/theatrical/plays")
async def get_plays():
    plays = daemon.list_plays()
    return {"plays": plays}

@app.post("/theatrical/plays/create")
async def create_play(req: PlayCreateRequest):
    success = daemon.create_play(req.play_name)
    if success:
        return {"status": "success", "play_name": req.play_name}
    raise HTTPException(status_code=400, detail="Failed to create play. It may already exist.")

@app.post("/theatrical/plays/{play_name}/upload")
async def upload_to_play(play_name: str, file: UploadFile = File(...)):
    content = await file.read()
    try:
        chunks_added = await daemon.upload_material(play_name, content, file.filename)
        return {"status": "success", "chunks_added": chunks_added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/theatrical/plays/{play_name}/chat")
async def chat_with_play(play_name: str, req: ChatRequest):
    try:
        reply = await daemon.chat_with_play(play_name, req.message)
        return {"status": "success", "reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/theatrical/toggle")
async def toggle_theatrical_mode(request: Request):
    data = await request.json()
    active = data.get("active", False)
    config_path = r"C:\AI-BS\backend\compute_schedule_config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = {}
        
    if active:
        config["current_mode"] = "theatrical_override"
        logger.info("Theatrical Stage Switch FLIPPED ON. Signaling Swarm to pause monetization.")
    else:
        config["current_mode"] = "auto_schedule"
        logger.info("Theatrical Stage Switch FLIPPED OFF. Signaling Swarm to resume monetization.")
        
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
        
    return {"status": "success", "theatrical_mode_active": active}

@app.websocket("/theatrical/audio_stream")
async def theatrical_audio_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("Theatrical Stage Mic Connected to Standalone Gateway.")
    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            if len(audio_chunk) > 0:
                transcript = "This is a simulated transcript from the standalone gateway."
                await daemon.process_transcript(transcript)
    except WebSocketDisconnect:
        logger.info("Theatrical Stage Mic Disconnected.")
    except Exception as e:
        logger.error(f"Stage Mic Error: {e}")

if __name__ == "__main__":
    logger.info("Starting Theatrical World Gateway on port 8001...")
    uvicorn.run("theatrical_gateway:app", host="0.0.0.0", port=8001, reload=True)
