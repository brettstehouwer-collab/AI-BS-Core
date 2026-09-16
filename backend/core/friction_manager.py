import asyncio
import json
import logging
from typing import Dict, Optional
from fastapi import WebSocket

# ToolResult — graceful import so FrictionManager still works standalone
try:
    from tool_result import ToolResult

    _TOOL_RESULT_AVAILABLE = True
except ImportError:
    _TOOL_RESULT_AVAILABLE = False

logger = logging.getLogger(__name__)


class FrictionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.friction_locks: Dict[str, asyncio.Event] = {}
        self.friction_decisions: Dict[str, bool] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected for Friction events")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_friction(
        self,
        friction_id: str,
        action: str,
        trace: str,
        tool_result: Optional["ToolResult"] = None,
    ):
        """
        Broadcast a FRICTION_REQUIRED event to all connected WebSocket clients.

        Parameters
        ----------
        friction_id : str
            Unique ID for this friction event (used to resolve approval/denial).
        action : str
            Human-readable description of the action requiring approval.
        trace : str
            Legacy flat diagnostic trace string (kept for frontend backwards-compat).
        tool_result : Optional[ToolResult]
            Structured ToolResult envelope. If provided, the frontend modal
            receives the full status code, stdout, stderr, and DiagnosticTrace.
        """
        payload = {
            "type": "FRICTION_REQUIRED",
            "friction_id": friction_id,
            "action": action,
            "diagnostic_trace": trace,  # legacy flat field
        }
        # Enrich with full ToolResult if available
        if tool_result is not None and _TOOL_RESULT_AVAILABLE:
            payload["tool_result"] = tool_result.to_dict()
        message = json.dumps(payload)
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting friction to websocket: {e}")

    def resolve_friction(self, friction_id: str, approved: bool):
        if friction_id in self.friction_locks:
            self.friction_decisions[friction_id] = approved
            self.friction_locks[friction_id].set()
            return True
        return False


friction_manager = FrictionManager()
