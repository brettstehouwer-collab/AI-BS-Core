"""Synthetic PCM only: no devices, capture, windows or network."""
import importlib
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class AudioQueueTests(unittest.TestCase):
    def module(self):
        return importlib.import_module('backend.core.broadcast_audio')

    def test_queue_retains_bounded_latest_audio_and_counts_drops(self):
        queue = self.module().PcmQueue(channels=1, capacity_frames=4)
        queue.push(struct.pack('<6f', 1, 2, 3, 4, 5, 6))
        self.assertEqual(queue.dropped_frames, 2)
        self.assertEqual(struct.unpack('<4f', queue.read(4)), (3, 4, 5, 6))

    def test_underflow_has_exact_duration_and_channel_count(self):
        queue = self.module().PcmQueue(channels=2, capacity_frames=20)
        queue.push(struct.pack('<4f', .5, -.5, .25, -.25))
        data = queue.read(4)
        self.assertEqual(len(data), 4 * 2 * 4)
        self.assertEqual(struct.unpack('<8f', data), (.5, -.5, .25, -.25, 0, 0, 0, 0))

    def test_fragmented_packets_preserve_every_sample_in_order(self):
        queue = self.module().PcmQueue(channels=1, capacity_frames=100)
        queue.push(struct.pack('<2f', .1, .2))
        first = queue.read(1)
        queue.push(struct.pack('<2f', .3, .4))
        data = first + queue.read(3)
        for actual, expected in zip(struct.unpack('<4f', data), (.1, .2, .3, .4)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(queue.dropped_frames, 0)

    def test_invalid_pcm_is_rejected_before_changing_queue(self):
        queue = self.module().PcmQueue(channels=2, capacity_frames=4)
        with self.assertRaises(ValueError): queue.push(b'broken')
        self.assertEqual(queue.read(1), bytes(8))

    def test_constructing_capture_does_not_open_devices_or_a_pipe(self):
        audio = self.module().PcmAudioPipe('mic', 'Synthetic test device')
        state = audio.snapshot()
        self.assertFalse(state['active'])
        self.assertEqual(state['frames_captured'], 0)
        self.assertFalse(state['signal_detected'])

    def test_synchronous_pipe_connect_and_write_do_not_wait_on_an_unsignalled_event(self):
        module = self.module()
        audio = module.PcmAudioPipe('mic', 'Synthetic device')
        event = SimpleNamespace(Close=lambda: None)
        def must_not_wait(*args): raise AssertionError('Synchronous operation must not wait')
        fixtures = {'pywintypes': SimpleNamespace(OVERLAPPED=SimpleNamespace, error=OSError),
                    'win32event': SimpleNamespace(CreateEvent=lambda *args: event, WaitForSingleObject=must_not_wait),
                    'win32file': SimpleNamespace()}
        with patch.dict('sys.modules', fixtures):
            self.assertTrue(audio._operation(lambda _overlapped: 535))
            self.assertTrue(audio._operation(lambda _overlapped: (0, b'')))

    def test_secondary_encoder_consumes_owned_pcm_without_opening_a_dshow_device(self):
        from scripts.tests.test_broadcast_daemon_integrity import load_daemon
        daemon, namespace, process, _ = load_daemon()
        daemon._secondary_outputs = True
        pipe = SimpleNamespace(path=r'\\.\pipe\AI_BS_Audio_214fixture', rate=48000, channels=2)
        daemon._audio_provider_overrides = {'mic': pipe}
        daemon._capture_provider_override = SimpleNamespace(width=1280, height=720, fps=30,
            start=lambda **kwargs: True, stop=lambda **kwargs: True,
            read_frame=lambda **kwargs: bytes(1280*720*4))
        self.assertTrue(daemon.start_stream([], fps=30, resolution='1280x720', sources=[
            {'type':'game','enabled':True,'capture_policy':'verified_game_follow'},
            {'type':'mic','enabled':True,'deviceId':'__wasapi_pcm__','gain':.8}]))
        command = namespace['subprocess'].Popen.call_args.args[0]
        self.assertIn('f32le', command)
        self.assertIn(pipe.path, command)
        self.assertFalse(any(str(value).startswith('audio=') for value in command))
        self.assertNotIn('anullsrc=channel_layout=stereo:sample_rate=48000', command)
