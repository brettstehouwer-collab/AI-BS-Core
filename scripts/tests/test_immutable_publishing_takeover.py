"""Synthetic publishing storage contracts; never load or read the real vault."""
import ast
import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import multiprocessing
from pathlib import Path
import re
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def load_engine(directory):
    """Load actual storage code with the actual pure comparator, no app imports."""
    source = ROOT / "backend/core/subagent_coordinator.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    comparator = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                      and node.name == "verify_immutable_transcription")
    namespace = {"re": re, "Dict": dict, "Any": object}
    exec(compile(ast.Module(body=[comparator], type_ignores=[]), str(source), "exec"), namespace)
    core = types.ModuleType("core")
    core.__path__ = []
    coordinator = types.ModuleType("core.subagent_coordinator")
    coordinator.verify_immutable_transcription = namespace["verify_immutable_transcription"]
    spec = importlib.util.spec_from_file_location(
        "publishing_synthetic_fixture", ROOT / "backend/core/immutable_publishing_engine.py")
    module = importlib.util.module_from_spec(spec)
    # Old source creates its real vault at import. Intercept that call so RED is safe.
    with patch.dict(sys.modules, {"core": core, "core.subagent_coordinator": coordinator}), \
            patch.object(Path, "mkdir") as mkdir:
        spec.loader.exec_module(module)
    module.MANUSCRIPTS_DIR = Path(directory)
    module.INDEX_FILE = Path(directory) / "chapters_index.json"
    return module, mkdir.call_count


def process_save(directory, chapter_id, result):
    module, _ = load_engine(directory)
    try:
        module.ImmutablePublishingEngine.save_verified_chapter(chapter_id, "Fixture", "hello world", "Hello, world!")
        result.put("saved")
    except Exception as error:
        result.put(type(error).__name__)


class PublishingStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aibs-publishing-synthetic-")
        self.addCleanup(self.temporary.cleanup)
        self.vault = Path(self.temporary.name) / "vault"
        self.module, self.import_mkdir_calls = load_engine(self.vault)
        self.engine = self.module.ImmutablePublishingEngine

    def save(self, chapter_id="ch01", raw="hello world", formatted="Hello, world!"):
        self.vault.mkdir(exist_ok=True)
        return self.engine.save_verified_chapter(chapter_id, "Fixture", raw, formatted)

    def snapshot(self):
        return {str(p.relative_to(self.vault)): p.read_bytes()
                for p in self.vault.rglob("*") if p.is_file()} if self.vault.exists() else {}

    def test_import_and_empty_listing_create_no_directory(self):
        self.assertEqual(self.import_mkdir_calls, 0)
        self.assertEqual(self.engine.list_chapters(), [])
        self.assertFalse(self.vault.exists())

    def test_lexical_rejection_precedes_storage(self):
        with self.assertRaises(self.module.LexicalIntegrityError):
            self.engine.save_verified_chapter("ch01", "Fixture", "hello world", "different words")
        self.assertFalse(self.vault.exists())

    def test_windows_device_identifiers_rejected_before_storage(self):
        for identifier in ('CON', 'nul', 'Com1', 'lpt9'):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                self.engine.save_verified_chapter(identifier, 'Fixture', 'hello', 'Hello.')
        self.assertFalse(self.vault.exists())

    def test_aggregate_index_limit_preserves_existing_commit_and_artifacts(self):
        self.save('first')
        before = self.snapshot()
        # Reduce only the test fixture limit, including multibyte UTF-8 titles.
        with patch.object(self.module, '_MAX_INDEX_BYTES', len(self.module.INDEX_FILE.read_bytes()) + 400):
            with self.assertRaises(self.module.PublishingStorageError):
                self.engine.save_verified_chapter('second', '\u00e9' * 300, 'hello', 'Hello.')
            self.assertEqual(len(self.engine.list_chapters()), 1)
        self.assertEqual(before, self.snapshot())

    def test_oversized_first_index_publishes_no_manuscript_or_index(self):
        with patch.object(self.module, '_MAX_INDEX_BYTES', 300):
            with self.assertRaises(self.module.PublishingStorageError):
                self.save()
        self.assertFalse(self.module.INDEX_FILE.exists())
        self.assertEqual(list(self.vault.glob('*.md')), [])
        self.assertEqual(list(self.vault.glob('*.raw.txt')), [])

    def test_actual_http_handlers_map_commit_conflict_validation_and_storage(self):
        from fastapi import FastAPI, APIRouter, HTTPException
        from fastapi.testclient import TestClient
        from pydantic import BaseModel, Field
        from typing import Optional
        source = ROOT / 'backend/routers/agent_crew_router.py'
        selected = [node for node in ast.parse(source.read_text(encoding='utf-8-sig')).body
                    if getattr(node, 'name', '') in ('SealChapterRequest',
                        'list_sealed_chapters_endpoint', 'seal_immutable_chapter_endpoint')]
        router = APIRouter()
        namespace = dict(router=router, BaseModel=BaseModel, Field=Field,
                         Optional=Optional, HTTPException=HTTPException, asyncio=asyncio)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
        core = types.ModuleType('core')
        core.__path__ = []
        app = FastAPI()
        app.include_router(router)
        # Isolated HTTP integration: owning handlers/models, synthetic vault;
        # production auth middleware and the rest of the app are not loaded.
        with patch.dict(sys.modules, {'core': core, 'core.immutable_publishing_engine': self.module}), TestClient(app) as client:
            url = '/immutable-scribe/seal'
            payload = dict(chapter_id='http-fixture', title='Fixture', raw_text='hello world',
                           formatted_text='Hello, world!')
            self.assertEqual(client.post(url, json={}).status_code, 422)
            self.assertEqual(client.post(url, json={**payload, 'formatted_text': 'other words'}).status_code, 422)
            self.assertEqual(client.post(url, json={**payload, 'chapter_id': 'con'}).status_code, 422)
            saved = client.post(url, json=payload)
            self.assertEqual(saved.status_code, 200)
            self.assertEqual(client.post(url, json=payload).json()['idempotent'], True)
            self.assertEqual(client.post(url, json={**payload, 'title': 'Changed'}).status_code, 409)
            self.assertEqual(client.get('/immutable-scribe/chapters').json()['count'], 1)
            Path(saved.json()['record']['raw_file']).write_text('synthetic tamper')
            unavailable = client.post(url, json=payload)
            self.assertEqual(unavailable.status_code, 503)
            self.assertNotIn(str(self.vault), unavailable.text)
            self.module.INDEX_FILE.write_text('{synthetic corrupt index')
            self.assertEqual(client.get('/immutable-scribe/chapters').status_code, 503)

    def test_actual_publishing_handlers_keep_event_loop_responsive(self):
        from fastapi import HTTPException
        source = ROOT / 'backend/routers/agent_crew_router.py'
        selected = [node for node in ast.parse(source.read_text(encoding='utf-8-sig')).body
                    if getattr(node, 'name', '') in ('list_sealed_chapters_endpoint', 'seal_immutable_chapter_endpoint')]
        for node in selected:
            node.decorator_list = []
        namespace = dict(HTTPException=HTTPException, SealChapterRequest=object, asyncio=asyncio)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
        core = types.ModuleType('core')
        core.__path__ = []
        def slow_listing():
            time.sleep(.12)
            return []
        def slow_save(**kwargs):
            time.sleep(.12)
            return {'status': 'synthetic'}
        async def scenario():
            request = types.SimpleNamespace(chapter_id='fixture', title='Fixture', raw_text='hello',
                                            formatted_text='Hello.', author='Fixture')
            for operation in (namespace['list_sealed_chapters_endpoint'](),
                              namespace['seal_immutable_chapter_endpoint'](request)):
                task = asyncio.create_task(operation)
                start = time.monotonic()
                await asyncio.sleep(.02)
                self.assertLess(time.monotonic() - start, .09)
                await task
        with patch.dict(sys.modules, {'core': core, 'core.immutable_publishing_engine': self.module}), \
                patch.object(self.engine, 'list_chapters', side_effect=slow_listing), \
                patch.object(self.engine, 'save_verified_chapter', side_effect=slow_save):
            asyncio.run(scenario())

    def test_exact_retry_is_idempotent_and_keeps_compatibility_fields(self):
        first = self.save()
        before = self.snapshot()
        retry = self.save()
        self.assertEqual(retry["record"], first["record"])
        self.assertEqual(before, self.snapshot())
        self.assertEqual(len(self.engine.list_chapters()), 1)
        self.assertEqual(Path(first["record"]["raw_file"]).read_text(), "hello world")
        for key in ("chapter_id", "title", "author", "word_count", "verified_utc", "formatted_file", "raw_file", "status", "raw_sha256", "formatted_sha256"):
            self.assertIn(key, first["record"])

    def test_changed_same_id_rejected_without_overwriting(self):
        self.save()
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            self.save(raw="new words", formatted="New words.")
        self.assertEqual(before, self.snapshot())

    def test_distinct_ids_cannot_collide_after_normalization(self):
        self.save("Ch 01")
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            self.save("ch_01")
        self.assertEqual(before, self.snapshot())

    def test_corrupt_or_wrong_shape_index_is_not_empty_success(self):
        self.vault.mkdir()
        for invalid in (b"{partial", b"{}", b"[17]", b'[{"chapter_id":"only-id"}]'):
            self.module.INDEX_FILE.write_bytes(invalid)
            before = self.snapshot()
            with self.assertRaises(RuntimeError):
                self.engine.list_chapters()
            with self.assertRaises(RuntimeError):
                self.save()
            self.assertEqual(before, self.snapshot())

    def test_commit_failure_keeps_old_index_and_orphans_are_retryable(self):
        self.save("first")
        prior = self.module.INDEX_FILE.read_bytes()
        with patch.object(self.engine, "_write_index", side_effect=OSError("synthetic index failure")):
            with self.assertRaises((OSError, RuntimeError)):
                self.save("second")
        self.assertEqual(self.module.INDEX_FILE.read_bytes(), prior)
        before_retry = {p.name: p.read_bytes() for p in self.vault.glob("*.md")}
        self.save("second")
        self.assertEqual(len(self.engine.list_chapters()), 2)
        self.assertEqual(before_retry, {p.name: p.read_bytes() for p in self.vault.glob("*.md")})

    def test_file_tampering_rejected_on_exact_retry(self):
        record = self.save()["record"]
        Path(record["raw_file"]).write_text("synthetic changed bytes")
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            self.save()
        self.assertEqual(before, self.snapshot())

    def test_legacy_records_are_listed_but_never_silently_resealed(self):
        self.vault.mkdir()
        raw = self.vault / "legacy.raw.txt"
        formatted = self.vault / "legacy.md"
        raw.write_text("legacy source")
        formatted.write_text("Legacy source.")
        record = dict(chapter_id="legacy", title="Legacy", author="Fixture", word_count=2,
                      verified_utc="2026-01-01T00:00:00Z", raw_file=str(raw),
                      formatted_file=str(formatted), status="SEALED_IMMUTABLE")
        self.module.INDEX_FILE.write_text(json.dumps([record]))
        self.assertEqual(self.engine.list_chapters(), [record])
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            self.save("legacy", "legacy source", "Legacy source.")
        self.assertEqual(before, self.snapshot())

    def test_missing_index_does_not_adopt_existing_legacy_files(self):
        self.vault.mkdir()
        (self.vault / "old.raw.txt").write_text("preserve original")
        before = self.snapshot()
        with self.assertRaises(RuntimeError):
            self.save()
        self.assertEqual(before, self.snapshot())

    def test_concurrent_exact_thread_retries_publish_one_record(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            rows = list(pool.map(lambda _: self.save()["record"], range(12)))
        self.assertTrue(all(row == rows[0] for row in rows))
        self.assertEqual(len(self.engine.list_chapters()), 1)

    def test_separate_processes_preserve_both_chapters(self):
        context = multiprocessing.get_context("spawn")
        results = context.Queue()
        processes = [context.Process(target=process_save, args=(str(self.vault), name, results))
                     for name in ("one", "two")]
        try:
            for process in processes:
                process.start()
            for process in processes:
                process.join(20)
                self.assertFalse(process.is_alive(), "synthetic writer exceeded bound")
                self.assertEqual(process.exitcode, 0)
            self.assertEqual([results.get(timeout=3), results.get(timeout=3)], ["saved", "saved"])
            self.assertEqual({row["chapter_id"] for row in self.engine.list_chapters()}, {"one", "two"})
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(3)
            results.close()
            results.join_thread()


if __name__ == "__main__":
    unittest.main()
