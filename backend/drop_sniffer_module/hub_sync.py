"""
AI-BS Drop Sniffer Module - Cymatics Hub Synchronizer
Integrates with local Cymatics Hub data to maintain a live, automated exclusion list.
"""

import os
import json

HUB_DIR = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_User_Presets\Cymatics Hub"

class HubSynchronizer:
    def __init__(self, hub_dir=HUB_DIR):
        self.hub_dir = hub_dir

    def get_installed_plugins(self):
        inst_file = os.path.join(self.hub_dir, "installed.json")
        if os.path.exists(inst_file):
            try:
                with open(inst_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_installed_packs(self):
        packs_file = os.path.join(self.hub_dir, "pack-folders.json")
        if os.path.exists(packs_file):
            try:
                with open(packs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_cached_products(self):
        cached_file = os.path.join(self.hub_dir, "cached-products.json")
        if os.path.exists(cached_file):
            try:
                with open(cached_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_master_exclusion_set(self):
        owned = set()
        plugins = self.get_installed_plugins()
        for k in plugins.keys():
            k_clean = k.lower().strip()
            owned.add(k_clean)
            owned.add(k_clean.replace("-", " "))

        packs = self.get_installed_packs()
        for k, v in packs.items():
            k_clean = k.lower().strip()
            owned.add(k_clean)
            owned.add(k_clean.replace("-", " "))
            folder = v.get("folder_name", "")
            if folder:
                clean_f = folder.replace("Cymatics - ", "").replace("Cymatics-", "").lower().strip()
                owned.add(clean_f)
                owned.add(clean_f.replace("(", "").replace(")", "").replace("-", " ").strip())

        # Baseline exclusions for stream drops
        baseline = [
            "dope collection - bonus stash", "dope collection - vocals",
            "dope collection - drums", "dope collection - melodies",
            "mystery - 11 year anniversary edition", "destiny - analog melodies",
            "casino - baby keem inspired pack", "daydream - vocal loops",
            "cascade - vocal loops", "boom'n - drum loops", "boom'n - melodies",
            "apocalypse - launch edition"
        ]
        for b in baseline:
            owned.add(b)
            owned.add(b.replace("-", " ").strip())

        return owned

    def get_inventory_summary(self):
        plugins = self.get_installed_plugins()
        packs = self.get_installed_packs()
        return {
            "total_plugins": len(plugins),
            "plugins_list": sorted(list(plugins.keys())),
            "total_packs": len(packs),
            "packs_list": sorted(list(packs.keys())),
            "total_exclusions": len(self.get_master_exclusion_set())
        }
