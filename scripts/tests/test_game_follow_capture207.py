"""Offline follow/holding frames; never reads a window, key or encoder."""
from __future__ import annotations

import importlib
from types import SimpleNamespace
import threading
import time
import unittest
from unittest.mock import Mock,patch


def window(hwnd=207,pid=900,title='Fixture game  ',created=123.):
    return SimpleNamespace(hwnd=hwnd,title=title,process=SimpleNamespace(pid=pid,create_time=created,exe='C:/Games/Fixture/Game.exe'),package_family='')


def decision(source=None,*,manual=False,reason='NO_VERIFIED_GAME'):
    key=None if source is None else ('window',source.hwnd,source.process.pid,source.process.create_time,source.process.exe,source.title,'')
    return SimpleNamespace(source=source,source_key=key,manual=manual,must_clear=True,reason=reason,manual_source=None)


class Capture:
    width=2;height=2;fps=30
    def __init__(self,source=None,value=1):
        source=source or window();self.hwnd=source.hwnd;self.pid=source.process.pid;self.title=source.title
        self.start=Mock(return_value={});self.read_frame=Mock(return_value=bytes([value])*16)
        self.stop=Mock(return_value=True)
    def metadata(self):return {'frame_available':True,'frames_received':1}


class GameFollowCaptureTests(unittest.TestCase):
    def setUp(self):
        self.m=importlib.import_module('backend.core.game_follow_capture')
        self.source=window();self.choice=decision(self.source);self.current=Capture(self.source)
        self.selector=Mock(return_value=self.choice);self.factory=Mock()
    def follower(self,**kwargs):
        result=self.m.FollowingWindowCapture(self.current,self.choice,self.selector,capture_factory=self.factory,poll_interval=0,identity_checker=lambda _:True,**kwargs)
        self.addCleanup(result.stop);return result
    def settled(self,follower):
        follower.read_frame()
        worker=getattr(follower,'_switcher',None)
        if worker is not None:worker.join(1)
        return follower.read_frame()

    def test_existing_verified_game_kept_without_reopening_or_desktop_capture(self):
        follower=self.follower();self.assertEqual(follower.read_frame(),b'\x01'*16)
        self.factory.assert_not_called();self.assertTrue(follower.metadata()['game_frame_verified'])
        self.assertEqual(follower.metadata()['capture_state'],'capturing')

    def test_lost_game_clears_old_provider_and_returns_labeled_holding_buffer(self):
        follower=self.follower();self.selector.return_value=decision()
        frame=follower.read_frame()
        self.assertEqual(frame,b'\x00\x00\x00\xff'*4)
        self.current.stop.assert_called();self.factory.assert_not_called()
        self.assertFalse(follower.metadata()['game_frame_verified'])
        self.assertEqual(follower.metadata()['capture_state'],'holding')
        self.assertFalse(follower.metadata()['game_frame_available'])

    def test_new_game_swaps_exact_identity_after_old_pixels_cleared(self):
        follower=self.follower();other=window(208,901,'Second game  ');new=Capture(other,2)
        self.selector.return_value=decision(other)
        def create(hwnd,pid,title,**kwargs):
            self.current.stop.assert_called()
            self.assertEqual(follower.metadata()['capture_state'],'holding')
            self.assertFalse(follower.metadata()['game_frame_available'])
            self.assertEqual((hwnd,pid,title),(208,901,'Second game  '))
            self.assertEqual(kwargs,{'fps':30,'width':2,'height':2})
            return new
        self.factory.side_effect=create
        self.assertEqual(self.settled(follower),b'\x02'*16)
        self.assertEqual(follower.metadata()['target_hwnd'],208)
        self.assertTrue(follower.metadata()['game_frame_verified'])

    def test_holding_reacquires_verified_game_without_an_encoder_reference(self):
        follower=self.follower();self.selector.return_value=decision();follower.read_frame()
        other=window(209,902,'Later game');self.selector.return_value=decision(other);self.factory.return_value=Capture(other,3)
        self.assertEqual(self.settled(follower),b'\x03'*16)
        self.assertEqual(follower.metadata()['capture_state'],'capturing')

    def test_changed_policy_during_new_first_frame_never_publishes_that_frame(self):
        follower=self.follower();other=window(208,901);new=Capture(other,2)
        self.selector.side_effect=[decision(other),decision()];self.factory.return_value=new
        self.assertEqual(self.settled(follower),b'\x00\x00\x00\xff'*4)
        new.stop.assert_called();self.assertFalse(follower.metadata()['game_frame_verified'])

    def test_bad_first_frame_or_provider_failure_holds_without_fallback(self):
        for failure in ('frame','start'):
            with self.subTest(failure=failure):
                follower=self.follower();other=window(208,901);new=Capture(other)
                if failure=='frame':new.read_frame.return_value=b'bad'
                else:new.start.side_effect=RuntimeError('fixture private credentials')
                self.selector.return_value=decision(other);self.factory.return_value=new
                self.assertEqual(self.settled(follower),b'\x00\x00\x00\xff'*4)
                new.stop.assert_called();self.assertNotIn('credentials',str(follower.metadata()))
                self.selector.reset_mock(side_effect=True);self.selector.return_value=self.choice

    def test_unconfirmed_old_cleanup_prevents_new_provider_accumulation(self):
        follower=self.follower();self.current.stop.return_value=False;self.selector.return_value=decision(window(208,901))
        self.assertEqual(follower.read_frame(),b'\x00\x00\x00\xff'*4)
        self.factory.assert_not_called();self.assertFalse(follower.stop(timeout=.01))
        self.current.stop.return_value=True;self.assertTrue(follower.stop(timeout=.2))

    def test_manual_window_is_explicit_and_not_reported_as_a_verified_game(self):
        follower=self.follower();browser=window(210,903,'Explicitly shared browser');new=Capture(browser,4)
        self.selector.return_value=decision(browser,manual=True);self.factory.return_value=new
        self.assertEqual(self.settled(follower),b'\x04'*16)
        self.assertTrue(follower.metadata()['manual']);self.assertFalse(follower.metadata()['game_frame_verified'])

    def test_manual_screen_decision_holds_without_opening_any_monitor(self):
        follower=self.follower();screen=decision(manual=True,reason='MANUAL_SCREEN_SELECTED')
        screen.source_key=('screen','display-1');screen.manual_source=SimpleNamespace(kind='screen',screen_id='display-1')
        self.selector.return_value=screen
        self.assertEqual(follower.read_frame(),b'\x00\x00\x00\xff'*4)
        self.factory.assert_not_called();self.assertFalse(follower.metadata()['game_frame_verified'])

    def test_stop_during_pending_start_rejects_late_game_frame(self):
        follower=self.follower();other=window(208,901);new=Capture(other,2)
        entered=threading.Event();release=threading.Event();frames=[];failures=[]
        def start(**_):entered.set();release.wait(1)
        new.start.side_effect=start;self.selector.return_value=decision(other);self.factory.return_value=new
        def read():
            try:frames.append(follower.read_frame())
            except self.m.CaptureUnavailable:failures.append('closed')
        self.assertEqual(follower.read_frame(),b'\x00\x00\x00\xff'*4)
        self.assertTrue(entered.wait(1));worker=follower._switcher
        try:self.assertFalse(follower.stop(timeout=.05))
        finally:release.set();worker.join(1)
        self.assertTrue(follower.stop(timeout=.2));new.stop.assert_called()
        self.assertFalse(follower.metadata()['game_frame_available'])

    def test_closed_capture_and_invalid_limits_never_return_holding_as_game(self):
        follower=self.follower();self.assertTrue(follower.stop())
        with self.assertRaises(self.m.CaptureUnavailable):follower.read_frame()
        self.assertFalse(follower.metadata()['game_frame_verified'])
        with self.assertRaises(ValueError):self.m.FollowingWindowCapture(self.current,self.choice,self.selector,poll_interval=-1)

    def test_initial_capture_identity_must_match_pinned_policy_decision(self):
        for name,value in [('hwnd',208),('pid',901),('title','Other game')]:
            with self.subTest(field=name):
                current=Capture(self.source);setattr(current,name,value)
                with self.assertRaises(ValueError):self.m.FollowingWindowCapture(current,self.choice,self.selector)
                current.stop.assert_not_called()

    def test_initial_no_game_starts_explicit_holding_and_reacquires(self):
        self.selector.return_value=decision()
        follower=self.m.FollowingWindowCapture(None,None,self.selector,width=2,height=2,fps=30,
                                               capture_factory=self.factory,poll_interval=0,identity_checker=lambda _:True)
        self.addCleanup(follower.stop)
        self.assertEqual(follower.start()['capture_state'],'holding')
        self.assertEqual(follower.read_frame(),b'\x00\x00\x00\xff'*4)
        self.selector.return_value=self.choice;self.factory.return_value=self.current
        self.assertEqual(self.settled(follower),b'\x01'*16)
        self.assertTrue(follower.metadata()['game_frame_verified'])

    def test_reused_process_or_changed_executable_is_held_before_pixels_publish(self):
        follower=self.follower();follower._identity_checker=Mock(return_value=False)
        self.assertEqual(self.settled(follower),b'\x00\x00\x00\xff'*4)
        self.assertFalse(follower.metadata()['game_frame_verified']);self.current.stop.assert_called()

    def test_manual_intent_invalidation_during_pending_start_never_publishes_old_choice(self):
        follower=self.follower();other=window(208,901);new=Capture(other,2)
        self.selector.return_value=decision(other);self.factory.return_value=new
        new.start.side_effect=lambda **_:follower.invalidate('SOURCE_INTENT_CHANGED',manual=True)
        self.assertEqual(self.settled(follower),b'\x00\x00\x00\xff'*4)
        new.stop.assert_called();self.assertFalse(follower.metadata()['game_frame_verified'])

    def test_waiting_for_new_surface_does_not_block_holding_frames(self):
        follower=self.follower();other=window(208,901);new=Capture(other,2)
        entered=threading.Event();release=threading.Event();returned=threading.Event()
        def start(**_):entered.set();release.wait(1)
        new.start.side_effect=start;self.selector.return_value=decision(other);self.factory.return_value=new
        thread=threading.Thread(target=lambda:(follower.read_frame(),returned.set()));thread.start()
        self.assertTrue(entered.wait(1))
        try:
            self.assertTrue(returned.wait(.1),'Writer must receive holding while capture startup waits')
            self.assertEqual(follower.read_frame(),b'\x00\x00\x00\xff'*4)
        finally:
            release.set();thread.join(1)
            worker=getattr(follower,'_switcher',None)
            if worker is not None:worker.join(1)

    def test_stop_rechecks_capture_created_after_initial_cleanup_snapshot(self):
        follower=self.follower();other=window(208,901);new=Capture(other,2);new.stop.return_value=False
        entered=threading.Event();release=threading.Event();results=[]
        def factory(*_,**__):entered.set();release.wait(1);return new
        self.selector.return_value=decision(other);self.factory.side_effect=factory
        follower.read_frame();self.assertTrue(entered.wait(1))
        stopper=threading.Thread(target=lambda:results.append(follower.stop(timeout=.5)));stopper.start()
        deadline=time.monotonic()+.2
        while follower.metadata()['capture_state']!='closed' and time.monotonic()<deadline:time.sleep(.001)
        release.set();stopper.join(1)
        self.assertEqual(results,[False],'A late-created unconfirmed provider remains owned')
        new.stop.return_value=True;self.assertTrue(follower.stop(timeout=.2))

    def test_new_provider_not_opened_when_pinned_process_already_changed(self):
        follower=self.follower();self.selector.return_value=decision(window(208,901))
        follower._identity_checker=lambda identity:identity.pid!=901
        self.assertEqual(self.settled(follower),b'\x00\x00\x00\xff'*4)
        self.factory.assert_not_called()


if __name__=='__main__':unittest.main()
