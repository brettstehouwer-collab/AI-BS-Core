"""
AI-BS Drop Sniffer Module - Central Sniffer Engine
Coordinates channels, evasion, actions, and watchdog heartbeat into a unified execution instance.
"""

import time
import os
import json
import requests
import threading
from datetime import datetime

from .evasion import EvasionEngine
from .actions import ActionDispatcher
from .hub_sync import HubSynchronizer
from .channels import ChannelManager

HEARTBEAT_FILE = r"C:\AI-BS\saved_data\cymatics_heartbeat.json"

class OmniDropSnifferEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(EvasionEngine.get_spoofed_headers())
        
        self.hub_sync = HubSynchronizer()
        self.exclusions = self.hub_sync.get_master_exclusion_set()
        
        self.actions = ActionDispatcher(self.session)
        self.channels = ChannelManager(self.session, self.actions, self.exclusions)
        self.is_running = False

    def update_heartbeat(self):
        try:
            with open(HEARTBEAT_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": time.time(),
                    "datetime": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "pid": os.getpid(),
                    "status": "HEALTHY",
                    "owned_count": len(self.exclusions),
                    "channels_stats": self.channels.latest_stats
                }, f, indent=2)
        except Exception:
            pass

    def start(self):
        self.is_running = True
        print(f"=====================================================", flush=True)
        print(f"  AI-BS ENTERPRISE DROP SNIFFER & WATCHDOG MODULE", flush=True)
        print(f"  Status: ACTIVE & FULLY ARMED", flush=True)
        print(f"  Exclusions Synced from Hub: {len(self.exclusions)} items", flush=True)
        print(f"  Filter: STRICT $0.00 FREE ONLY", flush=True)
        print(f"=====================================================", flush=True)

        # Launch background channel threads
        threading.Thread(target=self.channels.scan_catalog_channel, daemon=True).start()
        threading.Thread(target=self.channels.scan_sitemap_channel, daemon=True).start()
        threading.Thread(target=self.channels.probe_variant_channel, daemon=True).start()
        threading.Thread(target=self.channels.scan_youtube_channel, daemon=True).start()

        poll_count = 0
        while self.is_running:
            poll_count += 1
            self.update_heartbeat()
            if poll_count % 20 == 0:
                self.session.headers.update(EvasionEngine.get_spoofed_headers())
            self.channels.scan_dom_channel()
            time.sleep(0.25)

if __name__ == "__main__":
    engine = OmniDropSnifferEngine()
    engine.start()
