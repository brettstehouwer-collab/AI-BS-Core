import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [Unreal Signaling] - %(message)s')

# In-memory registry
streamers = set()
players = set()
player_counter = 100

players_map = {}

async def handler(websocket, *args, **kwargs):
    global player_counter
    client_type = "Streamer" # Assume streamer initially
    player_id = None
    streamers.add(websocket)
    
    # Epic Games Streamer Protocol: send config immediately
    await websocket.send(json.dumps({
        "type": "config",
        "peerConnectionOptions": {
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        }
    }))

    try:
        async for message in websocket:
            logging.info(f"Raw message received from {client_type}: {message}")
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")
            
            if msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong", "time": data.get("time")}))
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
                logging.info(f"Player {player_id} Connected from React UI.")
                
                # Notify streamers that a player joined
                for s in list(streamers):
                    await s.send(json.dumps({
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
                        await s.send(json.dumps(data))
                elif client_type == "Streamer":
                    target_id = str(data.get("playerId"))
                    if target_id in players_map:
                        await players_map[target_id].send(json.dumps(data))
                continue

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if client_type == "Streamer":
            streamers.discard(websocket)
            logging.info("Unreal Engine Streamer Disconnected.")
            for p in list(players):
                try:
                    await p.send(json.dumps({"type": "streamerDisconnected"}))
                except:
                    pass
        elif client_type == "Player":
            players.discard(websocket)
            if player_id in players_map:
                del players_map[player_id]
            logging.info(f"Player {player_id} Disconnected.")
            for s in list(streamers):
                try:
                    await s.send(json.dumps({"type": "playerDisconnected", "playerId": player_id}))
                except:
                    pass

async def main():
    port = 8888
    logging.info(f"Starting AI-BS Unreal Engine Pixel Streaming Signaling Server on ws://0.0.0.0:{port}")
    # Epic Games default streamer port is usually 8888, players connect to 80 (we'll unify on 8888 for local test)
    async with websockets.serve(handler, "0.0.0.0", port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down signaling server.")
