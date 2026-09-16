import importlib
import inspect
import logging
import os
import pkgutil
import sys
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, APIRouter

logger = logging.getLogger("AIBS_PluginLoader")
logger.setLevel(logging.INFO)

class PluginRegistry:
    """
    Dynamic Plugin Loader & Module Registry for AI-BS Matrix.
    Automatically discovers and mounts domain-isolated vertical plugins,
    API routers, background tasks, and database schemas.
    """
    def __init__(self):
        self.loaded_plugins: Dict[str, Dict[str, Any]] = {}

    def discover_and_mount_plugins(self, app: FastAPI, base_dirs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if base_dirs is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_dirs = [
                os.path.join(backend_dir, "modules"),
                os.path.join(backend_dir, "routers")
            ]

        results = []

        for b_dir in base_dirs:
            if not os.path.exists(b_dir):
                continue

            if b_dir not in sys.path:
                sys.path.insert(0, b_dir)

            # Discover packages and standalone router modules
            for finder, name, ispkg in pkgutil.iter_modules([b_dir]):
                if name.startswith("__"):
                    continue

                try:
                    module = importlib.import_module(name)
                    
                    # 1. Look for 'router' attribute
                    router = getattr(module, "router", None)
                    if isinstance(router, APIRouter):
                        app.include_router(router)
                        route_count = len(router.routes)
                        logger.info(f"[PluginLoader] Mounted router: '{name}' ({route_count} routes)")
                        plugin_info = {
                            "name": name,
                            "type": "package" if ispkg else "module",
                            "status": "active",
                            "routes": route_count,
                            "path": getattr(module, "__file__", "")
                        }
                        self.loaded_plugins[name] = plugin_info
                        results.append(plugin_info)

                    # 2. Check for optional module initialization hook
                    init_fn = getattr(module, "init_module", None)
                    if callable(init_fn):
                        init_fn(app)
                        logger.info(f"[PluginLoader] Initialized module hook: '{name}'")

                except Exception as e:
                    logger.warning(f"[PluginLoader] Could not load plugin '{name}': {e}")

        logger.info(f"[PluginLoader] Successfully mounted {len(results)} dynamic plugins/routers.")
        return results

    def get_plugin_summary(self) -> Dict[str, Any]:
        return {
            "total_plugins": len(self.loaded_plugins),
            "plugins": list(self.loaded_plugins.values())
        }

plugin_registry = PluginRegistry()
