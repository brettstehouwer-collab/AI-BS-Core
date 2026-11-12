"""Offline request-level trace and verification fixture for audio_catalog_router candidate.

Exercises both primary (aibs_audio_router) and fallback (audio_catalog_router)
routers using synthetic SQLite stores and isolated temporary audio files.
Does not import the monolithic AI_BS_Backend or start any daemons/listeners.
"""

import ast
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))


class AudioRouterRegistrationTraceTests(unittest.TestCase):
    """Trace source AST registration and verify mutual exclusivity of mounts."""

    def test_audio_catalog_router_mounts_are_mutually_exclusive_in_ast(self):
        backend_path = ROOT / "backend" / "AI_BS_Backend.py"
        tree = ast.parse(backend_path.read_text(encoding="utf-8"))

        # Find the try-except block containing audio_catalog_router
        found_try = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                body_has_audio = any(
                    isinstance(stmt, ast.ImportFrom)
                    and stmt.module == "aibs_audio_router"
                    for stmt in node.body
                )
                if body_has_audio:
                    found_try = True
                    # Primary branch: include_router called in try body
                    primary_includes = [
                        stmt for stmt in node.body
                        if isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Call)
                        and getattr(stmt.value.func, "attr", None) == "include_router"
                    ]
                    self.assertEqual(len(primary_includes), 1, "Expected exactly 1 include_router in primary branch")

                    # Fallback branch: must be inside except ImportError handler
                    import_handlers = [h for h in node.handlers if getattr(h.type, "id", None) == "ImportError"]
                    self.assertEqual(len(import_handlers), 1, "Expected exactly 1 ImportError handler for fallback")
                    fallback_handler = import_handlers[0]

                    # Check inner try or import in handler
                    inner_nodes = list(ast.walk(fallback_handler))
                    fallback_imports = [
                        n for n in inner_nodes
                        if isinstance(n, ast.ImportFrom) and n.module == "audio_catalog_router"
                    ]
                    self.assertTrue(len(fallback_imports) >= 1, "Expected fallback import from audio_catalog_router")

                    fallback_includes = [
                        n for n in inner_nodes
                        if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "include_router"
                    ]
                    self.assertEqual(len(fallback_includes), 1, "Expected exactly 1 fallback include_router")
                    break

        self.assertTrue(found_try, "Could not locate audio_catalog_router try-except block in backend/AI_BS_Backend.py")

    def test_primary_and_fallback_routers_have_no_duplicate_routes(self):
        import aibs_audio_router
        import audio_catalog_router

        # Primary routes
        primary_paths = [r.path for r in aibs_audio_router.router.routes]
        self.assertEqual(len(primary_paths), len(set(primary_paths)), "Primary router contains duplicate routes")
        self.assertIn("/api/audio/stats", primary_paths)
        self.assertIn("/api/audio/search", primary_paths)
        self.assertIn("/api/audio/stream/{asset_id}", primary_paths)
        self.assertIn("/api/audio/stream", primary_paths)
        self.assertIn("/api/audio/sonify/query", primary_paths)

        # Fallback routes
        fallback_paths = [r.path for r in audio_catalog_router.router.routes]
        self.assertEqual(len(fallback_paths), len(set(fallback_paths)), "Fallback router contains duplicate routes")
        self.assertIn("/api/audio/stats", fallback_paths)
        self.assertIn("/api/audio/search", fallback_paths)
        self.assertIn("/api/audio/stream", fallback_paths)


