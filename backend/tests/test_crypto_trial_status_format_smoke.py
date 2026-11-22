"""Ten truthful status-mode versus entry-cutoff formatting cases."""
import unittest
from core.crypto_trial_status_chat import _format
from core.crypto_trial_status_contract import trial_status


class CryptoTrialStatusFormatSmoke(unittest.TestCase):
    def test_01_qualification_latched(self):
        text=_format(trial_status('qualification',entry_held=True))
        self.assertIn('simulation',text);self.assertIn('cutoff is latched',text)
    def test_02_qualification_not_latched(self):
        text=_format(trial_status('qualification',entry_held=False))
        self.assertIn('simulation',text);self.assertIn('cutoff is not latched',text)
    def test_03_held_latched(self):
        text=_format(trial_status('held',entry_held=True))
        self.assertIn('cutoff is latched',text);self.assertIn('new entries are held',text)
    def test_04_held_not_latched(self):
        text=_format(trial_status('held',entry_held=False))
        self.assertIn('cutoff is not latched',text)
        self.assertNotIn('held by the retained local cutoff',text)
    def test_05_not_registered_no_cutoff_claim(self):
        self.assertNotIn('cutoff is',_format(trial_status('not_registered')))
    def test_06_unavailable_no_cutoff_claim(self):
        self.assertNotIn('cutoff is',_format(trial_status('unavailable')))
    def test_07_denied_no_cutoff_claim(self):
        self.assertNotIn('cutoff is',_format(trial_status('denied')))
    def test_08_malformed_cutoff_type_no_claim(self):
        result=trial_status('qualification');result['entry_held']='yes'
        self.assertNotIn('cutoff is',_format(result));self.assertIn('unavailable',_format(result))
    def test_09_both_modes_live_held_independently(self):
        for mode in ('qualification','held'):
            for latch in (True,False):
                with self.subTest(mode=mode,latch=latch):
                    self.assertIn('Live trading remains held',_format(trial_status(mode,entry_held=latch)))
    def test_10_no_private_free_text_in_cutoff_lines(self):
        result=trial_status('held',entry_held=True);result['reason']='PRIVATE_SENTINEL'
        self.assertNotIn('PRIVATE_SENTINEL',_format(result));self.assertNotIn('cutoff is',_format(result))


if __name__=='__main__':unittest.main()
