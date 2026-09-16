#!/usr/bin/env python3
"""
Automated Omni-Channel Broadcast & Campaign Matrix Test (v5.130.0)
Tests Multi-URL Multiplexing, Discord Webhook, Telegram, Bluesky/Mastodon,
and Dynamic Local Sitemap/Feed Synchronization.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from AI_BS_Backend import app
from modules.syndication_router import update_local_sitemap_and_feed

class TestOmniChannelSyndication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_1_local_sitemap_and_feed_sync(self):
        """Verify dynamic local sitemap.xml and feed.xml generation."""
        res = update_local_sitemap_and_feed(
            target_url="https://stehouwer-publishing.com/test-article",
            title="Omni-Channel Test Release",
            description="Testing automated RSS and sitemap injection engine."
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreater(len(res["updated_files"]), 0)
        print(f"\n[TEST PASS] Dynamic local sitemap & feed synced ({', '.join(res['updated_files'])}).")

    def test_2_omnichannel_broadcast_single_url(self):
        """Verify single URL omni-channel broadcast with social toggles."""
        payload = {
            "site_name": "Stehouwer Publishing Omni-Test",
            "target_url": "https://stehouwer-publishing.com",
            "feed_url": "https://stehouwer-publishing.com/feed.xml",
            "custom_message": "Automated Omni-Channel Broadcast Engine Active",
            "only_active": True,
            "channels": {
                "discord": True,
                "telegram": True,
                "bluesky": True,
                "mastodon": True,
                "sitemap": True
            }
        }
        resp = self.client.post("/api/syndication/broadcast", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["total_targets"], 20)
        self.assertGreater(data["successful_targets"], 10)
        
        # Verify omni-channel nodes exist in results
        results = data["results"]
        targets_hit = [r["target"] for r in results]
        self.assertIn("Discord Community Webhook", targets_hit)
        self.assertIn("Telegram Channel Broadcast", targets_hit)
        self.assertIn("Bluesky AT Protocol", targets_hit)
        self.assertIn("Mastodon / Fediverse", targets_hit)
        self.assertIn("Local Sitemap & RSS Feed Sync", targets_hit)
        print(f"[TEST PASS] Single-URL Omni-Channel Broadcast succeeded ({data['successful_targets']} / {data['total_targets']} nodes responding).")

    def test_3_multi_url_campaign_multiplexing(self):
        """Verify multi-URL campaign multiplexing (Full Media Footprint)."""
        multi_urls = [
            "https://stehouwer-publishing.com",
            "https://www.amazon.com/dp/B0H524NPXV",
            "https://www.imdb.com/name/nm12567135/",
            "https://www.youtube.com/@BrettStehouwer"
        ]
        payload = {
            "site_name": "Stehouwer Publishing Media Fleet",
            "target_url": "https://stehouwer-publishing.com",
            "feed_url": "https://stehouwer-publishing.com/feed.xml",
            "urls": multi_urls,
            "only_active": True
        }
        resp = self.client.post("/api/syndication/broadcast", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["multiplexed_urls"]), 4)
        print(f"[TEST PASS] Multi-URL Campaign Multiplexer verified with {len(multi_urls)} targets.")

if __name__ == "__main__":
    unittest.main()
