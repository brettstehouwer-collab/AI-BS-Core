"""Offline registry integration checks; no live operations or activation."""
import asyncio
import os
import unittest
from unittest.mock import Mock, patch

from core.personal_memory_scope import (bind_memory_principal,
    current_memory_principal, reset_memory_principal)
from tools.bs_chat_tool_bridge import BSChatToolBridge
from tools.tool_registry import ToolRegistry, _BS_CHAT_DIAGNOSTIC_NAMES


class BridgeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {'AI_BS_ENABLE_CHAT_TOOL_BRIDGE': '1'})
        self.environment.start()
        self.bridge = BSChatToolBridge()
        self.binding = patch('tools.bs_chat_tool_bridge.bs_chat_bridge', self.bridge)
        self.binding.start()

    def tearDown(self):
        self.binding.stop()
        self.environment.stop()

    def invoke(self, name='verify_sqlite_wal', arguments=None):
        return ToolRegistry.execute_tool(name, {} if arguments is None else arguments)

    def test_01_default_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            names = {d['name'] for d in ToolRegistry.get_tool_declarations()}
            self.assertTrue(names.isdisjoint(_BS_CHAT_DIAGNOSTIC_NAMES))
            self.assertEqual(self.invoke()['error_code'], 'INVALID_TOOL_CALL')

    def test_02_flag_requires_exact_one(self):
        for value in ('0', 'true', 'yes', ' 1', ''):
            with patch.dict(os.environ, {'AI_BS_ENABLE_CHAT_TOOL_BRIDGE': value}):
                self.assertEqual(self.invoke()['error_code'], 'INVALID_TOOL_CALL')

    def test_03_seven_unique_closed_declarations(self):
        declarations = ToolRegistry.get_tool_declarations()
        selected = [d for d in declarations if d['name'] in _BS_CHAT_DIAGNOSTIC_NAMES]
        self.assertEqual(len(selected), 7)
        self.assertEqual(len({d['name'] for d in selected}), 7)
        self.assertTrue(all(d['parameters']['additionalProperties'] is False for d in selected))

    def test_04_legacy_declarations_unchanged(self):
        enabled = ToolRegistry.get_tool_declarations()
        with patch.dict(os.environ, {'AI_BS_ENABLE_CHAT_TOOL_BRIDGE': '0'}):
            disabled = ToolRegistry.get_tool_declarations()
        self.assertEqual([d for d in enabled if d['name'] not in _BS_CHAT_DIAGNOSTIC_NAMES], disabled)

    def test_05_unknown_name_rejected(self):
        self.assertEqual(self.invoke('bridge_unknown')['error_code'], 'INVALID_TOOL_CALL')

    def test_06_argument_container_and_owner_rejected(self):
        for arguments in ([], {'owner': 'local_admin'}, {'root': 'C:/'}):
            self.assertEqual(self.invoke(arguments=arguments)['error_code'], 'INVALID_TOOL_CALL')

    def test_07_required_and_enum_arguments(self):
        cases = [('inspect_source_diff', {}), ('inspect_database_schema', {}),
                 ('inspect_database_schema', {'database': 'arbitrary'}),
                 ('check_service_health', {'service': 'https://example.invalid'}),
                 ('run_coding_smoke', {'max_checks': True}),
                 ('run_coding_smoke', {'max_checks': 16})]
        for name, arguments in cases:
            self.assertEqual(self.invoke(name, arguments)['error_code'], 'INVALID_TOOL_CALL')

    def test_08_missing_verified_context_denied(self):
        with patch('tools.bs_chat_tool_bridge.current_memory_principal', return_value=None), \
                patch.object(self.bridge, 'verify_sqlite_wal') as operation:
            self.assertEqual(self.invoke(), {'status': 'denied'})
            operation.assert_not_called()

    def test_09_verified_context_dispatches_without_rebinding(self):
        token = bind_memory_principal('local_admin')
        try:
            with patch.object(self.bridge, 'verify_sqlite_wal',
                    side_effect=lambda: {'status': 'observed', 'verified': current_memory_principal() == 'local_admin'}):
                self.assertEqual(self.invoke(), {'status': 'observed', 'verified': True})
        finally:
            reset_memory_principal(token)

    def test_10_thread_context_and_exception_reset(self):
        original = current_memory_principal()
        async def call():
            token = bind_memory_principal('local_admin')
            try:
                with patch.object(self.bridge, 'verify_sqlite_wal',
                        side_effect=lambda: {'status': 'observed', 'verified': current_memory_principal() == 'local_admin'}):
                    self.assertTrue((await asyncio.to_thread(self.invoke))['verified'])
                with patch.object(self.bridge, 'verify_sqlite_wal', side_effect=RuntimeError('hidden')):
                    self.assertEqual(await asyncio.to_thread(self.invoke),
                                     {'status': 'error', 'error': 'diagnostic_unavailable'})
            finally:
                reset_memory_principal(token)
        asyncio.run(call())
        self.assertEqual(current_memory_principal(), original)

    def test_11_diff_approval_cannot_be_supplied(self):
        self.assertEqual(self.invoke('inspect_source_diff',
            {'path': 'src/example.py', 'approved_diff_paths': ['src/example.py']})['error_code'], 'INVALID_TOOL_CALL')
        token = bind_memory_principal('local_admin')
        try:
            self.assertEqual(self.invoke('inspect_source_diff', {'path': 'src/example.py'}), {'status': 'denied'})
        finally:
            reset_memory_principal(token)

    def test_12_unbound_batch_controller_remains_unavailable(self):
        token = bind_memory_principal('local_admin')
        try:
            self.assertEqual(self.invoke('process_batch_status'),
                {'status': 'unavailable', 'reason': 'no_existing_controller_bound'})
        finally:
            reset_memory_principal(token)


if __name__ == '__main__':
    unittest.main()