class AudioRouterOfflineRequestTests(unittest.TestCase):
    """Execute synthetic offline requests against the audio endpoints."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_path = Path(self.temp_dir.name)

        # Create synthetic audio file
        self.audio_file = self.temp_path / "synthetic_test.wav"
        self.audio_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 32
        self.audio_file.write_bytes(self.audio_content)

        # Create synthetic SQLite database with both schemas
        self.db_path = self.temp_path / "synthetic_audio_catalog.db"
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        # Schema for aibs_audio_router (FTS5 corpus)
        cur.execute("""
            CREATE VIRTUAL TABLE audio_corpus_fts USING fts5(
                asset_id, file_path, sample_rate, duration_ms, category, bpm,
                musical_key, timbral_spectrum, semantic_context, data_bindings
            );
        """)
        cur.execute("""
            INSERT INTO audio_corpus_fts (
                asset_id, file_path, sample_rate, duration_ms, category, bpm,
                musical_key, timbral_spectrum, semantic_context, data_bindings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "syn_asset_001", str(self.audio_file), 44100, 1500, "stinger", "120",
            "Cmin", "sharp", "tension", "high_variance"
        ))

        # Schema for audio_catalog_router (audio_assets table)
        cur.execute("""
            CREATE TABLE audio_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                extension TEXT,
                path TEXT,
                rel_path TEXT,
                size_bytes INTEGER,
                bpm INTEGER,
                musical_key TEXT,
                category TEXT,
                modified_ts REAL
            );
        """)
        cur.execute("""
            INSERT INTO audio_assets (
                filename, extension, path, rel_path, size_bytes, bpm,
                musical_key, category, modified_ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "synthetic_test.wav", ".wav", str(self.audio_file), "synthetic_test.wav",
            len(self.audio_content), 120, "Cmin", "stinger", 1700000000.0
        ))
        conn.commit()
        conn.close()

        # Monkeypatch DB paths to point to synthetic store
        import aibs_audio_router
        import audio_catalog_router

        self._orig_resolve = aibs_audio_router.resolve_db_path
        self._orig_db_paths = list(aibs_audio_router.DB_PATHS)
        self._orig_catalog_db = audio_catalog_router.DB_PATH

        aibs_audio_router.resolve_db_path = lambda: str(self.db_path)
        aibs_audio_router.DB_PATHS = [str(self.db_path)]
        audio_catalog_router.DB_PATH = str(self.db_path)

        # Primary test app
        self.primary_app = FastAPI()
        self.primary_app.include_router(aibs_audio_router.router)
        self.primary_client = TestClient(self.primary_app)

        # Fallback test app
        self.fallback_app = FastAPI()
        self.fallback_app.include_router(audio_catalog_router.router)
        self.fallback_client = TestClient(self.fallback_app)

    def tearDown(self):
        import aibs_audio_router
        import audio_catalog_router
        import gc

        if hasattr(self, "primary_client"):
            self.primary_client.close()
        if hasattr(self, "fallback_client"):
            self.fallback_client.close()

        aibs_audio_router.resolve_db_path = self._orig_resolve
        aibs_audio_router.DB_PATHS = self._orig_db_paths
        audio_catalog_router.DB_PATH = self._orig_catalog_db
        gc.collect()

    def test_primary_stats_endpoint(self):
        resp = self.primary_client.get("/api/audio/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "online")
        self.assertEqual(data.get("total_indexed_assets"), 1)
        self.assertIn("stinger", data.get("categories", {}))

    def test_primary_search_endpoint(self):
        resp = self.primary_client.get("/api/audio/search", params={"category": "stinger"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("count"), 1)
        self.assertEqual(data["results"][0]["asset_id"], "syn_asset_001")
        self.assertEqual(data["results"][0]["bpm"], "120")

    def test_primary_stream_by_asset_id_full_and_partial_range(self):
        # Full content
        resp = self.primary_client.get("/api/audio/stream/syn_asset_001")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, self.audio_content)
        self.assertEqual(resp.headers.get("content-type"), "audio/wav")

        # Range request (HTTP 206)
        range_resp = self.primary_client.get(
            "/api/audio/stream/syn_asset_001",
            headers={"Range": "bytes=0-3"}
        )
        self.assertEqual(range_resp.status_code, 206)
        self.assertEqual(range_resp.content, b"RIFF")
        self.assertEqual(
            range_resp.headers.get("content-range"),
            f"bytes 0-3/{len(self.audio_content)}"
        )

        # Nonexistent asset ID
        missing_resp = self.primary_client.get("/api/audio/stream/nonexistent_id")
        self.assertEqual(missing_resp.status_code, 404)

    def test_primary_stream_by_path_full_and_partial_range(self):
        resp = self.primary_client.get(
            "/api/audio/stream",
            params={"path": str(self.audio_file)}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, self.audio_content)

        range_resp = self.primary_client.get(
            "/api/audio/stream",
            params={"path": str(self.audio_file)},
            headers={"Range": "bytes=0-3"}
        )
        self.assertEqual(range_resp.status_code, 206)
        self.assertEqual(range_resp.content, b"RIFF")

        # Missing path
        missing_resp = self.primary_client.get(
            "/api/audio/stream",
            params={"path": str(self.temp_path / "missing.wav")}
        )
        self.assertEqual(missing_resp.status_code, 404)

    def test_primary_sonification_query(self):
        resp = self.primary_client.get(
            "/api/audio/sonify/query",
            params={"event_type": "variance_breach", "variance": 15.5, "valence": "tension"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("event_type"), "variance_breach")
        self.assertEqual(data.get("valence"), "tension")
        self.assertIn("transient_stingers", data)

    def test_fallback_stats_and_search(self):
        stats_resp = self.fallback_client.get("/api/audio/stats")
        self.assertEqual(stats_resp.status_code, 200)
        stats_data = stats_resp.json()
        self.assertEqual(stats_data.get("total_assets"), 1)

        search_resp = self.fallback_client.get("/api/audio/search", params={"category": "stinger"})
        self.assertEqual(search_resp.status_code, 200)
        search_data = search_resp.json()
        self.assertEqual(search_data.get("total"), 1)
        self.assertEqual(search_data["items"][0]["filename"], "synthetic_test.wav")

    def test_fallback_stream_by_path(self):
        resp = self.fallback_client.get(
            "/api/audio/stream",
            params={"path": str(self.audio_file)}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, self.audio_content)

        missing_resp = self.fallback_client.get(
            "/api/audio/stream",
            params={"path": str(self.temp_path / "missing.wav")}
        )
        self.assertEqual(missing_resp.status_code, 404)

    def test_audio_endpoints_security_boundary_and_identity_neutrality(self):
        """Verify endpoints are read-only media utilities accessible with or without admin headers."""
        # Unauthenticated request
        anon_resp = self.primary_client.get("/api/audio/stats")
        self.assertEqual(anon_resp.status_code, 200)

        # Authenticated with admin key header
        admin_resp = self.primary_client.get(
            "/api/audio/stats",
            headers={"x-admin-key": "synthetic-test-key"}
        )
        self.assertEqual(admin_resp.status_code, 200)
        self.assertEqual(anon_resp.json(), admin_resp.json())

        # Verify /api/audio does not trigger admin execution boundary
        from security.vault_access import is_vault_path
        from security.analytics_access import is_analytics_path
        from security.screenwriting_access import is_screenwriting_path
        from security.recdebut_access import is_recdebut_path
        from security.document_access import is_document_path

        for p in ["/api/audio/stats", "/api/audio/search", "/api/audio/stream", "/api/audio/sonify/query"]:
            self.assertFalse(is_vault_path(p), f"{p} should not be classified as vault path")
            self.assertFalse(is_analytics_path(p), f"{p} should not be classified as analytics path")
            self.assertFalse(is_screenwriting_path(p), f"{p} should not be classified as screenwriting path")
            self.assertFalse(is_recdebut_path(p), f"{p} should not be classified as recdebut path")
            self.assertFalse(is_document_path(p), f"{p} should not be classified as document path")


if __name__ == "__main__":
    unittest.main()
