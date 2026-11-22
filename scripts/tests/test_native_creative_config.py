"""Strict inert configuration; no candidate launch, router activation or Qt."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from security import native_creative_config as config
from security.native_creative_controller import ReviewedCandidate, ReviewedFile


class NativeCreativeConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'candidate.json'

    def manifest(self, enabled=True):
        layout = config.candidate_layout()
        pin = lambda path: {'path': path, 'sha256': 'a' * 64}
        spec = {'executable': pin(layout['executable_path']),
                'arguments': layout['arguments'], 'cwd': layout['cwd'],
                'environment': layout['environment'],
                'dependencies': [pin(path) for path in layout['dependency_paths']]}
        candidate = ReviewedCandidate(ReviewedFile(**spec['executable']),
            tuple(spec['arguments']), spec['cwd'], tuple(tuple(pair) for pair in spec['environment']),
            tuple(ReviewedFile(**row) for row in spec['dependencies']), layout['contract'])
        return {'schema': 1, 'enabled': enabled, 'contract': layout['contract'], 'capacity': 1,
                'candidate': spec, 'candidate_sha256': candidate.sha256}

    def write(self, value):
        self.path.write_text(json.dumps(value), encoding='utf8')

    def test_missing_and_minimal_disabled_do_not_verify_or_create(self):
        with patch.object(config, '_verify_pins') as verify:
            self.assertIsNone(config.load_reviewed_candidate(self.path))
            self.assertFalse(self.path.exists())
            self.write({'schema': 1, 'enabled': False})
            before = self.path.read_bytes()
            self.assertIsNone(config.load_reviewed_candidate(self.path))
            self.assertEqual(self.path.read_bytes(), before)
        verify.assert_not_called()

    def test_full_disabled_is_validated_but_never_opens_candidate_files(self):
        self.write(self.manifest(False))
        with patch.object(config, '_verify_pins') as verify:
            self.assertIsNone(config.load_reviewed_candidate(self.path))
        verify.assert_not_called()

    def test_enabled_schema_returns_exact_fixed_spec_with_mocked_byte_verification(self):
        value = self.manifest()
        self.write(value)
        with patch.object(config, '_verify_pins') as verify:
            candidate = config.load_reviewed_candidate(self.path)
        verify.assert_called_once_with(candidate)
        self.assertEqual(candidate.sha256, value['candidate_sha256'])
        self.assertEqual(candidate.arguments, tuple(config.candidate_layout()['arguments']))
        self.assertEqual(candidate.contract, config.PIPE_BOOTSTRAP_CONTRACT)

    def test_invalid_schema_types_and_nonfinite_or_duplicate_json_refused(self):
        cases = ['{"schema":1,"enabled":false,"enabled":true}',
                 '{"schema":1,"enabled":NaN}', '{"schema":true,"enabled":false}',
                 '{"schema":1,"enabled":0}', '[]',
                 '{"schema":1,"enabled":false,"extra":true}']
        with patch.object(config, '_verify_pins') as verify:
            for raw in cases:
                with self.subTest(raw=raw):
                    self.path.write_text(raw, encoding='utf8')
                    with self.assertRaises(config.NativeCreativeConfigError):
                        config.load_reviewed_candidate(self.path)
        verify.assert_not_called()

    def test_caller_paths_arguments_env_contract_and_capacity_refused(self):
        original = self.manifest()
        cases = []
        for key, replacement in [('contract', 'stdin-v1'), ('capacity', 2), ('candidate_sha256', 'f'*64)]:
            value = copy.deepcopy(original);value[key] = replacement;cases.append(value)
        for key, replacement in [('arguments', ['-c', 'raise SystemExit(0)']), ('cwd', 'C:\\'),
                                 ('environment', [['GEMINI_API_KEY', 'not-a-real-key']])]:
            value = copy.deepcopy(original);value['candidate'][key] = replacement;cases.append(value)
        for field in ('executable', 'dependencies'):
            value = copy.deepcopy(original)
            row = value['candidate'][field] if field == 'executable' else value['candidate'][field][0]
            row['path'] = 'C:\\other.py';cases.append(value)
        with patch.object(config, '_verify_pins') as verify:
            for value in cases:
                with self.subTest(value=value):
                    self.write(value)
                    with self.assertRaises(config.NativeCreativeConfigError):
                        config.load_reviewed_candidate(self.path)
        verify.assert_not_called()

    def test_missing_or_reordered_duplicate_dependencies_refused(self):
        original = self.manifest()
        for change in ('missing', 'reordered', 'duplicate'):
            value = copy.deepcopy(original)
            rows = value['candidate']['dependencies']
            if change == 'missing':rows.pop()
            elif change == 'reordered':rows.reverse()
            else:rows[1] = rows[0]
            self.write(value)
            with self.assertRaises(config.NativeCreativeConfigError):
                config.load_reviewed_candidate(self.path)

    def test_oversized_and_hardlinked_manifest_refused(self):
        self.path.write_bytes(b' ' * (config.MAX_CONFIG_BYTES + 1))
        with self.assertRaises(config.NativeCreativeConfigError):
            config.load_reviewed_candidate(self.path)
        self.write({'schema': 1, 'enabled': False})
        alias = self.path.parent / 'alias.json'
        os.link(self.path, alias)
        with self.assertRaises(config.NativeCreativeConfigError):
            config.load_reviewed_candidate(self.path)

    def test_byte_verification_failure_stays_sanitized(self):
        self.write(self.manifest())
        with patch.object(config, '_verify_pins', side_effect=ValueError('private fixture detail')):
            with self.assertRaises(config.NativeCreativeConfigError) as error:
                config.load_reviewed_candidate(self.path)
        self.assertNotIn('private fixture detail', str(error.exception))

    def test_actual_enabled_mismatching_file_bytes_are_refused(self):
        self.write(self.manifest())
        with self.assertRaises(config.NativeCreativeConfigError):
            config.load_reviewed_candidate(self.path)

    def test_actual_manifest_hashes_when_fixed_launcher_exists(self):
        value = self.manifest()
        files = [value['candidate']['executable'], *value['candidate']['dependencies']]
        if not all(Path(row['path']).is_file() for row in files):
            self.skipTest('Fixed launcher not yet present; mocked schema checks are separate')
        for row in files:
            row['sha256'] = hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()
        spec = value['candidate']
        candidate = ReviewedCandidate(ReviewedFile(**spec['executable']), tuple(spec['arguments']),
            spec['cwd'], tuple(tuple(pair) for pair in spec['environment']),
            tuple(ReviewedFile(**row) for row in spec['dependencies']), value['contract'])
        value['candidate_sha256'] = candidate.sha256
        self.write(value)
        before = set(sys.modules)
        actual = config.load_reviewed_candidate(self.path)
        self.assertEqual(actual.sha256, candidate.sha256)
        self.assertFalse(any(name.startswith('PyQt6') for name in set(sys.modules) - before))


if __name__ == '__main__':unittest.main()
