from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Dict
import re
from security.host_control_access import require_host_admin

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        try:
            await require_host_admin(websocket)
        except HTTPException:
            await websocket.close(code=1008, reason="Verified administrator authorization is required.")
            return False
        await websocket.accept()
        self.active_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in tuple(self.active_connections):
            try:
                await require_host_admin(connection)
                await connection.send_text(message)
            except (HTTPException, WebSocketDisconnect):
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws/telemetry/{industry}")
async def websocket_telemetry_endpoint(websocket: WebSocket, industry: str):
    if not await manager.connect(websocket):
        return
    try:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", industry):
            await websocket.close(code=1008, reason="Invalid industry identifier.")
            return
        # The old table has no proven producer, freshness or ownership contract.
        # Do not publish historical/synthetic rows as live telemetry or mutate
        # arbitrary SQLite journal settings during a WebSocket read.
        await websocket.send_json({"industry": industry, "status": "unavailable", "data": None,
            "reason": "A verified telemetry producer and record provenance are required."})
        await websocket.close(code=1013, reason="Verified telemetry producer unavailable.")
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
