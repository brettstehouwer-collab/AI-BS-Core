import asyncio
import json
from modules.syndication_router import execute_broadcast, BroadcastRequest

class MockRequest:
    headers = {"x-client-id": "stehouwer_publishing"}

async def test_30_nodes():
    req = BroadcastRequest(
        site_name="Stehouwer Publishing L.L.C.",
        target_url="https://stehouwer-publishing.com",
        feed_url="https://stehouwer-publishing.com/library",
        custom_message="Stehouwer Publishing Global Syndication"
    )
    print("Broadcasting to 30-Node Ultra-Syndication Matrix...")
    res = await execute_broadcast(req, MockRequest(), "stehouwer_publishing")
    print(f"Total Targets: {res['total_targets']}")
    print(f"Responded / Succeeded: {res['successful_targets']}")
    print("Node Results Preview:")
    for r in res['results']:
        print(f" - [{r['category'].upper()}] {r['target']} ({r['type']}): {r['status']} ({r['latency_ms']}ms) -> {r['response'][:40]}")

if __name__ == "__main__":
    asyncio.run(test_30_nodes())
