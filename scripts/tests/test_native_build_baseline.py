"""Build admission fixtures only: never imports or launches the native app."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_builder', ROOT / 'scripts/build_native_web_parity.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class VerifiedBaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = self.root / 'backups/web'
        self.evidence.mkdir(parents=True)
        self.manifest = self.evidence / 'hosting_artifact_manifest_final.json'
        self.proof = self.evidence / 'live_verification.json'
        self.output = self.root / 'backups/native'
        self.web = {'sourceVersion': 'v5.329.52', 'buildId': 'web-v5-329-52-fixture', 'count': 2, 'files': [
            {'relative': 'index.html', 'bytes': 10, 'sha256': 'a' * 64},
            {'relative': 'version.json', 'bytes': 20, 'sha256': 'b' * 64}]}
        self.live = {'origin': 'https://ai-bs-dashboard.web.app', 'sourceVersion': self.web['sourceVersion'], 'buildId': self.web['buildId'], 'count': 2, 'passed': 2, 'failed': 0, 'versionMatch': True, 'excludedProbes': [{'notPublished': True}], 'files': [dict(row, status=200, match=True, expectedSha256=row['sha256']) for row in self.web['files']]}
        self.trusted = {'sourceVersion': self.web['sourceVersion'], 'buildId': self.web['buildId'], 'count': 2, 'origin': self.live['origin']}
        self.pin()
        (self.root / 'version.txt').write_text('v5.329.52')
        assets = self.root / 'frontend/public'
        assets.mkdir(parents=True)
        for name in ['favicon.ico', 'psychedelic_theme.jpg']:
            (assets / name).write_bytes(b'fixture')
        self.root_patch = patch.object(builder, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.modules_patch = patch.object(builder, 'native_modules', return_value=[])
        self.modules_patch.start()
        self.addCleanup(self.modules_patch.stop)
        self.trust_patch = patch.object(builder, 'VERIFIED_WEB_BASELINE', self.trusted, create=True)
        self.trust_patch.start()
        self.addCleanup(self.trust_patch.stop)

    def pin(self):
        self.manifest.write_text(json.dumps(self.web))
        self.proof.write_text(json.dumps(self.live))
        self.trusted['manifestSha256'] = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.trusted['verificationSha256'] = hashlib.sha256(self.proof.read_bytes()).hexdigest()

    def stage(self):
        return builder.stage(self.output, self.manifest)

    def denied_before_writes(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.stage()
        self.assertFalse(self.output.exists())

    def test_current_verified_baseline_records_proof_and_preserves_gates(self):
        result = self.stage()
        baseline = result['webBaseline']
        self.assertEqual(baseline['web_build_id'], self.web['buildId'])
        self.assertEqual(baseline['web_verification_sha256'], self.trusted['verificationSha256'])
        self.assertFalse(baseline['parity_verified'])
        self.assertFalse(baseline['isolated_execution_available'])
        self.assertEqual(baseline['signing'], 'NOT_SIGNED')
        self.assertFalse(result['applicationExecuted'])

    def test_manifest_bytes_must_match_admitted_pin(self):
        self.manifest.write_text(self.manifest.read_text() + '\n')
        self.denied_before_writes()

    def test_proof_bytes_must_match_admitted_pin(self):
        self.proof.write_text(self.proof.read_text() + '\n')
        self.denied_before_writes()

    def test_missing_proof_is_denied(self):
        self.proof.rename(self.evidence / 'proof.retained')
        self.denied_before_writes()

    def test_wrong_release_is_denied_even_with_fixture_hash(self):
        self.web['sourceVersion'] = 'v5.329.50'
        self.pin()
        self.denied_before_writes()

    def test_failed_live_check_is_denied_even_with_fixture_hash(self):
        self.live['failed'] = 1
        self.pin()
        self.denied_before_writes()

    def test_live_hashes_must_match_exact_manifest(self):
        self.live['files'][0]['sha256'] = 'c' * 64
        self.pin()
        self.denied_before_writes()

    def test_missing_live_file_is_denied(self):
        self.live['files'].pop()
        self.pin()
        self.denied_before_writes()

    def test_excluded_private_path_must_not_be_published(self):
        self.live['excludedProbes'][0]['notPublished'] = False
        self.pin()
        self.denied_before_writes()


if __name__ == '__main__':
    unittest.main()
