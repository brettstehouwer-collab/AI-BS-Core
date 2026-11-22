"""Restart inspection of applied disposable trusted-local synthetic evidence."""
import unittest
from unittest.mock import patch

import test_coding_mode_local as fixtures
from core import coding_mode_execution as service
from core import coding_mode_local as local


class RestartTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.TrustedLocalTests.setUpClass.__func__)
    setUp = fixtures.TrustedLocalTests.setUp
    payload = fixtures.TrustedLocalTests.payload
    job = fixtures.TrustedLocalTests.job
    client = fixtures.TrustedLocalTests.client
    generate = fixtures.TrustedLocalTests.generate
    fresh_plan = fixtures.TrustedLocalTests.fresh_plan
    prepare_and_plan = fixtures.TrustedLocalTests.prepare_and_plan
    finish = fixtures.TrustedLocalTests.finish

    def test_restart_retains_applied_bytes_without_replay(self):
        result = fixtures.TrustedLocalTests.run_task(self)
        self.assertEqual(result['state'], 'VERIFIED', result)
        review = service.review_execution(self.owner, self.execution['execution_id'])
        self.assertTrue(review['can_apply'])
        applied = service.apply_execution(self.owner, self.execution['execution_id'], review['review_token'])
        self.assertEqual(applied['application']['state'], 'APPLIED')
        source = self.repo/'src/app.py'
        self.assertEqual(source.read_bytes(), b'value = 42\n')
        folder = service._folder(self.owner, self.execution['execution_id'])
        retained = {path: path.read_bytes() for path in folder.rglob('*') if path.is_file()}
        calls = self.provider.await_count
        with patch.object(local, '_KEY', b'fresh-restart-runtime-key-00000000'), \
                patch.object(local, 'start', side_effect=AssertionError('No verification replay')), \
                patch('subprocess.Popen', side_effect=AssertionError('No child execution')):
            inspected = service.read_execution(self.owner, self.execution['execution_id'])
            recovered = service.recover_execution(self.owner, self.execution['execution_id'])
        for response in (inspected, recovered):
            self.assertEqual(response['state'], 'UNCONFIRMED', response)
            self.assertEqual(response['application']['state'], 'ATTENTION_REQUIRED')
            self.assertFalse(response['runtime_receipt_verified'])
            self.assertFalse(response['can_apply'])
            self.assertFalse(response['apply_authorized'])
        self.assertFalse(recovered['replayed'])
        self.assertEqual(source.read_bytes(), b'value = 42\n')
        self.assertEqual((folder/'application_backups/src/app.py').read_bytes(), b'value = 1\n')
        self.assertEqual(self.provider.await_count, calls)
        self.assertEqual({path: path.read_bytes() for path in folder.rglob('*') if path.is_file()}, retained)
