"""Offline preview contracts with fake media/sink/manifest; no real playback."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import importlib
import unittest
import tempfile
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage

class Signal:
    def __init__(self):self.handlers=[]
    def connect(self,handler,*_,**__):self.handlers.append(handler)
    def disconnect(self,handler):
        if handler in self.handlers:self.handlers.remove(handler)
    def emit(self,*args):
        for handler in list(self.handlers):handler(*args)
class Player:
    def __init__(self,*_):self.errorOccurred=Signal();self.sources=[];self.plays=0;self.stops=0;self.audio=[]
    def setSource(self,value):self.sources.append(value)
    def play(self):self.plays+=1
    def stop(self):self.stops+=1
    def setVideoSink(self,value):self.sink=value
    def setAudioOutput(self,value):self.audio.append(value)
class Sink:
    def __init__(self,*_):self.videoFrameChanged=Signal()
    def setVideoFrame(self,*_):pass
class Manifest:
    def __init__(self):self.good=True;self.started=False;self.stopped=False;self.modified_utc=2000.
    def start(self):self.started=True;return True
    def snapshot(self):return {'valid':self.good,'fresh':self.good,'advancing':self.good,'modified_utc':self.modified_utc,'error_code':None if self.good else 'HLS_STALE'}
    def stop(self,timeout=.2):self.stopped=True;return True
class Frame:
    def __init__(self):self.conversions=0
    def isValid(self):return True
    def toImage(self):
        self.conversions+=1;image=QImage(2,2,QImage.Format.Format_RGB32);image.fill(0xff00aa44);return image

class BroadcastPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.m=importlib.import_module('native_studio.broadcast_preview');self.now=100.;self.player=Player();self.sink=Sink();self.manifest=Manifest()
        self.preview=self.m.NativeBroadcastPreview(player_factory=lambda *_:self.player,sink_factory=lambda *_:self.sink,
            manifest_factory=lambda:self.manifest,clock=lambda:self.now)
        self.frames=[];self.clears=[];self.preview.frame_ready.connect(self.frames.append);self.preview.cleared.connect(lambda:self.clears.append(True))
        self.addCleanup(self.preview.shutdown)
    def state(self,**changes):
        result={'active':True,'can_select':True,'protocol_version':2,'session_id':'a'*32,'capture_state':'capturing',
                'source_mode':'auto_game','game_frame_verified':True,'controller_pid':100,'encoder_pid':101,
                'controller_create_time':1000.,'encoder_create_time':1001.,'frames_encoded':30,'out_time_us':1000000};result.update(changes);return result
    def test_creation_does_not_play_and_source_is_fixed_loopback_hls_without_audio(self):
        self.assertEqual(self.player.plays,0);self.preview.set_coordinator_state(self.state(preview_url='https://untrusted.invalid'))
        self.assertEqual(self.player.plays,1)
        source=self.player.sources[-1]
        self.assertEqual(source.toString(),'http://127.0.0.1:9011/hls/native/index.m3u8')
        self.assertFalse(source.isLocalFile())
        self.assertEqual(self.player.audio,[None]);self.assertFalse(self.preview.preview_status()['audio_enabled'])

    def test_manifest_metadata_uses_shared_delete_reader_not_path_open(self):
        raw=b'#EXTM3U\n#EXT-X-VERSION:6\n#EXT-X-MEDIA-SEQUENCE:2\n#EXTINF:2,\nsegment_000000002.ts\n'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'index.m3u8'
            path.write_bytes(raw)
            monitor=self.m._ManifestMonitor()
            with patch.object(self.m,'HLS_PATH',path), \
                 patch.object(self.m,'read_shared_bytes',return_value=raw,create=True) as reader, \
                 patch.object(Path,'open',side_effect=AssertionError('Original file must not be held open')), \
                 patch.object(monitor._stop,'wait',side_effect=lambda *_:monitor._stop.set()):
                monitor._run()
            reader.assert_called_once_with(path,max_bytes=32768)
            self.assertTrue(monitor.snapshot()['valid'])
    def test_held_unknown_legacy_or_unverified_auto_state_never_decodes(self):
        for changes in [{'active':False},{'can_select':False},{'protocol_version':1},{'protocol_version':True},
                        {'session_id':'bad'},{'capture_state':'holding'},{'game_frame_verified':False},
                        {'source_mode':'screen'}]:
            self.preview.set_coordinator_state(self.state(**changes))
        self.assertEqual(self.player.plays,0);self.assertEqual(self.frames,[])
    def test_old_queued_frame_after_session_change_is_rejected(self):
        self.preview.set_coordinator_state(self.state());old=self.sink.videoFrameChanged.handlers[-1]
        self.preview.set_coordinator_state(self.state(session_id='b'*32));old(Frame())
        self.assertEqual(self.frames,[]);self.assertTrue(self.clears)
        self.sink.videoFrameChanged.emit(Frame());self.assertEqual(len(self.frames),1)
    def test_status_ttl_expires_before_frame_conversion_and_clears_image(self):
        self.preview.set_coordinator_state(self.state());handler=self.sink.videoFrameChanged.handlers[-1]
        self.now+=3.1;frame=Frame();handler(frame)
        self.assertEqual(frame.conversions,0);self.assertEqual(self.frames,[]);self.assertTrue(self.clears)
        self.assertFalse(self.preview.preview_status()['showing'])
    def test_manifest_stall_halts_decode_and_clears_without_broadcast_actions(self):
        self.preview.set_coordinator_state(self.state());self.sink.videoFrameChanged.emit(Frame())
        self.manifest.good=False;self.preview._tick()
        self.assertTrue(self.clears);self.assertFalse(self.preview.preview_status()['showing'])
    def test_retries_are_bounded_and_shutdown_ignores_late_frames(self):
        self.preview.set_coordinator_state(self.state())
        for _ in range(5):
            self.player.errorOccurred.emit(1);self.now+=10;self.preview.set_coordinator_state(self.state());self.preview._tick()
        self.assertLessEqual(self.player.plays,3)
        callback=self.sink.videoFrameChanged.handlers[-1] if self.sink.videoFrameChanged.handlers else lambda *_:None
        self.preview.shutdown();callback(Frame());self.assertTrue(self.manifest.stopped)
        self.assertEqual(self.preview.preview_status()['state'],'closed')
    def test_checkbox_stops_only_preview_and_explicit_manual_window_is_supported(self):
        self.preview.set_coordinator_state(self.state(source_mode='window',game_frame_verified=False))
        self.assertEqual(self.player.plays,1);self.preview.set_preview_enabled(False)
        self.assertEqual(self.preview.preview_status()['state'],'disabled');self.assertTrue(self.clears)
    def test_manifest_parser_rejects_urls_keys_traversal_and_unbounded_payload(self):
        valid=b'#EXTM3U\n#EXT-X-VERSION:6\n#EXT-X-MEDIA-SEQUENCE:2\n#EXTINF:2,\nsegment_000000002.ts\n'
        self.assertEqual(self.m.parse_preview_manifest(valid),2)
        for raw in [valid.replace(b'segment_000000002.ts',b'../private.ts'),valid.replace(b'segment_000000002.ts',b'https://other.invalid/a.ts'),
                    valid+b'#EXT-X-KEY:METHOD=AES-128,URI="file:///private"\n',b'x'*32769]:
            with self.assertRaises(ValueError):self.m.parse_preview_manifest(raw)
    def test_source_mode_change_rejects_old_queued_frame_and_repeated_shutdown_stays_unconfirmed(self):
        self.preview.set_coordinator_state(self.state());old=self.sink.videoFrameChanged.handlers[-1]
        self.preview.set_coordinator_state(self.state(source_mode='window',game_frame_verified=False));old(Frame())
        self.assertEqual(self.frames,[])
        self.manifest.stop=lambda timeout=.2:False
        self.assertFalse(self.preview.shutdown());self.assertFalse(self.preview.shutdown())

    def test_previous_encoder_playlist_never_plays_until_new_epoch_has_output(self):
        self.manifest.modified_utc=1000.9
        self.preview.set_coordinator_state(self.state())
        self.assertEqual(self.player.plays,0)
        self.manifest.modified_utc=1001.01
        self.preview.set_coordinator_state(self.state(frames_encoded=0,out_time_us=0))
        self.assertEqual(self.player.plays,0)
        self.preview.set_coordinator_state(self.state())
        self.assertEqual(self.player.plays,1)
        old=self.sink.videoFrameChanged.handlers[-1]
        self.preview.set_coordinator_state(self.state(encoder_pid=102,encoder_create_time=1002.))
        old(Frame());self.assertEqual(self.frames,[])
        self.assertEqual(self.player.plays,1)
        self.manifest.modified_utc=1002.01;self.preview._tick()
        self.assertEqual(self.player.plays,2)
        self.preview.set_coordinator_state(self.state(encoder_create_time=None))
        self.assertFalse(self.preview._decoding)

    def test_verified_modern_status_exposes_epochs_but_legacy_or_unverified_does_not(self):
        client=importlib.import_module('native_studio.broadcast_secondary_control')
        raw=self.state();raw['status']='running_unverified'
        owner={'controller_pid':100,'encoder_pid':101}
        with patch.object(client,'_read_status',return_value=(raw,True)),patch.object(client,'_verified_owner',return_value=owner):
            status=client.read_broadcast_status()
        self.assertEqual(status['controller_create_time'],1000.)
        self.assertEqual(status['encoder_create_time'],1001.)
        legacy={key:value for key,value in raw.items() if key not in ('protocol_version','session_id')}
        with patch.object(client,'_read_status',return_value=(legacy,True)),patch.object(client,'_verified_owner',return_value=owner):
            self.assertNotIn('encoder_create_time',client.read_broadcast_status())
        with patch.object(client,'_read_status',return_value=(raw,True)),patch.object(client,'_verified_owner',return_value=None),patch.object(client,'_read_legacy_status',return_value=({},False)):
            self.assertNotIn('encoder_create_time',client.read_broadcast_status())

if __name__=='__main__':unittest.main()
