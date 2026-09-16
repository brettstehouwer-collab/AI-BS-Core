import json
import logging
from typing import Dict
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class VideoAgentManager:
    def __init__(self):
        # Maps user session_id to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Video Agent: Client {session_id} connected for WebRTC signaling.")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Video Agent: Client {session_id} disconnected.")

    async def broadcast_signal(self, sender_id: str, message: dict):
        """
        Broadcast SDP offers/answers or ICE candidates to all OTHER active participants.
        In a 1-to-1 or multi-party room, we route to peers. 
        For simplicity, this broadcasts to all peers except sender.
        """
        message['sender_id'] = sender_id
        for peer_id, connection in self.active_connections.items():
            if peer_id != sender_id:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending signal to {peer_id}: {e}")

video_agent_manager = VideoAgentManager()
