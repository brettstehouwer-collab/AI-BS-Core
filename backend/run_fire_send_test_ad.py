"""Module for testing Fire Send broadcast of video ads."""

import asyncio
import sys
from fastapi import Request
from modules.syndication_router import execute_broadcast, BroadcastRequest

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")


async def run_fire_send_test() -> None:
    """Execute Fire Send test broadcast against syndicated networks."""
    scope = {
        "type": "http",
        "headers": [(b"x-client-id", b"stehouwer_publishing")],
    }
    dummy_req = Request(scope=scope)

    target_url = "https://www.youtube.com/watch?v=rq2LZe3hcUU"
    req = BroadcastRequest(
        site_name="Stehouwer Publishing Video Showcase",
        target_url=target_url,
        feed_url=target_url,
        custom_message=f"Watch Now: {target_url}",
    )

    print(f"🔥 FIRE SEND TRIGGERED FOR: {target_url}")
    res = await execute_broadcast(req, dummy_req, "stehouwer_publishing")
    print(
        f"\nBroadcast Result: {res['status']} | "
        f"Successful Targets: {res['successful_targets']} / {res['total_targets']}"
    )
    for r in res["results"]:
        print(
            f"  - [{r['status']:<10}] {r['target']:<45} ({r['latency_ms']}ms) -> {r['response']}"
        )


if __name__ == "__main__":
    asyncio.run(run_fire_send_test())
