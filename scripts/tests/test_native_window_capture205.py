"""Synthetic WGC callbacks only; no actual window/camera/GPU capture."""
from __future__ import annotations
import importlib
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import numpy as np


class NativeWindowCaptureTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('backend.core.native_window_capture')
        self.identity={'exists':True,'visible':True,'minimized':False,'pid':900,'title':'Fixture  '}
        self.buffer=np.arange(32,dtype=np.uint8).reshape(2,4,4)
        owner=self
        class FakeCapture:
            instances=[]
            def __init__(self,**kwargs):
                self.kwargs=kwargs;self.handlers={};self.control=SimpleNamespace(stop=Mock(),is_finished=lambda:False)
                self.internal=SimpleNamespace(stop=Mock());FakeCapture.instances.append(self)
            def event(self,handler):self.handlers[handler.__name__]=handler;return handler
            def emit(self,buffer=None):
                data=owner.buffer if buffer is None else buffer
                self.handlers['on_frame_arrived'](SimpleNamespace(frame_buffer=data,width=data.shape[1],height=data.shape[0],timespan=1),self.internal)
            def start_free_threaded(self):
                self.emit();return self.control
        self.factory=FakeCapture
        self.identity_patch=patch.object(self.module,'_read_window_identity',side_effect=lambda hwnd:dict(self.identity))
        self.factory_patch=patch.object(self.module,'_capture_class',return_value=self.factory)
        self.identity_patch.start();self.factory_patch.start()
        self.addCleanup(self.identity_patch.stop);self.addCleanup(self.factory_patch.stop)

    def source(self,**kwargs):
        source=self.module.NativeWindowCapture(205,900,'Fixture  ',fps=30,**kwargs)
        self.addCleanup(source.stop)
        return source

    def test_targets_only_exact_hwnd_with_bgra_owned_latest_frame(self):
        source=self.source();meta=source.start(timeout=0.5)
        native=self.factory.instances[0]
        self.assertEqual(native.kwargs['window_hwnd'],205)
        self.assertIsNone(native.kwargs['monitor_index']);self.assertIsNone(native.kwargs['window_name'])
        self.assertEqual(source.width,4);self.assertEqual(source.height,2)
        expected=self.buffer.tobytes();self.buffer[:]=0
        self.assertEqual(source.read_frame(),expected)
        self.assertEqual(meta['pixel_format'],'bgra')
        self.assertEqual(meta['provider'],'windows_graphics_capture_hwnd')

    def test_wrong_pid_title_minimized_or_closed_holds_before_provider_start(self):
        for change in ({'pid':901},{'title':'Other'},{'minimized':True},{'exists':False}):
            with self.subTest(change=change):
                original=dict(self.identity);self.identity.update(change)
                with self.assertRaises(self.module.CaptureUnavailable):self.source().start(timeout=0.1)
                self.identity=original
        self.assertEqual(self.factory.instances,[])

    def test_title_whitespace_remains_part_of_identity(self):
        self.identity['title']='Fixture'
        with self.assertRaises(self.module.CaptureUnavailable):self.source().start(timeout=0.1)

    def test_identity_change_after_start_discards_previous_pixels(self):
        source=self.source();source.start(timeout=0.5);self.identity['pid']=901
        with self.assertRaises(self.module.CaptureUnavailable):source.read_frame()
        self.assertFalse(source.metadata()['frame_available'])

    def test_capture_closed_event_discards_pixels_and_cannot_restart(self):
        source=self.source();source.start(timeout=0.5)
        self.factory.instances[0].handlers['on_closed']()
        with self.assertRaises(self.module.CaptureUnavailable):source.read_frame()
        with self.assertRaises(self.module.CaptureUnavailable):source.start()
        self.assertFalse(source.metadata()['frame_available'])
        self.assertEqual(len(self.factory.instances),1)

    def test_invalid_frame_shape_or_dtype_never_becomes_available(self):
        for bad in (np.zeros((2,4,3),np.uint8),np.zeros((2,4,4),np.float32)):
            with self.subTest(dtype=str(bad.dtype),shape=bad.shape):
                self.buffer=bad;source=self.source()
                with self.assertRaises(self.module.CaptureUnavailable):source.start(timeout=0.2)
                self.assertFalse(source.metadata()['frame_available'])
                self.assertTrue(self.factory.instances[-1].internal.stop.called)

    def test_fixed_output_dimensions_survive_source_resize(self):
        source=self.source(width=2,height=2);source.start(timeout=0.5)
        self.assertEqual(len(source.read_frame()),16)
        self.factory.instances[0].emit(np.zeros((4,8,4),np.uint8))
        self.assertEqual(len(source.read_frame()),16)
        self.assertEqual((source.width,source.height),(2,2))

    def test_latest_frame_replaces_previous_without_queue_growth(self):
        source=self.source();source.start(timeout=0.5)
        for value in range(10):self.factory.instances[0].emit(np.full((2,4,4),value,np.uint8))
        self.assertEqual(source.read_frame(),bytes([9])*32)
        self.assertEqual(source.metadata()['buffered_frames'],1)

    def test_jpeg_snapshot_is_bounded_and_rejects_closed_capture(self):
        source=self.source();source.start(timeout=0.5)
        jpeg=source.snapshot_jpeg(quality=70,max_side=1280,max_bytes=2048)
        self.assertTrue(jpeg.startswith(b'\xff\xd8'))
        self.assertLessEqual(len(jpeg),2048)
        with self.assertRaises(self.module.CaptureUnavailable):source.snapshot_jpeg(max_bytes=256)
        self.assertTrue(source.metadata()['frame_available'])
        source.stop()
        with self.assertRaises(self.module.CaptureUnavailable):source.snapshot_jpeg()

    def test_start_and_stop_are_idempotent(self):
        source=self.source();source.start(timeout=0.5);source.start(timeout=0.5)
        self.assertEqual(len(self.factory.instances),1)
        self.assertTrue(source.stop(timeout=0.5));self.assertTrue(source.stop(timeout=0.5))
        self.factory.instances[0].control.stop.assert_called_once_with()
        with self.assertRaises(self.module.CaptureUnavailable):source.read_frame()

    def test_frame_arriving_after_stop_is_discarded(self):
        source=self.source();source.start(timeout=0.5);before=source.metadata()['frames_received']
        self.assertTrue(source.stop(timeout=0.5))
        native=self.factory.instances[0];native.emit()
        self.assertEqual(source.metadata()['frames_received'],before)
        self.assertFalse(source.metadata()['frame_available']);native.internal.stop.assert_called()

    def test_blocked_native_stop_returns_unconfirmed_within_caller_deadline(self):
        source=self.source();source.start(timeout=0.5)
        release=threading.Event()
        self.addCleanup(release.set)
        native=self.factory.instances[0]
        native.control.stop=Mock(side_effect=lambda:release.wait(1))
        self.assertFalse(source.stop(timeout=0.01))
        self.assertFalse(source.metadata()['frame_available'])
        release.set();self.assertTrue(source.stop(timeout=0.5))
        native.control.stop.assert_called_once_with()

    def test_unavailable_dependency_is_held_without_another_capture_backend(self):
        with patch.object(self.module,'_capture_class',side_effect=ImportError('fixture package missing')):
            with self.assertRaises(self.module.CaptureUnavailable):self.source().start(timeout=0.2)
        self.assertFalse(self.factory.instances)

    def test_no_first_frame_times_out_and_stops_only_own_session(self):
        with patch.object(self.factory,'start_free_threaded',lambda native:native.control):
            source=self.source()
            with self.assertRaises(self.module.CaptureUnavailable):source.start(timeout=0.05)
        self.assertTrue(source.stop(timeout=0.5))
        self.assertFalse(source.metadata()['frame_available'])

    def test_invalid_identity_and_dimensions_are_rejected(self):
        for hwnd,pid,title in ((True,900,'Fixture  '),(0,900,'Fixture  '),(205,True,'Fixture  '),(205,900,'')):
            with self.subTest(hwnd=hwnd,pid=pid):
                with self.assertRaises(ValueError):self.module.NativeWindowCapture(hwnd,pid,title)
        for dims in ({'width':2},{'width':0,'height':2},{'width':99999,'height':2}):
            with self.assertRaises(ValueError):self.source(**dims)


if __name__=='__main__':unittest.main()
