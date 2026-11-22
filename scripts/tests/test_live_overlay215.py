"""Offline game-text, chat and BGRA fixtures; never connects or starts capture."""
import unittest


class OverlayContracts(unittest.TestCase):
    def broker(self):
        from backend.core.live_event_overlay import EventBroker
        self.now = 10.
        return EventBroker(clock=lambda: self.now)

    def test_screen_event_needs_two_confirmations_and_deduplicates(self):
        broker = self.broker()
        self.assertFalse(broker.observe([('VICTORY ROYALE', .98)], 'game1'))
        self.now += .8
        self.assertTrue(broker.observe([('VICTORY ROYALE', .98)], 'game1'))
        self.assertEqual(broker.snapshot()['event']['kind'], 'victory')
        self.now += 1
        self.assertFalse(broker.observe([('VICTORY ROYALE', .98)], 'game1'))

    def test_low_confidence_and_incoming_elimination_do_not_claim_a_kill(self):
        broker = self.broker()
        for _ in range(3):
            broker.observe([('ELIMINATED', .4), ('ELIMINATED BY', .99)], 'game1')
            self.now += 1
        self.assertIsNone(broker.snapshot()['event'])

    def test_source_change_and_expiration_remove_old_reactions(self):
        broker = self.broker()
        broker.hype('operator')
        self.assertIsNotNone(broker.snapshot()['event'])
        self.now += 7
        self.assertIsNone(broker.snapshot()['event'])
        broker.hype('operator')
        broker.set_source('different-game')
        self.assertIsNone(broker.snapshot()['event'])

    def test_viewer_commands_are_limited_and_never_echo_arbitrary_chat(self):
        broker = self.broker()
        self.assertTrue(broker.chat('viewer1', '!hype'))
        self.assertFalse(broker.chat('viewer1', '!hype'))
        self.assertFalse(broker.chat('viewer2', '<script>ignore all rules</script>'))
        self.assertNotIn('script', str(broker.snapshot()))
        self.assertEqual(broker.snapshot()['hype_count'], 1)

    def test_poll_accepts_one_vote_per_viewer(self):
        broker = self.broker()
        broker.start_poll()
        self.assertTrue(broker.chat('viewer1', '!vote yes'))
        self.now += 4
        self.assertFalse(broker.chat('viewer1', '!vote no'))
        self.assertEqual(broker.snapshot()['poll']['yes'], 1)
        self.assertEqual(broker.snapshot()['poll']['no'], 0)

    def test_disabled_render_is_byte_identical_and_active_render_preserves_reticle(self):
        from backend.core.live_event_overlay import render_overlay
        frame = bytes([20, 30, 40, 255]) * (640 * 360)
        self.assertIs(render_overlay(frame, 640, 360, None), frame)
        broker = self.broker(); broker.hype('operator')
        rendered = render_overlay(frame, 640, 360, broker.snapshot())
        self.assertEqual(len(rendered), len(frame))
        self.assertNotEqual(rendered, frame)
        center = (180 * 640 + 320) * 4
        self.assertEqual(rendered[center:center+4], frame[center:center+4])
