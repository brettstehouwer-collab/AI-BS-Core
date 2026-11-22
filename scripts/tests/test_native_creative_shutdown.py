"""Actual owned controller shutdown never kills an acknowledged editor."""
import os
import threading
import time
import unittest
from unittest.mock import patch
from scripts.tests import test_native_creative_pipe_controller as fixture
from security.native_creative_controller import NativeControllerError
from security.firebase_auth import VerifiedFirebaseContext


@unittest.skipUnless(os.name=='nt','Windows owned controller')
class NativeShutdown(unittest.TestCase):
    def setUp(self):
        self.host=fixture.PipeControllerTests();self.host.setUp()
        self.addCleanup(self.host.doCleanups)

    def test_shutdown_drains_channel_preserves_acknowledged_child_and_blocks_new_launch(self):
        import _winapi
        observed=threading.Event();read=self.host.services.read_screenplay
        def actual_read(*args,**kwargs):
            result=read(*args,**kwargs);observed.set();return result
        self.host.services.read_screenplay=actual_read
        record=self.host.launch('read-hold')
        self.assertTrue(observed.wait(10));self.assertTrue(record.acknowledged)
        result=self.host.controller.shutdown()
        self.assertTrue(result['complete']);self.assertEqual(result['retained_resources'],0)
        self.assertEqual(_winapi.WaitForSingleObject(self.host.retained,0),258)
        self.assertFalse(record._result.termination_requested)
        self.assertFalse(record._pipes._fds)
        with patch('security.native_creative_controller._PinnedFiles')as pins:
            with self.assertRaises(NativeControllerError):
                self.host.controller.launch(VerifiedFirebaseContext(fixture.pdf.OWNER,time.monotonic()+60),
                    project='Pipe Project',revision=self.host.opening['revision'],
                    source_sha256=self.host.source['source_sha256'])
        pins.assert_not_called()
        self.assertTrue(self.host.controller.shutdown()['complete'])

    def test_pending_preflight_is_reported_and_cannot_reopen_authority_after_shutdown(self):
        # Block after the exact child has been created but before its grant is
        # issued. Shutdown must retain/report this outstanding caller honestly.
        entered=threading.Event();release=threading.Event();failures=[]
        original=self.host.ns['_issue_native_creative_grant']
        def preflight(*args,**kwargs):
            entered.set()
            if not release.wait(10):raise RuntimeError('Synthetic preflight bound')
            return original(*args,**kwargs)
        self.host.ns['_issue_native_creative_grant']=preflight
        self.addCleanup(release.set)
        def launch():
            try:self.host.launch('read-hold')
            except BaseException as error:failures.append(error)
        thread=threading.Thread(target=launch);thread.start()
        try:
            self.assertTrue(entered.wait(5))
            result=self.host.controller.shutdown()
            self.assertFalse(result['complete']);self.assertEqual(result['pending_launches'],1)
        finally:
            release.set();thread.join(timeout=10)
        self.assertFalse(thread.is_alive());self.assertEqual(len(failures),1)
        self.assertIsInstance(failures[0],NativeControllerError)
        self.assertTrue(self.host.controller.shutdown()['complete'])
        self.assertFalse(self.host.grants._grants)


if __name__=='__main__':unittest.main()
