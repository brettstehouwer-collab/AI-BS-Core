"""CPU/file fixtures only: no output devices, API keys, services or user files."""
import importlib
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from native_studio.audio_kernel import AudioEngine, EV_CLEAR, EV_GAIN, EV_MUTE, EV_SWING


class PatternExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.engine=AudioEngine(samplerate=16000)

    def exporter(self):
        return importlib.import_module('native_studio.pattern_export')

    def read(self,path):
        with wave.open(str(path),'rb') as f:
            return f.getparams(),np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').reshape(-1,2)

    def test_snapshot_includes_pending_controls_without_draining_live_ring(self):
        self.engine.set_step(0,0,True)
        self.engine.set_step(6,4,True,note=45)
        self.engine.set_bpm(90)
        self.engine.send(EV_SWING,0.25)
        self.engine.send(EV_GAIN,0,0.4)
        self.engine.send(EV_MUTE,2,1)
        tail=self.engine.ring.tail
        snap=self.engine.pattern_snapshot()
        self.assertTrue(snap.pattern[0,0]); self.assertTrue(snap.pattern[6,4])
        self.assertEqual(snap.notes[6,4],45)
        self.assertEqual(snap.bpm,90); self.assertEqual(snap.swing,0.25)
        self.assertAlmostEqual(snap.track_gain[0],0.4)
        self.assertTrue(snap.mute[2]); self.assertEqual(self.engine.ring.tail,tail)
        self.assertFalse(self.engine._pattern[0,0])
        self.assertIsNone(self.engine._stream)

    def test_snapshot_is_detached_and_immutable(self):
        self.engine.set_step(0,0,True)
        snap=self.engine.pattern_snapshot()
        self.engine.send(EV_CLEAR)
        self.assertTrue(snap.pattern[0,0])
        self.assertFalse(self.engine.pattern_snapshot().pattern.any())
        with self.assertRaises(ValueError):snap.pattern[0,0]=False

    def test_dropped_event_does_not_change_export_state(self):
        with patch.object(self.engine.ring,'push',return_value=False):
            self.assertFalse(self.engine.send(EV_GAIN,-1,0))
        self.assertEqual(self.engine.pattern_snapshot().master,0.8)

    def test_export_writes_verified_stereo_pcm_at_current_tempo_without_audio_start(self):
        self.engine.set_step(0,0,True)
        self.engine.set_bpm(120)
        target=self.folder/'pattern.wav'
        with patch.object(AudioEngine,'start',side_effect=AssertionError('No audio device permitted')):
            result=self.exporter().write_pattern_wav(target,self.engine.pattern_snapshot(),bars=1,tail_seconds=0.5)
        params,pcm=self.read(target)
        self.assertEqual((params.nchannels,params.sampwidth,params.framerate),(2,2,16000))
        self.assertEqual(params.nframes,40000)
        self.assertTrue(np.array_equal(pcm[:,0],pcm[:,1]))
        self.assertGreater(np.abs(pcm.astype(np.int32)).max(),0)
        self.assertEqual(result['frames'],params.nframes)
        self.assertTrue(result['readbackVerified'])
        self.assertIsNone(self.engine._stream)
        self.assertFalse(self.engine.playing)

    def test_pattern_changes_are_audible_and_not_a_fixed_demo(self):
        export=self.exporter().write_pattern_wav
        silent=self.folder/'silent.wav'; kick=self.folder/'kick.wav'; bass=self.folder/'bass.wav'
        export(silent,self.engine.pattern_snapshot(),bars=1,tail_seconds=0)
        self.engine.set_step(0,0,True)
        export(kick,self.engine.pattern_snapshot(),bars=1,tail_seconds=0)
        self.engine.send(EV_CLEAR); self.engine.set_step(6,0,True,note=45)
        export(bass,self.engine.pattern_snapshot(),bars=1,tail_seconds=0)
        self.assertFalse(self.read(silent)[1].any())
        self.assertFalse(np.array_equal(self.read(kick)[1],self.read(bass)[1]))

    def test_master_and_track_mute_apply_to_export(self):
        self.engine.set_step(0,0,True)
        self.engine.send(EV_MUTE,0,1)
        path=self.folder/'mute.wav'
        self.exporter().write_pattern_wav(path,self.engine.pattern_snapshot(),bars=1,tail_seconds=0)
        self.assertFalse(self.read(path)[1].any())
        self.engine.send(EV_MUTE,0,0); self.engine.send(EV_GAIN,-1,0)
        path=self.folder/'master-zero.wav'
        self.exporter().write_pattern_wav(path,self.engine.pattern_snapshot(),bars=1,tail_seconds=0)
        self.assertFalse(self.read(path)[1].any())

    def test_existing_file_is_preserved(self):
        path=self.folder/'existing.wav'; path.write_bytes(b'preserved-original')
        with self.assertRaises(FileExistsError):
            self.exporter().write_pattern_wav(path,self.engine.pattern_snapshot())
        self.assertEqual(path.read_bytes(),b'preserved-original')

    def test_cancel_before_export_creates_no_file(self):
        event=threading.Event(); event.set()
        module=self.exporter()
        with self.assertRaises(module.ExportCancelled):
            module.write_pattern_wav(self.folder/'cancel.wav',self.engine.pattern_snapshot(),cancel=event)
        self.assertEqual(list(self.folder.iterdir()),[])

    def test_cancel_during_render_leaves_no_published_file(self):
        event=threading.Event(); module=self.exporter()
        original=AudioEngine.render_block
        def render(engine,frames):
            value=original(engine,frames); event.set(); return value
        with patch.object(AudioEngine,'render_block',render):
            with self.assertRaises(module.ExportCancelled):
                module.write_pattern_wav(self.folder/'cancel.wav',self.engine.pattern_snapshot(),cancel=event)
        self.assertEqual(list(self.folder.iterdir()),[])

    def test_write_failure_never_publishes_destination(self):
        path=self.folder/'failed.wav'
        with patch('os.fsync',side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError):
                self.exporter().write_pattern_wav(path,self.engine.pattern_snapshot(),bars=1,tail_seconds=0)
        self.assertFalse(path.exists())

    def test_invalid_render_bounds_rejected_before_disk_changes(self):
        export=self.exporter().write_pattern_wav
        for kwargs in [{'bars':0},{'bars':17},{'bars':True},{'tail_seconds':-1},{'tail_seconds':float('nan')}]:
            with self.assertRaises(ValueError):export(self.folder/'bad.wav',self.engine.pattern_snapshot(),**kwargs)
        self.assertEqual(list(self.folder.iterdir()),[])

    def test_late_destination_collision_preserves_the_other_file(self):
        module=self.exporter(); target=self.folder/'race.wav'; rename=os.rename
        def collide(source,destination):
            target.write_bytes(b'other-file-created-before-publication')
            return rename(source,destination)
        with patch.object(module.os,'rename',side_effect=collide):
            with self.assertRaises(FileExistsError):
                module.write_pattern_wav(target,self.engine.pattern_snapshot(),bars=1,tail_seconds=0)
        self.assertEqual(target.read_bytes(),b'other-file-created-before-publication')

    def test_disk_readback_mismatch_is_not_published(self):
        target=self.folder/'corrupt.wav'; read=Path.read_bytes
        def mismatched(path):
            data=read(path)
            return data+b'fixture-mismatch' if path.suffix=='.wavtmp' else data
        with patch.object(Path,'read_bytes',mismatched):
            with self.assertRaisesRegex(OSError,'readback'):
                self.exporter().write_pattern_wav(target,self.engine.pattern_snapshot(),bars=1,tail_seconds=0)
        self.assertFalse(target.exists())


class ExportViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['QT_QPA_PLATFORM']='offscreen'
        from PyQt6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        from native_studio.music_daw_view import MusicDawView
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.jobs=[]
        outer=self
        class Bus:
            def submit(self,*args,**kwargs):outer.jobs.append((args,kwargs))
        self.start_guard=patch.object(AudioEngine,'start',side_effect=AssertionError('Audio output must remain idle'))
        self.start_guard.start(); self.addCleanup(self.start_guard.stop)
        self.view=MusicDawView(Bus(),AudioEngine(16000))
        self.addCleanup(self.view.close)
        self.addCleanup(self.view.shutdown)

    def picker(self,path):
        return patch('native_studio.music_daw_view.QFileDialog.getSaveFileName',return_value=(str(path), 'WAV audio (*.wav)'))

    def test_picker_cancel_does_not_queue_or_claim_an_export(self):
        with self.picker(''):self.view._export_master('WAV')
        self.assertEqual(self.jobs,[])
        self.assertFalse(self.view._wav_export_pending)
        self.assertNotIn('Saved and verified',self.view.chat_history.toPlainText())

    def test_button_queues_local_snapshot_at_displayed_tempo_then_confirms_real_file(self):
        path=self.folder/'current.wav'
        self.view.spin_bpm.setValue(100)
        with self.picker(path):self.view._export_master('WAV')
        self.assertTrue(self.view._wav_export_pending)
        self.assertFalse(self.view.btn_exp_wav.isEnabled())
        self.assertEqual(len(self.jobs),1)
        args,options=self.jobs[0]
        self.assertEqual(args[2].bpm,100)
        result=args[0](*args[1:],**{k:v for k,v in options.items() if k not in ('on_result','on_error')})
        self.assertTrue(path.is_file())
        options['on_result'](result)
        self.assertFalse(self.view._wav_export_pending)
        self.assertTrue(self.view.btn_exp_wav.isEnabled())
        self.assertIn('Saved and verified',self.view.chat_history.toPlainText())
        self.assertIsNone(self.view.engine._stream)

    def test_worker_failure_is_not_reported_as_saved(self):
        with self.picker(self.folder/'fail.wav'):self.view._export_master('WAV')
        self.jobs[0][1]['on_error']('OSError: fixture disk unavailable')
        self.assertIn('File was not saved',self.view.chat_history.toPlainText())
        self.assertNotIn('Saved and verified',self.view.chat_history.toPlainText())
        self.assertTrue(self.view.btn_exp_wav.isEnabled())

    def test_cancel_marks_only_its_worker_and_allows_retry_after_confirmation(self):
        with self.picker(self.folder/'cancel.wav'):self.view._export_master('WAV')
        event=self.jobs[0][1]['cancel']
        self.view._cancel_wav_export()
        self.assertTrue(event.is_set())
        self.assertTrue(self.view._wav_export_pending)
        self.jobs[0][1]['on_error']('ExportCancelled: cancelled')
        self.assertFalse(self.view._wav_export_pending)
        self.assertIn('Cancelled before',self.view.chat_history.toPlainText())

    def test_duplicate_click_does_not_queue_a_second_render(self):
        with self.picker(self.folder/'single.wav'):
            self.view._export_master('WAV'); self.view._export_master('WAV')
        self.assertEqual(len(self.jobs),1)

    def test_unconnected_mp4_does_not_claim_a_render_or_queue(self):
        with patch('native_studio.music_daw_view._safe_info_dialog') as info:
            self.view._export_master('MP4')
        self.assertIn('not connected',info.call_args.args[2])
        self.assertEqual(self.jobs,[])
        self.assertNotIn('Rendered project master',self.view.chat_history.toPlainText())


if __name__=='__main__':unittest.main()
