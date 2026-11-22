"""Synthetic bridge qualification; no live services, processes or databases."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
from tools.bs_chat_tool_bridge import BSChatToolBridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.bridge = BSChatToolBridge(self.root, ('src/example.py',))
        self.token = bind_memory_principal('local_admin')

    def tearDown(self):
        reset_memory_principal(self.token)
        self.directory.cleanup()

    def test_unbound_dispatch_denied(self):
        with patch('tools.bs_chat_tool_bridge.current_memory_principal', return_value=None):
            self.assertEqual(self.bridge.execute_tool('verify_sqlite_wal', {}), {'status': 'denied'})

    def test_direct_method_requires_current_context(self):
        with patch('tools.bs_chat_tool_bridge.current_memory_principal', return_value=None):
            with self.assertRaises(PermissionError):
                self.bridge.verify_sqlite_wal()

    def test_owner_override_rejected(self):
        self.assertEqual(self.bridge.execute_tool('verify_sqlite_wal', {'owner': 'local_admin'})['status'], 'error')

    def test_unknown_tool_and_argument_container(self):
        self.assertEqual(self.bridge.execute_tool('__init__', {})['status'], 'error')
        self.assertEqual(self.bridge.execute_tool('verify_sqlite_wal', [])['status'], 'error')

    def test_smoke_exact_integer_bounds(self):
        for value in (True, 11, 16, '12', 12.0):
            with self.assertRaises(ValueError):
                self.bridge.run_coding_smoke(value)

    def test_smoke_sanitizes_existing_profile(self):
        module = Mock()
        module.run_checks.return_value = [{'passed': i != 0, 'secret': 'hidden'} for i in range(12)]
        with patch.object(self.bridge, '_path', return_value=self.root / 'script.py'), \
                patch('tools.bs_chat_tool_bridge.importlib.util.spec_from_file_location') as spec, \
                patch('tools.bs_chat_tool_bridge.importlib.util.module_from_spec', return_value=module):
            result = self.bridge.run_coding_smoke(12)
        self.assertEqual(result, {'status': 'failed', 'check_count': 12, 'passed_count': 11, 'failed_count': 1})
        spec.return_value.loader.exec_module.assert_called_once_with(module)

    def test_database_both_readonly_without_data(self):
        connection = Mock()
        connection.execute.return_value.fetchone.side_effect = [('wal',), (2,), ('delete',), (1,)]
        with patch.object(self.bridge, '_path', side_effect=lambda p: self.root / p), \
                patch('tools.bs_chat_tool_bridge.sqlite3.connect', return_value=connection) as connect:
            result = self.bridge.verify_sqlite_wal()
        self.assertEqual([o['database'] for o in result['observations']], ['backend_master', 'cdz_audit'])
        self.assertTrue(all(call.args[0].endswith('?mode=ro') and call.kwargs['uri'] for call in connect.call_args_list))
        self.assertEqual([c.args[0] for c in connection.execute.call_args_list],
                         ['PRAGMA journal_mode', 'PRAGMA synchronous'] * 2)

    def test_diff_default_deny(self):
        bridge = BSChatToolBridge(self.root)
        with self.assertRaises(PermissionError):
            bridge.inspect_source_diff('src/example.py')

    def test_dangerous_paths_rejected(self):
        for path in ('../x', '.git/config', 'src/../x', 'C:/x', 'private/x', 'x.db', 'src//x'):
            with self.assertRaises(ValueError):
                BSChatToolBridge(self.root, (path,))

    def test_hardlink_denied(self):
        file = self.root / 'source.py'
        file.write_text('safe')
        import os
        os.link(file, self.root / 'other.py')
        with self.assertRaises(ValueError):
            self.bridge._path('source.py')

    def test_diff_states_without_exposing_content(self):
        file = self.root / 'src' / 'example.py'
        file.parent.mkdir()
        file.write_text('hidden content')
        for tracked, output, expected in ((1, '', 'untracked'), (0, '', 'unmodified'), (0, '1\t0\tx', 'modified')):
            with patch.object(self.bridge, '_git', side_effect=[{'returncode': tracked}, {'returncode': 0, 'stdout': output}]):
                result = self.bridge.inspect_source_diff('src/example.py')
            self.assertEqual(result['file_state'], expected)
            self.assertNotIn('hidden content', str(result))
        file.unlink()
        with patch.object(self.bridge, '_git', side_effect=[{'returncode': 0}, {'returncode': 0, 'stdout': '0\t1\tx'}]):
            self.assertEqual(self.bridge.inspect_source_diff('src/example.py')['file_state'], 'deleted')

    def test_health_named_loopback_stream_only(self):
        response = Mock(status_code=503)
        client = Mock()
        client.stream.return_value.__enter__ = Mock(return_value=response)
        client.stream.return_value.__exit__ = Mock(return_value=False)
        with patch('httpx.Client') as factory:
            factory.return_value.__enter__.return_value = client
            result = self.bridge.check_service_health('backend')
        self.assertEqual(result['status'], 'failed')
        factory.assert_called_once_with(trust_env=False, follow_redirects=False, timeout=2.0)
        client.stream.assert_called_once_with('GET', 'http://127.0.0.1:8080/health')
        with self.assertRaises(ValueError):
            self.bridge.check_service_health('http://example.com')

    def test_discovery_never_scans_other_roots(self):
        with patch.object(self.bridge, '_path', side_effect=ValueError):
            result = self.bridge.discover_databases()
        self.assertEqual(len(result['databases']), 2)
        self.assertTrue(all(d['status'] == 'unavailable' for d in result['databases']))

    def test_schema_named_only_and_bounded(self):
        with self.assertRaises(ValueError):
            self.bridge.inspect_database_schema('E:/arbitrary.db')
        connection = Mock()
        connection.execute.return_value.fetchall.side_effect = [[('table_one',)], [('column_one', 'TEXT')]]
        with patch.object(self.bridge, '_path', return_value=self.root / 'fixture.db'), \
                patch('tools.bs_chat_tool_bridge.sqlite3.connect', return_value=connection):
            result = self.bridge.inspect_database_schema()
        self.assertFalse(result['row_values_exposed'])
        self.assertEqual(result['tables'][0]['columns'], [{'name': 'column_one', 'type': 'TEXT'}])
        self.assertTrue(all('LIMIT' in call.args[0] for call in connection.execute.call_args_list))

    def test_process_status_injected_controller_sanitized(self):
        self.assertEqual(self.bridge.process_batch_status()['status'], 'unavailable')
        bridge = BSChatToolBridge(self.root, batch_status_provider=lambda: {
            'running': 1, 'queued': True, 'command': 'secret', 'failed': -1})
        self.assertEqual(bridge.process_batch_status(), {'status': 'observed', 'counts': {'running': 1}})


if __name__ == '__main__':
    unittest.main()
