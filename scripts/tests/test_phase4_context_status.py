"""Context reporting must recognize a worker RunAs shell without granting admission."""
import unittest
from scripts.inspect_phase4_readiness import worker_context_status

class WorkerContextStatusTests(unittest.TestCase):
    def test_authenticated_worker_shell_does_not_require_separate_desktop_logon(self):
        self.assertEqual(worker_context_status(False,True,False,True),
                         'WORKER_SHELL_PRESENT_ENTRY_ADMISSION_REQUIRED')

    def test_no_worker_context_retains_authentication_prerequisite(self):
        self.assertEqual(worker_context_status(False,True,False,False),
                         'AUTHENTICATED_WORKER_CONTEXT_REQUIRED')

    def test_current_worker_identity_still_requires_full_entry_admission(self):
        self.assertEqual(worker_context_status(True,True,False,True),
                         'WORKER_ENTRY_ADMISSION_REQUIRED')

    def test_worker_desktop_is_context_evidence_only(self):
        self.assertEqual(worker_context_status(False,True,True,False),
                         'WORKER_DESKTOP_PRESENT_ENTRY_ADMISSION_REQUIRED')

    def test_unverified_account_cannot_be_overridden_by_context_indicators(self):
        self.assertEqual(worker_context_status(True,False,True,True),
                         'EXPECTED_WORKER_ACCOUNT_NOT_VERIFIED')

if __name__=='__main__':unittest.main()
