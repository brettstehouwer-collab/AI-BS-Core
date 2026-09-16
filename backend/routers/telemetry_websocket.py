from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio
import sqlite3
import os

router = APIRouter()

RESOURCE_DIR = "E:\\AI_BS_Resources"

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/telemetry/{industry}")
async def websocket_telemetry_endpoint(websocket: WebSocket, industry: str):
    await manager.connect(websocket)
    db_path = os.path.join(RESOURCE_DIR, f"{industry}.db")
    
    try:
        while True:
            # Check for new telemetry data in SQLite every 1 second
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    try:
                        conn.execute("PRAGMA journal_mode=WAL;")
                        conn.execute("PRAGMA synchronous=NORMAL;")
                    except Exception:
                        pass
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    # Fetch latest 10 rows
                    cursor.execute("SELECT * FROM system_telemetry ORDER BY timestamp DESC LIMIT 10")
                    rows = cursor.fetchall()
                    data = [dict(row) for row in rows]
                    conn.close()
                    
                    await websocket.send_json({"industry": industry, "data": data})
                except Exception as e:
                    await websocket.send_json({"error": f"DB Read Error: {str(e)}"})
            else:
                await websocket.send_json({"error": f"Database {db_path} not found."})
                
            await asyncio.sleep(2)  # Stream frequency
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
