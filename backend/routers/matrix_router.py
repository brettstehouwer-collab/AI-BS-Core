"""
AI-BS Master Matrix Router & Unified EventBus WebSocket Gateway
Provides bidirectional pub-sub multiplexing across Go, Python daemons, and React frontends.
Channels: telemetry, obs, vst, social, doctor, general
"""

import json
import asyncio
from typing import Dict, Set, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["Matrix EventBus"])

class MatrixPublishPayload(BaseModel):
    channel: str = "general"
    event_type: str = "INFO"
    data: Dict[str, Any] = {}
    client_id: str = "stehouwer_publishing"

class MatrixConnectionManager:
    def __init__(self):
        # Map channel -> Set of WebSockets
        self.channel_subscriptions: Dict[str, Set[WebSocket]] = {
            "all": set(),
            "telemetry": set(),
            "obs": set(),
            "vst": set(),
            "social": set(),
            "doctor": set(),
            "general": set()
        }
        self.active_sockets: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_sockets.add(websocket)
        self.channel_subscriptions["all"].add(websocket)
        self.channel_subscriptions["general"].add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_sockets.discard(websocket)
        for channel_set in self.channel_subscriptions.values():
            channel_set.discard(websocket)

    def subscribe(self, websocket: WebSocket, channel: str):
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        self.channel_subscriptions[channel].add(websocket)

    def unsubscribe(self, websocket: WebSocket, channel: str):
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(websocket)

    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        target_sockets = set()
        if channel in self.channel_subscriptions:
            target_sockets.update(self.channel_subscriptions[channel])
        target_sockets.update(self.channel_subscriptions["all"])

        payload_str = json.dumps(message)
        dead_sockets = []

        for ws in target_sockets:
            try:
                await ws.send_text(payload_str)
            except Exception:
                dead_sockets.append(ws)

        for dead_ws in dead_sockets:
            self.disconnect(dead_ws)

manager = MatrixConnectionManager()

@router.websocket("/ws/matrix")
async def matrix_websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial handshake welcome
        await websocket.send_text(json.dumps({
            "channel": "system",
            "event": "HANDSHAKE_OK",
            "message": "Connected to AI-BS Matrix EventBus Multiplexer",
            "available_channels": list(manager.channel_subscriptions.keys())
        }))

        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
                action = msg.get("action")
                channel = msg.get("channel", "general")

                if action == "subscribe":
                    manager.subscribe(websocket, channel)
                    await websocket.send_text(json.dumps({
                        "channel": "system",
                        "event": "SUBSCRIBED",
                        "target_channel": channel
                    }))
                elif action == "unsubscribe":
                    manager.unsubscribe(websocket, channel)
                    await websocket.send_text(json.dumps({
                        "channel": "system",
                        "event": "UNSUBSCRIBED",
                        "target_channel": channel
                    }))
                elif action == "publish":
                    payload = msg.get("payload", {})
                    await manager.broadcast_to_channel(channel, {
                        "channel": channel,
                        "event": msg.get("event", "MESSAGE"),
                        "data": payload
                    })
                elif action == "ping":
                    await websocket.send_text(json.dumps({"channel": "system", "event": "PONG", "timestamp": asyncio.get_event_loop().time()}))
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"channel": "system", "event": "ERROR", "error": "Invalid JSON format"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@router.post("/api/matrix/publish")
async def publish_matrix_event(payload: MatrixPublishPayload):
    """
    REST endpoint for background Python/Go daemons to dispatch events into WebSocket channels.
    """
    event_data = {
        "channel": payload.channel,
        "event_type": payload.event_type,
        "data": payload.data,
        "client_id": payload.client_id
    }
    await manager.broadcast_to_channel(payload.channel, event_data)
    return {
        "status": "success",
        "channel": payload.channel,
        "active_clients": len(manager.active_sockets)
    }

@router.get("/api/matrix/channels")
async def get_matrix_channels():
    return {
        "total_connections": len(manager.active_sockets),
        "channels": {k: len(v) for k, v in manager.channel_subscriptions.items()}
    }
