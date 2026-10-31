"""Synthetic profile fixtures; no Qt, real profiles, credentials or dispatch."""
from __future__ import annotations

import ast
import base64
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
from typing import Any, Dict
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]


def load_contract():
    path = ROOT/'native_studio/broadcast_control.py'
    spec = importlib.util.spec_from_file_location('_audit_broadcast_contract205', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_profile_class():
    """Compile only the persistence class and static public defaults."""
    path = ROOT/'native_studio/broadcast_stream_engine.py'
    parsed = ast.parse(path.read_text(encoding='utf-8-sig'))
    specification = next(node for node in parsed.body if isinstance(node, ast.AnnAssign)
                         and isinstance(node.target, ast.Name) and node.target.id == 'STREAM_PLATFORM_SPECS')
    defaults = ast.literal_eval(specification.value)
    node = next(node for node in parsed.body if isinstance(node, ast.ClassDef) and node.name == 'StreamProfileManager')
    namespace = {'Path': Path, 'Dict': Dict, 'Any': Any, 'json': json, 'copy': copy,
                 'base64': base64, 'os': os, 'tempfile': tempfile,
                 'STREAM_PLATFORM_SPECS': defaults}
    exec(compile(ast.Module([node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['StreamProfileManager']


class NativeBroadcastValidation205Tests(unittest.TestCase):
    def setUp(self):
        self.contract = load_contract()
        self.profiles = load_profile_class()
        self.cfg = self.profiles.get_defaults()
        self.cfg['destinations']['facebook'].update(
            enabled=True, url='rtmps://example.invalid:443/rtmp/', key='synthetic-fb-secret-only')

    def test_one_enabled_target_does_not_require_disabled_target_keys(self):
        self.cfg['destinations']['twitch'].update(enabled=False, url='deliberately invalid unused URL', key='')
        payload = self.contract.stream_payload(self.cfg)
        self.assertEqual([item['name'] for item in payload['endpoints']], ['facebook'])
        self.assertEqual(payload['endpoints'][0]['key'], 'synthetic-fb-secret-only')

    def test_enabled_missing_keys_identify_all_affected_platforms(self):
        self.cfg['destinations']['twitch'].update(enabled=True, key='')
        self.cfg['destinations']['youtube'].update(enabled=True, key='')
        with self.assertRaises(ValueError) as caught:
            self.contract.stream_payload(self.cfg)
        message = str(caught.exception).lower()
        self.assertIn('twitch', message)
        self.assertIn('youtube', message)
        self.assertIn('key', message)
        self.assertNotIn('synthetic-fb-secret-only', message)
        self.assertNotIn('example.invalid', message)

    def test_local_srt_reports_unsupported_transport_instead_of_missing_key(self):
        for destination in self.cfg['destinations'].values():
            destination['enabled'] = False
        self.cfg['destinations']['sovereign_srt'].update(enabled=True, key='')
        with self.assertRaises(ValueError) as caught:
            self.contract.stream_payload(self.cfg)
        message = str(caught.exception).lower()
        self.assertIn('srt', message)
        self.assertTrue('unsupported' in message or 'not supported' in message)
        self.assertNotIn('missing', message)

    def test_multiple_configuration_problems_are_reported_together(self):
        self.cfg['destinations']['twitch'].update(enabled=True, key='')
        self.cfg['destinations']['youtube'].update(enabled=True, key='')
        self.cfg['destinations']['sovereign_srt']['enabled'] = True
        with self.assertRaises(ValueError) as caught:
            self.contract.stream_payload(self.cfg)
        message = str(caught.exception).lower()
        for expected in ['twitch', 'youtube', 'srt']:
            self.assertIn(expected, message)

    def test_validation_preserves_entire_profile_schema_and_source_values(self):
        self.cfg['custom_extension'] = {'retained': ['history', {'local': True}]}
        self.cfg['destinations']['facebook']['custom_destination_field'] = {'retained': True}
        before = copy.deepcopy(self.cfg)
        self.contract.stream_payload(self.cfg)
        self.assertEqual(self.cfg, before)

    def test_invalid_destination_error_does_not_echo_private_url_or_key(self):
        self.cfg['destinations']['facebook'].update(url='https://private.invalid/synthetic-url-secret', key='synthetic-key-secret')
        with self.assertRaises(ValueError) as caught:
            self.contract.stream_payload(self.cfg)
        message = str(caught.exception)
        self.assertNotIn('private.invalid', message)
        self.assertNotIn('synthetic-url-secret', message)
        self.assertNotIn('synthetic-key-secret', message)
        self.assertIn('facebook', message.lower())

    def test_encrypted_disk_keys_keep_normalized_local_caller_schema(self):
        # This stand-in proves serialization/API shape only. It does not claim
        # DPAPI cryptographic strength, cross-account portability or live keys.
        crypto = types.ModuleType('win32crypt')
        crypto.CryptProtectData = Mock(return_value=b'synthetic-cipher-only')
        crypto.CryptUnprotectData = Mock(return_value=('fixture', b'synthetic-fb-secret-only'))
        self.cfg['custom_extension'] = {'retained': True}
        before = copy.deepcopy(self.cfg)
        with tempfile.TemporaryDirectory(prefix='broadcast_profile205_') as folder:
            target = Path(folder)/'profiles.json'
            self.profiles.PROFILE_FILE = target
            with patch.dict(sys.modules, {'win32crypt': crypto}):
                self.assertTrue(self.profiles.save(self.cfg))
                raw = target.read_text(encoding='utf-8')
                self.assertNotIn('synthetic-fb-secret-only', raw)
                serialized = json.loads(raw)
                self.assertIn('key_dpapi', serialized['destinations']['facebook'])
                loaded = self.profiles.load()
            self.assertEqual(loaded['destinations']['facebook']['key'], 'synthetic-fb-secret-only')
            self.assertEqual(loaded['custom_extension'], {'retained': True})
            self.assertEqual(self.cfg, before)


if __name__ == '__main__':
    unittest.main()
