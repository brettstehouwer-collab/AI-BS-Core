import asyncio
import fnmatch
import time
import logging
from typing import Callable, Dict, List, Any, Optional
import json

logger = logging.getLogger("AIBS_EventBus")
logger.setLevel(logging.INFO)

class AIBS_EventBus:
    """
    High-Performance Async Event Bus & Cross-Vertical Message Broker.
    Connects Prestige Mobile Wash, Noto's Enterprise OS, Project NoCo,
    Master Accounting, and ComfyUI Studio into a unified real-time event loop.
    """
    _instance: Optional['AIBS_EventBus'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIBS_EventBus, cls).__new__(cls)
            cls._instance._subscribers: Dict[str, List[Callable]] = {}
            cls._instance._event_history: List[Dict[str, Any]] = []
            cls._instance._max_history = 1000
        return cls._instance

    def subscribe(self, pattern: str, callback: Callable):
        """Subscribes an async or sync callback to a topic pattern (e.g. 'events.prestige.*')."""
        if pattern not in self._subscribers:
            self._subscribers[pattern] = []
        if callback not in self._subscribers[pattern]:
            self._subscribers[pattern].append(callback)
            logger.info(f"Subscribed callback {callback.__name__} to pattern '{pattern}'")

    def unsubscribe(self, pattern: str, callback: Callable):
        """Unsubscribes a callback from a topic pattern."""
        if pattern in self._subscribers and callback in self._subscribers[pattern]:
            self._subscribers[pattern].remove(callback)

    async def publish(self, topic: str, payload: Dict[str, Any], source: str = "core"):
        """Publishes an event to all matching subscribers asynchronously."""
        event = {
            "topic": topic,
            "payload": payload,
            "source": source,
            "timestamp": time.time()
        }

        # Store in event history (capped ring buffer)
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Dispatch to matching subscribers
        tasks = []
        for pattern, callbacks in list(self._subscribers.items()):
            if fnmatch.fnmatch(topic, pattern):
                for cb in callbacks:
                    if asyncio.iscoroutinefunction(cb):
                        tasks.append(asyncio.create_task(cb(event)))
                    else:
                        try:
                            cb(event)
                        except Exception as e:
                            logger.error(f"Error in sync subscriber callback {cb.__name__}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def publish_sync(self, topic: str, payload: Dict[str, Any], source: str = "core"):
        """Synchronous wrapper for publishing when called from synchronous threads."""
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(self.publish(topic, payload, source), loop)
        except RuntimeError:
            asyncio.run(self.publish(topic, payload, source))

    def get_recent_events(self, limit: int = 50, topic_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns recent events matching an optional topic filter."""
        events = self._event_history
        if topic_filter:
            events = [e for e in events if fnmatch.fnmatch(e["topic"], topic_filter)]
        return events[-limit:]

event_bus = AIBS_EventBus()
