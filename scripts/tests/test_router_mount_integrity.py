"""Offline request-level trace and verification fixture for router mount integrity.

Verifies:
1. Bioinformatics router unresolved stub is safely caught in AST without crash.
2. Zero duplicate unconditional include_router calls in backend/AI_BS_Backend.py.
3. Intentional prefix-aliased routers (unreal_bridge_new_router, data_feed_router) remain intact.
4. Single router mounts yield zero Duplicate Operation ID warnings during OpenAPI generation (except known internal recdebut GET/POST unsubscribe pair).
5. Double mounts reproduce Duplicate Operation ID warnings.
6. Offline synthetic HTTP requests successfully route to endpoints across candidate routers.
"""

import ast
import os
from pathlib import Path
import sys
import unittest
import warnings

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from security.recdebut_access import require_recdebut_access


class BioinformaticsStubTraceTests(unittest.TestCase):
    """Trace and verify safety of the unresolved bioinformatics_router stub."""

    def test_bioinformatics_router_is_safely_stubbed_in_backend_ast(self):
        backend_path = ROOT / "backend" / "AI_BS_Backend.py"
        tree = ast.parse(backend_path.read_text(encoding="utf-8"))

        found_stub = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                has_bio = any(
                    isinstance(stmt, ast.ImportFrom)
                    and stmt.module == "routers.bioinformatics_router"
                    for stmt in node.body
                )
                if has_bio:
                    found_stub = True
                    # Verify it catches ImportError
                    handler_types = [
                        getattr(h.type, "id", None)
                        for h in node.handlers
                        if h.type is not None
                    ]
                    self.assertIn(
                        "ImportError",
                        handler_types,
                        "Expected bioinformatics_router try block to handle ImportError",
                    )
                    break

        self.assertTrue(found_stub, "Could not locate bioinformatics_router try-except stub in AI_BS_Backend.py")

    def test_missing_bioinformatics_router_file_does_not_crash(self):
        router_path = ROOT / "backend" / "routers" / "bioinformatics_router.py"
        self.assertFalse(router_path.exists(), "bioinformatics_router.py was unexpectedly found on disk")

        # Test that executing the exact stub block safely passes
        stub_code = """
try:
    from routers.bioinformatics_router import router as bioinformatics_router
    app.include_router(bioinformatics_router)
except ImportError:
    pass
"""
        env = {"app": FastAPI()}
        try:
            exec(stub_code, env)
        except Exception as e:
            self.fail(f"Stub block raised unexpected exception: {e}")


class RouterMountASTIntegrityTests(unittest.TestCase):
    """Verify backend/AI_BS_Backend.py router mounts via AST parsing."""

    def setUp(self):
        backend_path = ROOT / "backend" / "AI_BS_Backend.py"
        self.tree = ast.parse(backend_path.read_text(encoding="utf-8"))
        self.includes = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "include_router":
                router_name = ast.unparse(node.args[0]) if node.args else "UNKNOWN"
                prefix = None
                for kw in node.keywords:
                    if kw.arg == "prefix":
                        prefix = ast.unparse(kw.value).strip("'\"")
                self.includes.append((node.lineno, router_name, prefix))

    def test_no_duplicate_identical_include_router_calls(self):
        """Ensure no router (excluding known mutually exclusive audio fallback) is included twice with identical prefix/arguments."""
        # Filter out audio_catalog_router which is verified in test_audio_router_trace.py to be in a try/except fallback
        signatures = [(name, prefix) for _, name, prefix in self.includes if name != "audio_catalog_router"]
        from collections import Counter
        counts = Counter(signatures)
        duplicates = {k: v for k, v in counts.items() if v > 1}
        self.assertEqual(
            duplicates,
            {},
            f"Found duplicate identical include_router calls: {duplicates}",
        )

    def test_prefix_aliased_routers_preserve_dual_mounts(self):
        """unreal_bridge_new_router and data_feed_router intentionally mount with and without prefix."""
        unreal_mounts = [p for _, name, p in self.includes if name == "unreal_bridge_new_router"]
        self.assertEqual(len(unreal_mounts), 2, "Expected exactly 2 mounts for unreal_bridge_new_router")
        self.assertIn(None, unreal_mounts, "Expected unprefixed mount for unreal_bridge_new_router")
        self.assertIn("/api", unreal_mounts, "Expected /api prefixed mount for unreal_bridge_new_router")

        feed_mounts = [p for _, name, p in self.includes if name == "data_feed_router"]
        self.assertEqual(len(feed_mounts), 2, "Expected exactly 2 mounts for data_feed_router")
        self.assertIn(None, feed_mounts, "Expected unprefixed mount for data_feed_router")
        self.assertIn("/api", feed_mounts, "Expected /api prefixed mount for data_feed_router")

    def test_candidate_routers_have_exact_single_mount(self):
        """gateway_router, updater_router, chef_orders_router, syndication_router, rec_debut_router must appear exactly once."""
        candidates = [
            "gateway_router",
            "updater_router",
            "chef_orders_router",
            "syndication_router",
            "rec_debut_router",
        ]
        for c in candidates:
            matching = [line for line, name, _ in self.includes if name == c]
            self.assertEqual(
                len(matching),
                1,
                f"Expected exactly 1 mount for {c}, found {len(matching)} at lines {matching}",
            )


