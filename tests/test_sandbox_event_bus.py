import unittest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))
from core.aibs_event_bus import AIBS_EventBus

class TestSandboxEventBus(unittest.TestCase):
    def setUp(self):
        self.bus = AIBS_EventBus()
        self.bus._subscribers.clear()
        self.bus._event_history.clear()

    def test_wildcard_subscription_and_dispatch(self):
        received_events = []

        async def prestige_handler(event):
            received_events.append(event)

        self.bus.subscribe("events.prestige.*", prestige_handler)

        async def run_test():
            # Matching event
            await self.bus.publish(
                "events.prestige.new_lead",
                {"client_name": "Lake Michigan Fleet", "value_est": 4500},
                source="prestige_mobile_wash"
            )
            # Non-matching event
            await self.bus.publish(
                "events.notos.bar_inventory",
                {"item": "Tequila Blanco", "stock": 4},
                source="notos_enterprise"
            )
            # Another matching event
            await self.bus.publish(
                "events.prestige.invoice_drafted",
                {"invoice_id": "INV-2026-001", "amount": 4500},
                source="accounting_router"
            )

        asyncio.run(run_test())

        self.assertEqual(len(received_events), 2)
        self.assertEqual(received_events[0]["topic"], "events.prestige.new_lead")
        self.assertEqual(received_events[0]["payload"]["client_name"], "Lake Michigan Fleet")
        self.assertEqual(received_events[1]["topic"], "events.prestige.invoice_drafted")

    def test_event_history_ring_buffer(self):
        async def run_history():
            for i in range(10):
                await self.bus.publish(f"events.test.item_{i}", {"index": i})

        asyncio.run(run_history())
        history = self.bus.get_recent_events(limit=5)
        self.assertEqual(len(history), 5)
        self.assertEqual(history[-1]["payload"]["index"], 9)

if __name__ == "__main__":
    unittest.main()
