"""
Antigravity Omni-Mount Multi-Drive Environment Loader
Module: C:\\AI-BS\\backend\\core\\aibs_mount_loader.py

Loads and exposes connected multi-drive workspaces, model vaults,
and resources from C:\\AI-BS\\saved_data\\antigravity_omni_mounts.json.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

CONFIG_PATH = Path(r"C:\AI-BS\saved_data\antigravity_omni_mounts.json")

class AntigravityMountLoader:
    """Manages multi-drive asset paths across C:, D:, and E: drives."""
    
    _config: Optional[Dict[str, Any]] = None

    @classmethod
    def load_config(cls, force_reload: bool = False) -> Dict[str, Any]:
        """Loads or reloads the omni-mount manifest."""
        if cls._config is None or force_reload:
            if CONFIG_PATH.exists():
                try:
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        cls._config = json.load(f)
                except Exception as e:
                    cls._config = {"active_mounts": {}, "missing_paths": [], "error": str(e)}
            else:
                cls._config = {"active_mounts": {}, "missing_paths": []}
        return cls._config

    @classmethod
    def get_category_mounts(cls, category: str) -> Dict[str, str]:
        """Returns map of path -> status for a given category (core_workspaces, storage_and_models, resources_and_media)."""
        cfg = cls.load_config()
        return cfg.get("active_mounts", {}).get(category, {})

    @classmethod
    def get_all_active_paths(cls) -> List[str]:
        """Returns flat list of all connected mount paths."""
        cfg = cls.load_config()
        active_paths = []
        for cat, mounts in cfg.get("active_mounts", {}).items():
            for p, status in mounts.items():
                if status == "CONNECTED":
                    active_paths.append(p)
        return active_paths

    @classmethod
    def resolve_resource(cls, relative_subpath: str, category: Optional[str] = None) -> Optional[str]:
        """
        Attempts to resolve a relative subpath across all active mounts or a specific category.
        Returns the absolute string path if found, else None.
        """
        cfg = cls.load_config()
        categories = [category] if category else list(cfg.get("active_mounts", {}).keys())
        
        for cat in categories:
            mounts = cfg.get("active_mounts", {}).get(cat, {})
            for root_path in mounts.keys():
                candidate = Path(root_path) / relative_subpath
                if candidate.exists():
                    return str(candidate)
        return None

# Export singleton loader instance
mount_loader = AntigravityMountLoader
