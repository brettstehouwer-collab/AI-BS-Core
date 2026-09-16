import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] WebRTCSignaling: %(message)s")

app = FastAPI()

# In-memory store for active connections and rooms
connections = {}

@app.websocket("/ws/webrtc/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    connections[client_id] = websocket
    logging.info(f"Client {client_id} connected for WebRTC signaling.")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            target_id = message.get("target")
            if target_id and target_id in connections:
                # Forward SDP offers, answers, and ICE candidates to the target
                logging.info(f"Routing signaling from {client_id} to {target_id}: {message.get('type')}")
                await connections[target_id].send_text(json.dumps({
                    "sender": client_id,
                    "type": message.get("type"),
                    "payload": message.get("payload")
                }))
            else:
                logging.warning(f"Target {target_id} not found.")
                
    except WebSocketDisconnect:
        logging.info(f"Client {client_id} disconnected.")
        if client_id in connections:
            del connections[client_id]

if __name__ == "__main__":
    logging.info("Starting WebRTC Signaling Server on port 8006...")
    uvicorn.run(app, host="127.0.0.1", port=8006)
