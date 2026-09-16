import time
import json
import asyncio
import logging
from typing import Dict, Any, Callable, List, Set, Optional

logger = logging.getLogger("MatrixEventBus")

class MatrixEventBus:
    def __init__(self, history_limit: int = 50):
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self.history: List[Dict[str, Any]] = []
        self.history_limit = history_limit
        self._lock = asyncio.Lock()

    async def subscribe(self, topic: str) -> asyncio.Queue:
        async with self._lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = set()
            queue = asyncio.Queue()
            self.subscribers[topic].add(queue)
            return queue

    async def unsubscribe(self, topic: str, queue: asyncio.Queue):
        async with self._lock:
            if topic in self.subscribers and queue in self.subscribers[topic]:
                self.subscribers[topic].remove(queue)

    async def publish(self, topic: str, event: str, data: Dict[str, Any], source: str = "fastapi"):
        envelope = {
            "topic": topic,
            "event": event,
            "data": data,
            "timestamp": time.time(),
            "source": source
        }
        
        # Store in circular history buffer
        self.history.append(envelope)
        if len(self.history) > self.history_limit:
            self.history.pop(0)

        async with self._lock:
            # Deliver to exact topic subscribers + wildcard '*' subscribers
            targets = self.subscribers.get(topic, set()).copy()
            targets.update(self.subscribers.get("*", set()).copy())
            for q in targets:
                try:
                    q.put_nowait(envelope)
                except asyncio.QueueFull:
                    pass

    def get_recent_events(self, topic: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if topic and topic != "*":
            filtered = [e for e in self.history if e["topic"] == topic]
            return filtered[-limit:]
        return self.history[-limit:]

matrix_event_bus = MatrixEventBus()
