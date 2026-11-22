"""Synthetic coding transport contract tests: no production service or model calls."""
import json
import unittest
import httpx
from native_studio.coding_mode_service import CodingModeService, coding_mode_enabled, preparation_payload


class CodingModeServiceTests(unittest.TestCase):
    def test_feature_disabled_by_default(self):
        self.assertFalse(coding_mode_enabled({}))
        self.assertTrue(coding_mode_enabled({'AI_BS_CODING_MODE': '1'}))

    def test_structured_python_and_web_scope(self):
        checks = [{'check_id': 'node', 'profile': 'node_test', 'targets': ['tests/x.mjs']}]
        value = preparation_payload('a'*32, 'ai-bs', 'Fix component',
            {'editable': 'frontend/x.jsx\nbackend/x.py', 'verification': 'tests/x.mjs'}, checks)
        self.assertEqual(len(value['files']), 3)
        self.assertEqual(value['checks'], checks)

    def test_local_authenticated_request_and_no_redirect(self):
        captured = []
        def serve(request):
            captured.append(request)
            return httpx.Response(200, json={'state': 'BLOCKED', 'verification_status': 'not_run'})
        service = CodingModeService(headers_provider=lambda: {'x-admin-key': 'synthetic'}, transport=httpx.MockTransport(serve))
        self.assertEqual(service.request('GET', '/mode/capabilities')['state'], 'BLOCKED')
        self.assertEqual(str(captured[0].url), 'http://127.0.0.1:8080/api/chat/coding-tasks/mode/capabilities')
        self.assertEqual(captured[0].headers['x-admin-key'], 'synthetic')

    def test_failure_does_not_retry(self):
        calls = []
        def serve(request):
            calls.append(request)
            return httpx.Response(409, json={'private': 'not displayed'})
        service = CodingModeService(headers_provider=lambda: {'x-admin-key': 'synthetic'}, transport=httpx.MockTransport(serve))
        with self.assertRaisesRegex(RuntimeError, 'HTTP409'):
            service.request('POST', '/mode/executions', {'execution_id': 'a'*32})
        self.assertEqual(len(calls), 1)

    def test_auth_and_invalid_path_stop_before_transport(self):
        service = CodingModeService(headers_provider=lambda: {})
        with self.assertRaises(RuntimeError): service.request('GET', '/preparations')
        with self.assertRaises(ValueError): service.request('GET', '/../other')

    def test_invalid_scope(self):
        with self.assertRaises(ValueError): preparation_payload('invalid', 'ai-bs', 'fix', {}, [])

    def test_only_bounded_execution_history_query_is_allowed(self):
        captured = []
        def serve(request):
            captured.append(request); return httpx.Response(200, json={'items': []})
        service = CodingModeService(headers_provider=lambda: {'x-admin-key': 'synthetic'}, transport=httpx.MockTransport(serve))
        service.request('GET', '/mode/executions?limit=20&cursor='+'a'*32)
        self.assertEqual(captured[-1].url.params['limit'], '20')
        for path in ['/mode/executions?limit=999', '/mode/executions?limit=20&cursor=bad', '/preparations?redirect=remote']:
            with self.assertRaises(ValueError): service.request('GET', path)


if __name__ == '__main__': unittest.main()
