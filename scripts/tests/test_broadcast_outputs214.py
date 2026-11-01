import unittest
from unittest.mock import Mock, patch
from backend.core import broadcast_outputs as outputs
from native_studio.broadcast_preferences import PROFILES


class OutputContracts(unittest.TestCase):
    def sender(self):
        return outputs.DestinationEncoder({'name':'youtube','url':'rtmps://example.invalid/live',
                                           'key':'SYNTHETIC-PRIVATE-KEY'}, PROFILES['youtube'])

    def test_destination_encoders_have_independent_bitrates_and_local_clocked_input(self):
        for name, profile in PROFILES.items():
            command=outputs.encoder_command(profile, 'rtmps://example.invalid/fixture')
            self.assertEqual(command[command.index('-b:v')+1], str(profile['video_kbps'])+'k')
            self.assertLess(command.index('-re'), command.index('-i'))
            self.assertEqual(command[command.index('-i')+1], outputs.SOURCE)

    def test_public_snapshot_and_errors_never_expose_publish_secrets(self):
        sender=self.sender()
        self.assertNotIn('SYNTHETIC-PRIVATE-KEY', str(sender.snapshot()))
        self.assertNotIn('SYNTHETIC-PRIVATE-KEY', sender._redact(sender._url))

    def test_retry_budget_is_finite(self):
        sender=self.sender(); sender.process=Mock(); sender.process.poll.return_value=1
        sender.attempts=3
        with patch.object(sender, 'start') as start:
            self.assertIsNone(sender.maintain()); start.assert_not_called()

    def test_an_alive_output_with_frozen_media_is_stopped_and_classified(self):
        sender=self.sender(); sender.process=Mock(); sender.process.poll.return_value=None
        sender._frame_advanced=sender._media_advanced=0
        with patch.object(outputs.time, 'monotonic', return_value=20): sender.maintain()
        sender.process.terminate.assert_called_once()
        self.assertEqual(sender.error_code, 'OUTPUT_STALLED')
