import asyncio
import sys
from modules.syndication_router import execute_broadcast, get_broadcast_history, BroadcastRequest

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    class DummyReq:
        headers = {'x-client-id': 'stehouwer_publishing'}
    
    req = BroadcastRequest(
        site_name="Stehouwer Publishing L.L.C.",
        target_url="https://stehouwer-publishing.com",
        feed_url="https://stehouwer-publishing.com/library"
    )
    print("Testing execute_broadcast...")
    res = await execute_broadcast(req, DummyReq(), "stehouwer_publishing")
    print(f"Broadcast Result: {res['status']} | Total: {res['total_targets']} | Success: {res['successful_targets']}")
    for r in res['results']:
        print(f"  - {r['target']} ({r['type']}): {r['status']} ({r['latency_ms']}ms) -> {r['response']}")

    print("\nTesting get_broadcast_history...")
    hist = await get_broadcast_history(limit=5, client_id="stehouwer_publishing")
    print(f"History records returned: {len(hist.get('history', []))}")

asyncio.run(main())