class RouterOpenAPIDuplicateTests(unittest.TestCase):
    """Verify that single mount produces 0 warnings and double mount reproduces warnings."""

    def test_individual_routers_produce_zero_duplicate_operation_id_warnings_on_single_mount(self):
        from commercial_gateway.gateway_router import gateway_router
        from routers.updater_router import router as updater_router
        from routers.chef_orders_router import router as chef_orders_router
        from modules.syndication_router import router as syndication_router

        for name, r in [
            ("gateway_router", gateway_router),
            ("updater_router", updater_router),
            ("chef_orders_router", chef_orders_router),
            ("syndication_router", syndication_router),
        ]:
            app = FastAPI()
            app.include_router(r)

            with warnings.catch_warnings(record=True) as recorded:
                warnings.simplefilter("always")
                _ = app.openapi()
                dup_warnings = [
                    w for w in recorded
                    if "Duplicate Operation ID" in str(w.message)
                ]
                self.assertEqual(
                    len(dup_warnings),
                    0,
                    f"Expected 0 duplicate operation ID warnings for {name} on single mount, got {len(dup_warnings)}",
                )

    def test_double_mount_reproduces_duplicate_warnings(self):
        from routers.updater_router import router as updater_router
        from routers.rec_debut_router import router as rec_debut_router

        # Test updater_router double mount
        app = FastAPI()
        app.include_router(updater_router)
        app.include_router(updater_router)

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            _ = app.openapi()
            dup_warnings = [
                w for w in recorded
                if "Duplicate Operation ID" in str(w.message)
            ]
            self.assertEqual(
                len(dup_warnings),
                6,
                f"Expected exactly 6 duplicate operation ID warnings on updater_router double mount, got {len(dup_warnings)}",
            )

        # Test rec_debut_router double mount jumps from 1 (internal unsubscribe) to 81
        app2 = FastAPI()
        app2.include_router(rec_debut_router)
        app2.include_router(rec_debut_router)

        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            _ = app2.openapi()
            dup_warnings = [
                w for w in recorded
                if "Duplicate Operation ID" in str(w.message)
            ]
            self.assertEqual(
                len(dup_warnings),
                81,
                f"Expected 81 duplicate operation ID warnings on rec_debut_router double mount, got {len(dup_warnings)}",
            )


class RouterOfflineRequestTests(unittest.TestCase):
    """Execute synthetic offline requests against candidate endpoints."""

    @classmethod
    def setUpClass(cls):
        from commercial_gateway.gateway_router import gateway_router
        from routers.updater_router import router as updater_router
        from routers.chef_orders_router import router as chef_orders_router
        from modules.syndication_router import router as syndication_router
        from routers.rec_debut_router import router as rec_debut_router

        cls.app = FastAPI()
        cls.app.include_router(gateway_router)
        cls.app.include_router(updater_router)
        cls.app.include_router(chef_orders_router)
        cls.app.include_router(syndication_router)
        cls.app.include_router(rec_debut_router)
        cls.client = TestClient(cls.app)

    def test_gateway_router_health_endpoint(self):
        resp = self.client.get("/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)

    def test_updater_router_status_endpoint(self):
        resp = self.client.get("/api/v1/updater/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)

    def test_chef_orders_router_orders_endpoint(self):
        resp = self.client.get("/api/v1/chef/orders")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(isinstance(data, (dict, list)))

    def test_syndication_router_nodes_endpoint(self):
        resp = self.client.get("/api/syndication/nodes")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(isinstance(data, (dict, list)))

    def test_rec_debut_router_unauthorized_yields_403(self):
        resp = self.client.get("/api/v1/recdebut/stats")
        self.assertEqual(resp.status_code, 403)

    def test_rec_debut_router_authorized_yields_200(self):
        self.app.dependency_overrides[require_recdebut_access] = lambda: None
        try:
            resp = self.client.get("/api/v1/recdebut/stats")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("total", data)
            self.assertTrue(data.get("success", False))
        finally:
            self.app.dependency_overrides.pop(require_recdebut_access, None)


if __name__ == "__main__":
    unittest.main()
