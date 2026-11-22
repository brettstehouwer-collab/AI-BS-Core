"""Synthetic signing transactions; never sign a production file or access a key."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('native_release_signing', ROOT/'scripts/sign_native_candidate.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class SigningTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'original.exe'
        self.source.write_bytes(b'MZ synthetic unsigned fixture')
        self.original = self.source.read_bytes()
        self.digest = hashlib.sha256(self.original).hexdigest()
        self.dest = self.root/'signed.exe'
        self.thumb = 'A'*40
        self.calls = []
        self.cert = dict(thumbprint=self.thumb, subject='CN=Fixture Publisher',
            issuer='CN=Fixture CA', selfIssued=False, hasPrivateKey=True,
            codeSigningEku=True, chainValid=True, currentlyValid=True)
        self.result = dict(status='Valid', signerThumbprint=self.thumb,
            timestampPresent=True)

    def backend(self, mode, path, thumbprint, timestamp):
        self.calls.append(mode)
        if mode == 'inspect':
            return dict(self.cert)
        if mode == 'sign':
            with path.open('ab') as f:
                f.write(b' synthetic signature')
            return {}
        return dict(self.result)

    def run_sign(self, **overrides):
        args = dict(source=self.source, destination=self.dest, expected_sha256=self.digest,
            thumbprint=self.thumb, timestamp_url='https://timestamp.example.test/tsa',
            backend=self.backend)
        args.update(overrides)
        return m.sign_candidate(**args)

    def test_new_copy_receipt_and_original_preservation(self):
        result = self.run_sign()
        self.assertEqual(self.calls, ['inspect', 'sign', 'verify'])
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertNotEqual(self.dest.read_bytes(), self.original)
        self.assertTrue(result['signatureVerified'])
        self.assertFalse(result['recipientWorkflowAccepted'])
        self.assertEqual(result['signedSha256'], hashlib.sha256(self.dest.read_bytes()).hexdigest())

    def test_wrong_original_hash_never_calls_provider_or_writes(self):
        with self.assertRaises(m.SigningError):
            self.run_sign(expected_sha256='0'*64)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.dest.exists())

    def test_existing_destination_and_receipt_are_preserved(self):
        for path in (self.dest, Path(str(self.dest)+'.signing.json')):
            with self.subTest(path=path):
                path.write_bytes(b'existing')
                with self.assertRaises(m.SigningError):
                    self.run_sign()
                self.assertEqual(path.read_bytes(), b'existing')
                path.rename(path.with_suffix(path.suffix+'.retained'))
        self.assertEqual(self.calls, [])

    def test_certificate_gates_before_any_copy(self):
        for field, value in [('selfIssued', True), ('hasPrivateKey', False),
                ('codeSigningEku', False), ('chainValid', False),
                ('currentlyValid', False), ('thumbprint', 'B'*40)]:
            with self.subTest(field=field):
                old = self.cert[field]
                self.cert[field] = value
                with self.assertRaises(m.SigningError):
                    self.run_sign()
                self.assertFalse(self.dest.exists())
                self.cert[field] = old
        self.assertNotIn('sign', self.calls)

    def test_insecure_or_credentialed_timestamp_rejected(self):
        for url in ['http://timestamp.example.test', 'https://u:p@tsa.example.test',
                    'https://127.0.0.1', 'https://tsa.example.test/#fragment', 'https://localhost']:
            with self.subTest(url=url), self.assertRaises(m.SigningError):
                self.run_sign(timestamp_url=url)
        self.assertEqual(self.calls, [])

    def test_signature_mismatch_retains_failed_copy_and_receipt(self):
        self.result['signerThumbprint'] = 'B'*40
        with self.assertRaises(m.SigningError):
            self.run_sign()
        self.assertTrue(self.dest.exists())
        receipt = json.loads(Path(str(self.dest)+'.signing.json').read_text())
        self.assertEqual(receipt['status'], 'FAILED_RETAINED')
        self.assertFalse(receipt['signatureVerified'])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_missing_timestamp_or_invalid_signature_not_accepted(self):
        for field, value in [('timestampPresent', False), ('status', 'NotTrusted')]:
            with self.subTest(field=field):
                dest = self.root/(field+'.exe')
                old = self.result[field]
                self.result[field] = value
                with self.assertRaises(m.SigningError):
                    self.run_sign(destination=dest)
                self.assertTrue(dest.exists())
                self.result[field] = old

    def test_signing_failure_has_no_secret_message_and_no_cleanup(self):
        def fail(mode, *args):
            if mode == 'inspect':
                return self.cert
            raise RuntimeError('synthetic-private-value')
        with self.assertRaises(m.SigningError) as error:
            self.run_sign(backend=fail)
        receipt = Path(str(self.dest)+'.signing.json').read_text()
        self.assertNotIn('synthetic-private-value', receipt+str(error.exception))
        self.assertTrue(self.dest.exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_boolean_strings_and_missing_metadata_fail_closed(self):
        self.cert['chainValid'] = 'true'
        with self.assertRaises(m.SigningError):
            self.run_sign()
        self.assertFalse(self.dest.exists())

    def test_source_alias_missing_source_and_symlink_fail_before_provider(self):
        for source, dest in [(self.source, self.source),
                (self.root/'missing.exe', self.dest)]:
            with self.subTest(source=source), self.assertRaises(m.SigningError):
                self.run_sign(source=source, destination=dest)
        self.assertEqual(self.calls, [])
        # Symlink privilege is not available to every Windows test account.
        link = self.root/'linked.exe'
        try:
            link.symlink_to(self.source)
        except OSError:
            return
        with self.assertRaises(m.SigningError):
            self.run_sign(source=link)
        self.assertEqual(self.calls, [])

    def test_inspection_failure_is_sanitized_and_creates_nothing(self):
        def fail(*args):
            raise RuntimeError('synthetic-private-value')
        with self.assertRaises(m.SigningError) as error:
            self.run_sign(backend=fail)
        self.assertNotIn('synthetic-private-value', str(error.exception))
        self.assertFalse(self.dest.exists())
        self.assertFalse(Path(str(self.dest)+'.signing.json').exists())

    def test_destination_created_during_inspection_is_never_overwritten(self):
        def race(mode, *args):
            self.dest.write_bytes(b'existing concurrent candidate')
            return self.cert
        with self.assertRaises(m.SigningError):
            self.run_sign(backend=race)
        self.assertEqual(self.dest.read_bytes(), b'existing concurrent candidate')
        self.assertEqual(self.source.read_bytes(), self.original)

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_original_windows_handle_denies_concurrent_write_and_replace(self):
        def guarded(mode, *args):
            if mode == 'inspect':
                with self.assertRaises(PermissionError):
                    with self.source.open('wb') as stream:
                        stream.write(b'changed')
                substitute = self.root/'substitute.exe'
                substitute.write_bytes(b'MZ replacement')
                with self.assertRaises(PermissionError):
                    os.replace(substitute, self.source)
            return self.backend(mode, *args)
        self.run_sign(backend=guarded)
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main()
