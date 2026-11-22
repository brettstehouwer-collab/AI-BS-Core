import asyncio
import re

class TheatricalEventBus:
    def __init__(self):
        # Map of keywords/regexes to webhook URLs or local scripts
        self.triggers = {
            # Example: if the AI or User says this exactly, trigger the smoke machine
            r"\bsystem override delta\b": {
                "type": "webhook",
                "url": "http://localhost:9090/trigger/smoke",
                "description": "Trigger Stage Smoke Machine"
            },
            # Example: if the AI gets angry and outputs 'TERMINATE'
            r"\bTERMINATE\b": {
                "type": "script",
                "path": "./scripts/stage_blackout.sh",
                "description": "Trigger Stage Blackout"
            }
        }
        print("[TheatricalEventBus] Initialized with", len(self.triggers), "triggers.")

    async def scan_text(self, text: str) -> list:
        """
        Scans a block of text (either from user or AI) for hidden keywords.
        Fires off the appropriate hardware hook if a match is found.
        Returns a list of triggered descriptions for frontend visual indicators.
        """
        triggered_events = []
        for pattern, action in self.triggers.items():
            if re.search(pattern, text, re.IGNORECASE):
                print(f"[TheatricalEventBus] 🔥 TRIGGER HIT: {pattern}")
                triggered_events.append(action["description"])
                
                # Execute the hook asynchronously so we don't block the chat
                asyncio.create_task(self._execute_hook(action))
                
        return triggered_events

    async def _execute_hook(self, action: dict):
        try:
            if action["type"] == "webhook":
                # In a real scenario, use httpx to hit the IoT device
                print(f"[TheatricalEventBus] Executing Webhook: {action['url']}")
                # async with httpx.AsyncClient() as client:
                #     await client.post(action["url"])
            elif action["type"] == "script":
                print(f"[TheatricalEventBus] Executing Script: {action['path']}")
                # subprocess.Popen([action["path"]])
        except Exception as e:
            print(f"[TheatricalEventBus] ERROR executing hook: {e}")

# Global instance
theatrical_event_bus = TheatricalEventBus()
