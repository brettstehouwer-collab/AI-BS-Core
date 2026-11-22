"""Offline source inventory must never import or execute an application."""
import json
from pathlib import Path
import tempfile
import unittest


class RouteInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def scan(self, source):
        from workspace.reviews.security_route_inventory import inspect_source
        path = self.root/'fixture.py'
        path.write_text(source, encoding='utf-8')
        return inspect_source(path, self.root)

    def test_inventory_never_executes_source_or_exports_arbitrary_literals(self):
        result = self.scan('raise RuntimeError("DO_NOT_EXECUTE")\n'
                           'secret = "INERT_PRIVATE_CANARY"\n'
                           '@app.post("/api/action")\n'
                           'def action():\n    subprocess.run(secret)\n')
        encoded = json.dumps(result)
        self.assertNotIn('INERT_PRIVATE_CANARY', encoded)
        self.assertNotIn('DO_NOT_EXECUTE', encoded)
        self.assertEqual(result['routes'][0]['methods'], ['POST'])
        self.assertEqual(result['candidate_sinks'][0]['call'], 'subprocess.run')

    def test_duplicate_handlers_and_conditional_mounts_stay_unresolved(self):
        result = self.scan('router = APIRouter(prefix="/worker")\n'
                           '@router.post("/run", dependencies=[Depends(require_owner)])\n'
                           'def one(): pass\n'
                           '@router.post("/run")\n'
                           'def two(): pass\n'
                           'if enabled:\n    app.include_router(router, prefix="/api")\n')
        self.assertEqual([r['source_path'] for r in result['routes']], ['/worker/run']*2)
        self.assertEqual(result['routes'][0]['dependency_symbols'], ['require_owner'])
        self.assertEqual(result['duplicate_source_groups'], [['one', 'two']])
        self.assertEqual(result['mounts'][0]['context'], ['if'])
        self.assertFalse(result['runtime_registration_verified'])

    def test_dynamic_routes_and_parse_errors_do_not_become_a_clean_inventory(self):
        result = self.scan('@app.api_route(dynamic_path, methods=method_names)\ndef action(): pass\n')
        self.assertEqual(result['routes'][0]['source_path'], None)
        self.assertTrue(result['routes'][0]['unresolved'])
        broken = self.scan('def invalid(:\n')
        self.assertEqual(broken['parse_status'], 'error')
        self.assertEqual(broken['error_type'], 'SyntaxError')

    def test_outside_root_is_rejected_before_reading(self):
        from workspace.reviews.security_route_inventory import inspect_source
        with self.assertRaises(ValueError):
            inspect_source(self.root.parent/'outside.py', self.root)


if __name__ == '__main__':
    unittest.main()
