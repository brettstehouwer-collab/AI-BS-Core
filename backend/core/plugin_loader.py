"""Deterministic registration; initialization is separately and truthfully reported."""
import contextlib
import copy
import importlib
import inspect
import logging
import os
import pkgutil
import sys
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, APIRouter

logger = logging.getLogger("AIBS_PluginLoader")

@contextlib.asynccontextmanager
async def _held_lifespan(app):
    yield

def collect_route_metadata(routes):
    """Read bounded registration structure, including FastAPI lazy include slots.

    Never build effective route/dependency contexts or invoke endpoint handlers.
    """
    from itertools import islice
    from starlette.routing import Mount, Route, WebSocketRoute
    try:
        from fastapi.routing import _IncludedRouter
        included_types = (_IncludedRouter,)
    except ImportError:
        included_types = ()
    max_routes, max_depth, max_visits = 1000, 8, 4000
    rows, duplicates, seen = [], [], {}
    truncated = False
    visits = 0

    def walk(items, prefix="", depth=0, ancestors=frozenset()):
        nonlocal truncated, visits
        for route in islice(items, max_visits + 1):
            visits += 1
            if visits > max_visits or len(rows) >= max_routes:
                truncated = True
                break
            if isinstance(route, included_types):
                if depth >= max_depth or id(route) in ancestors:
                    truncated = True
                else:
                    walk(route.original_router.routes, prefix + route.include_context.prefix,
                         depth + 1, ancestors | {id(route)})
                continue
            path = prefix + str(getattr(route, "path", ""))
            kind = "mount" if isinstance(route, Mount) else "websocket" if isinstance(route, WebSocketRoute) else "http" if isinstance(route, Route) else "other"
            methods = sorted(route.methods or []) if kind == "http" else []
            index = len(rows)
            rows.append({"index": index, "kind": kind, "path": path[:2048],
                         "name": str(getattr(route, "name", "") or "")[:256],
                         "methods": methods, "depth": depth})
            for method in methods or [kind]:
                key = (kind, method, path)
                if key in seen:
                    duplicates.append({"kind": kind, "method": method, "path": path[:2048],
                                       "first_index": seen[key], "index": index})
                else:
                    seen[key] = index
            if kind == "mount":
                if depth >= max_depth or id(route) in ancestors:
                    truncated = True
                else:
                    walk(route.routes, path, depth + 1, ancestors | {id(route)})
    walk(routes)
    return {"routes": rows, "duplicates": duplicates, "truncated": truncated,
            "limits": {"routes": max_routes, "depth": max_depth, "visits": max_visits}}

class PluginRegistry:
    def __init__(self):
        self.loaded_plugins: Dict[str, Dict[str, Any]] = {}

    def discover_and_mount_plugins(self, app: FastAPI, base_dirs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if base_dirs is None:
            base_dirs = [os.path.join(backend_dir, name) for name in ("modules", "routers")]
        background = os.getenv("AI_BS_BACKEND_BACKGROUND_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
        results = []
        discovered = set()
        for b_dir in sorted(base_dirs, key=lambda value: os.path.normcase(os.path.abspath(value))):
            if not os.path.isdir(b_dir):
                continue
            if b_dir not in sys.path:
                sys.path.insert(0, b_dir)
            for _, name, ispkg in sorted(pkgutil.iter_modules([b_dir]), key=lambda item: item.name):
                if name.startswith("__") or not name.isidentifier():
                    continue
                normalized = os.path.normcase(os.path.abspath(b_dir))
                package = next((p for p in ("modules", "routers") if normalized == os.path.normcase(os.path.join(backend_dir, p))), None)
                module_name = f"{package}.{name}" if package else name
                info = {"name": name, "module": module_name, "type": "package" if ispkg else "module",
                        "status": "discovered", "registration_status": "not_registered", "init_status": "not_attempted", "routes": 0,
                        "background_enabled": background, "lifecycle_status": "no_router", "conflicts": []}
                results.append(info)
                if module_name in discovered:
                    info["status"] = "duplicate_discovery"
                    continue
                discovered.add(module_name)
                self.loaded_plugins[module_name] = info
                try:
                    module = importlib.import_module(module_name)
                    router = getattr(module, "router", None)
                    if isinstance(router, APIRouter):
                        mounted = router
                        if not background:
                            mounted = copy.copy(router)
                            mounted.lifespan_context = _held_lifespan
                            mounted.on_startup = []
                            mounted.on_shutdown = []
                        existing = {}
                        existing_audit = collect_route_metadata(app.routes)
                        info["conflicts_truncated"] = existing_audit["truncated"]
                        for row in existing_audit["routes"]:
                            for method in row["methods"] or [row["kind"]]:
                                existing.setdefault((row["path"], method), []).append(row["index"])
                        for row in collect_route_metadata(router.routes)["routes"]:
                            for method in row["methods"] or [row["kind"]]:
                                key = (row["path"], method)
                                if key in existing:
                                    info["conflicts"].append({"path": key[0], "method": method, "existing_indices": existing[key]})
                        previous_lifespan = app.router.lifespan_context
                        app.include_router(mounted)
                        default_lifespan_type = type(APIRouter().lifespan_context)
                        if not background:
                            info["lifecycle_status"] = "held_policy"
                        elif isinstance(router.lifespan_context, default_lifespan_type):
                            info["lifecycle_status"] = "framework_default"
                        elif app.router.lifespan_context is previous_lifespan:
                            info["lifecycle_status"] = "unavailable_framework"
                        else:
                            info["lifecycle_status"] = "integrated"
                        info.update(status="registered", registration_status="registered", routes=len(router.routes))
                    else:
                        info["status"] = "no_router"
                        info["registration_status"] = "no_router"
                    init_fn = getattr(module, "init_module", None)
                    if not callable(init_fn):
                        info["init_status"] = "not_present"
                    if callable(init_fn):
                        if not background:
                            info["init_status"] = "skipped_policy"
                        elif inspect.iscoroutinefunction(init_fn):
                            info["init_status"] = "deferred_async"
                        else:
                            info["init_status"] = "running"
                            outcome = init_fn(app)
                            if inspect.isawaitable(outcome):
                                if inspect.iscoroutine(outcome):
                                    outcome.close()
                                info["init_status"] = "deferred_async"
                            else:
                                info["init_status"] = "initialized"
                except Exception as exc:
                    info["error_type"] = type(exc).__name__
                    if info["init_status"] == "running":
                        info["init_status"] = "failed"
                    elif info["registration_status"] != "registered":
                        info["registration_status"] = "failed"
                        info["status"] = "failed"
                    logger.warning("[PluginLoader] Plugin %s failed (%s)", module_name, type(exc).__name__)
        return results

    def get_plugin_summary(self) -> Dict[str, Any]:
        return {"total_plugins": len(self.loaded_plugins), "plugins": list(self.loaded_plugins.values())}

plugin_registry = PluginRegistry()
