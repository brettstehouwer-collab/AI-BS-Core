"""Offline coverage inventory: inspect source, never import application code."""
import json
from pathlib import Path
import tempfile
import unittest


class SubsystemInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'backend/routers').mkdir(parents=True)
        (self.root / 'version.txt').write_text('fixture-version')

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def collect(self):
        from workspace.reviews.subsystem_inventory import collect_backend
        return collect_backend(self.root)

    def test_import_alias_mount_candidates_remain_source_only_and_keep_order(self):
        self.write('backend/AI_BS_Backend.py',
                   'from routers.chat import router as chat\n'
                   'if enabled:\n    app.include_router(chat, prefix="/api")\n'
                   'app.include_router(chat, prefix="/api")\n')
        self.write('backend/routers/chat.py',
                   'router = APIRouter(prefix="/chat")\n'
                   '@router.post("/save")\nasync def save(): pass\n')
        report = self.collect()
        mounts = report['mounts']
        self.assertEqual([m['line'] for m in mounts], [3, 4])
        self.assertEqual(mounts[0]['candidate_router_files'], ['backend/routers/chat.py'])
        self.assertEqual(mounts[0]['context'], ['if'])
        self.assertFalse(report['runtime_registration_verified'])
        self.assertEqual(len(report['repeated_mount_candidates']), 1)
        self.assertEqual(report['declared_route_count'], 1)

    def test_local_relative_module_imports_and_unresolved_mounts_are_explicit(self):
        self.write('backend/AI_BS_Backend.py',
                   'from core import engine\napp.include_router(engine.router)\n'
                   'app.include_router(factory())\n')
        self.write('backend/core/engine.py', 'from ..routers import chat\nrouter.include_router(chat.router)\n')
        self.write('backend/routers/chat.py', '@router.get("/x")\ndef x(): pass\n')
        report = self.collect()
        self.assertEqual(report['mounts'][0]['candidate_router_files'], ['backend/core/engine.py'])
        self.assertTrue(any(m['resolution'] == 'unresolved' for m in report['mounts']))
        engine = next(m for m in report['mounts'] if m['file'] == 'backend/core/engine.py')
        self.assertEqual(engine['candidate_router_files'], ['backend/routers/chat.py'])

    def test_no_execution_no_arbitrary_literals_no_private_or_dependency_scan(self):
        self.write('backend/AI_BS_Backend.py',
                   'raise RuntimeError("NO_EXECUTE_CANARY")\nsecret="PRIVATE_CANARY"\n')
        self.write('backend/tests/test_secret.py', 'not valid python')
        self.write('backend/test_secret.py', 'not valid python')
        self.write('backend/.venv/pkg.py', 'not valid python')
        self.write('backend/private/record.json', '{private data}')
        report = self.collect()
        encoded = json.dumps(report)
        self.assertNotIn('PRIVATE_CANARY', encoded)
        self.assertNotIn('NO_EXECUTE_CANARY', encoded)
        self.assertEqual(report['source_file_count'], 1)
        self.assertEqual(len(report['source_pins'][0]['sha256']), 64)

    def test_parse_failures_do_not_become_verified_or_disappear(self):
        self.write('backend/AI_BS_Backend.py', 'def broken(:\n')
        report = self.collect()
        self.assertEqual(report['parse_errors'][0]['file'], 'backend/AI_BS_Backend.py')
        self.assertFalse(report['complete_source_parse'])
        self.assertFalse(report['runtime_registration_verified'])

    def test_file_filters_do_not_hide_non_test_route_sources(self):
        self.write('backend/AI_BS_Backend.py', 'pass\n')
        self.write('backend/routers/latest_routes.py', '@router.get("/latest")\ndef latest(): pass\n')
        self.assertEqual(self.collect()['declared_route_count'], 1)

    def test_package_qualified_backend_router_imports_resolve_to_local_candidates(self):
        self.write('backend/AI_BS_Backend.py',
                   'from backend.routers.chat import router as chat\napp.include_router(chat)\n')
        self.write('backend/routers/chat.py', '@router.get("/x")\ndef x(): pass\n')
        mount = self.collect()['mounts'][0]
        self.assertEqual(mount['candidate_router_files'], ['backend/routers/chat.py'])
        self.assertFalse(mount['runtime_registration_verified'])


if __name__ == '__main__':
    unittest.main()
