import asyncio
import json
import logging
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Unreal Signaling] - %(message)s')

app = FastAPI(title="AI-BS Unreal Engine Pixel Streaming Signaling Server (Port 8888)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory registry
streamers = set()
players = set()
player_counter = 100
players_map = {}

@app.get("/")
@app.get("/health")
def health_status():
    return {
        "status": "healthy",
        "service": "Unreal Engine Pixel Streaming Signaling",
        "port": 8888,
        "active_streamers": len(streamers),
        "active_players": len(players),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.websocket("/")
@app.websocket("/{full_path:path}")
async def ws_handler(websocket: WebSocket, full_path: str = ""):
    global player_counter
    await websocket.accept()
    client_type = "Streamer"  # Assume streamer initially
    player_id = None
    streamers.add(websocket)

    # Epic Games Streamer Protocol: send config immediately
    await websocket.send_text(json.dumps({
        "type": "config",
        "peerConnectionOptions": {
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        }
    }))

    try:
        while True:
            message = await websocket.receive_text()
            logging.info(f"Raw message received from {client_type}: {message}")
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "time": data.get("time")}))
                continue

            # Streamer explicitly identifying itself
            if msg_type in ["streamer", "endpointId"]:
                logging.info("Unreal Engine Streamer explicitly identified.")
                continue

            # Player connection (React Frontend)
            if msg_type == "player":
                client_type = "Player"
                streamers.discard(websocket)
                player_id = str(player_counter)
                player_counter += 1
                players.add(websocket)
                players_map[player_id] = websocket
                logging.info(f"Player {player_id} Connected from UI.")

                # Notify streamers that a player joined
                for s in list(streamers):
                    await s.send_text(json.dumps({
                        "type": "playerConnected",
                        "playerId": player_id,
                        "dataChannel": True,
                        "sfu": False
                    }))
                continue

            # Relay WebRTC Signaling Data & Custom Viewport Commands
            if msg_type in ["offer", "answer", "iceCandidate", "ui_command", "camera_switch", "avatar_preset", "render_profile"]:
                if client_type == "Player":
                    data["playerId"] = player_id
                    for s in list(streamers):
                        await s.send_text(json.dumps(data))
                elif client_type == "Streamer":
                    target_id = str(data.get("playerId"))
                    if target_id in players_map:
                        await players_map[target_id].send_text(json.dumps(data))
                continue

    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if client_type == "Streamer":
            streamers.discard(websocket)
            logging.info("Unreal Engine Streamer Disconnected.")
            for p in list(players):
                try:
                    await p.send_text(json.dumps({"type": "streamerDisconnected"}))
                except Exception:
                    pass
        elif client_type == "Player":
            players.discard(websocket)
            if player_id in players_map:
                del players_map[player_id]
            logging.info(f"Player {player_id} Disconnected.")
            for s in list(streamers):
                try:
                    await s.send_text(json.dumps({"type": "playerDisconnected", "playerId": player_id}))
                except Exception:
                    pass

if __name__ == "__main__":
    logging.info("Starting AI-BS Unreal Engine Pixel Streaming Signaling Server on http://0.0.0.0:8888")
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="warning")

