"""Owned synthetic sampler threads only; no Windows enumeration/capture or services."""
from __future__ import annotations

from dataclasses import replace
import importlib
import threading
import time
import unittest
from unittest.mock import Mock

from backend.core.game_capture_selection import (
    ManualSource, ProcessIdentity, SelectionDecision, WindowEvidence,
)


def window(hwnd=207,pid=900,created=123.,exe=r'C:\Games\Fixture\Game.exe',title='Fixture  '):
    return WindowEvidence(hwnd,title,ProcessIdentity(pid,created,exe),1280,720)


def decision(source=None,manual=False):
    return SelectionDecision(source,'MANUAL_WINDOW' if manual else 'VERIFIED_GAME',True,manual)


class GameSelectionSamplerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=importlib.import_module('backend.core.game_selection_sampler')

    def sampler(self,adapter,**kwargs):
        sampler=self.m.GameSelectionSampler(adapter,interval=.02,max_age=.5,**kwargs)
        self.addCleanup(lambda:sampler.stop(timeout=.5))
        return sampler

    def wait_for(self,predicate,timeout=1.):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if predicate():return
            threading.Event().wait(.001)
        self.fail('Synthetic sampler result did not arrive')

    def test_construction_and_cached_reads_never_start_discovery(self):
        adapter=Mock();sampler=self.sampler(adapter)
        self.assertIsNone(sampler.latest().source)
        self.assertEqual(sampler.latest().reason,'SAMPLER_NOT_STARTED')
        adapter.decide.assert_not_called()

    def test_blocked_discovery_never_blocks_video_or_control_reads(self):
        entered=threading.Event();release=threading.Event()
        def read(**_):entered.set();release.wait(2);return decision(window())
        sampler=self.sampler(Mock(decide=Mock(side_effect=read),cached_windows=()))
        try:
            self.assertTrue(sampler.start());self.assertTrue(entered.wait(1))
            begin=time.perf_counter()
            for _ in range(200):self.assertIsNone(sampler.latest().source)
            self.assertLess(time.perf_counter()-begin,.2)
            self.assertIsNone(sampler.resolve_window(207,900,'Fixture  '))
            self.assertFalse(sampler.stop(timeout=.01))
        finally:release.set();self.assertTrue(sampler.stop(timeout=.5))

    def test_only_one_owned_worker_and_stopped_blocked_worker_cannot_be_replaced(self):
        entered=threading.Event();release=threading.Event();calls=[]
        def read(**_):calls.append(threading.get_ident());entered.set();release.wait(2);return decision()
        sampler=self.sampler(Mock(decide=Mock(side_effect=read),cached_windows=()))
        try:
            sampler.start();self.assertTrue(entered.wait(1))
            for _ in range(10):self.assertTrue(sampler.start())
            self.assertEqual(len(calls),1)
            self.assertFalse(sampler.stop(timeout=.01));self.assertFalse(sampler.start())
            self.assertEqual(len(calls),1)
        finally:release.set();self.assertTrue(sampler.stop(timeout=.5))

    def test_fresh_decision_and_exact_cached_window_resolution(self):
        source=window();adapter=Mock(decide=Mock(return_value=decision(source)),cached_windows=(source,))
        sampler=self.sampler(adapter);sampler.start();self.wait_for(lambda:sampler.latest().source is not None)
        self.assertEqual(sampler.resolve_window(207,900,'Fixture  '),source)
        for args in ((207,900,'Fixture'),(207,901,'Fixture  '),(208,900,'Fixture  '),(True,900,'Fixture  ')):
            self.assertIsNone(sampler.resolve_window(*args))

    def test_cache_age_uses_sample_start_so_late_discovery_is_never_freshened(self):
        clock=[10.];entered=threading.Event();release=threading.Event();source=window()
        def read(**_):entered.set();release.wait(2);return decision(source)
        sampler=self.sampler(Mock(decide=Mock(side_effect=read),cached_windows=(source,)),clock=lambda:clock[0])
        try:
            sampler.start();self.assertTrue(entered.wait(1));clock[0]=11.;release.set()
            self.wait_for(lambda:sampler.status()['samples_completed']>0)
            self.assertIsNone(sampler.latest().source)
            self.assertEqual(sampler.latest().reason,'SAMPLER_STALE')
            self.assertIsNone(sampler.resolve_window(207,900,'Fixture  '))
        finally:release.set()

    def test_fresh_cache_expires_and_clears_previous_source_without_waiting_for_worker(self):
        clock=[10.];source=window()
        sampler=self.sampler(Mock(decide=Mock(return_value=decision(source)),cached_windows=(source,)),clock=lambda:clock[0])
        sampler.start();self.wait_for(lambda:sampler.latest().source is not None)
        prior=sampler.latest();clock[0]=10.6
        result=sampler.latest(previous=prior)
        self.assertIsNone(result.source);self.assertTrue(result.must_clear)
        self.assertEqual(result.reason,'SAMPLER_STALE')

    def test_intent_change_immediately_holds_and_discards_old_inflight_result(self):
        game=window();browser=window(208,901,exe=r'C:\Browser\chrome.exe',title='Shared browser')
        manual=ManualSource('window',window=browser);entered=threading.Event();release=threading.Event()
        def read(**kwargs):
            if kwargs['manual'] is None:
                entered.set();release.wait(2);return decision(game)
            return decision(browser,True)
        sampler=self.sampler(Mock(decide=Mock(side_effect=read),cached_windows=(game,browser)))
        try:
            sampler.start();self.assertTrue(entered.wait(1))
            held=sampler.latest(manual=manual)
            self.assertIsNone(held.source);self.assertTrue(held.manual)
            self.assertEqual(held.reason,'SAMPLER_INTENT_PENDING')
            release.set();self.wait_for(lambda:sampler.latest().source==browser)
            self.assertTrue(sampler.latest().manual)
        finally:release.set()

    def test_repeated_equivalent_intent_and_consumer_previous_do_not_starve_samples(self):
        browser=window(208,901,exe=r'C:\Browser\chrome.exe',title='Shared browser');manual=ManualSource('window',window=browser)
        sampler=self.sampler(Mock(decide=Mock(return_value=decision(browser,True)),cached_windows=(browser,)))
        sampler.set_intent(manual=manual);sampler.start();self.wait_for(lambda:sampler.latest().source is not None)
        generation=sampler.status()['intent_generation']
        for i in range(20):
            equivalent=ManualSource('window',window=replace(browser,width=640+i))
            self.assertEqual(sampler.latest(manual=equivalent,previous=decision()).source,browser)
        self.assertEqual(sampler.status()['intent_generation'],generation)

    def test_explicit_none_releases_manual_intent_and_returns_pending_until_revalidated(self):
        browser=window(208,901,exe=r'C:\Browser\chrome.exe');game=window()
        adapter=Mock(decide=Mock(side_effect=lambda **kw:decision(browser,True) if kw['manual'] else decision(game)),cached_windows=(browser,game))
        sampler=self.sampler(adapter);sampler.latest(manual=ManualSource('window',window=browser));sampler.start()
        self.wait_for(lambda:sampler.latest().source==browser)
        self.assertIsNone(sampler.latest(manual=None).source)
        self.wait_for(lambda:sampler.latest().source==game)

    def test_loss_is_published_as_holding_without_retaining_old_source(self):
        source=window();lost=threading.Event()
        adapter=Mock(decide=Mock(side_effect=lambda **_:decision() if lost.is_set() else decision(source)),cached_windows=(source,))
        sampler=self.sampler(adapter);sampler.start();self.wait_for(lambda:sampler.latest().source==source)
        lost.set();self.wait_for(lambda:sampler.latest().source is None)
        self.assertTrue(sampler.latest(previous=decision(source)).must_clear)

    def test_adapter_exception_or_invalid_result_has_fixed_nonsecret_hold(self):
        for failure in (RuntimeError('secret-not-for-status'),object()):
            with self.subTest(failure=type(failure).__name__):
                adapter=Mock(cached_windows=())
                if isinstance(failure,Exception):adapter.decide.side_effect=failure
                else:adapter.decide.return_value=failure
                sampler=self.sampler(adapter);sampler.start()
                self.wait_for(lambda:sampler.status()['samples_completed']>0)
                self.assertIsNone(sampler.latest().source)
                self.assertEqual(sampler.latest().reason,'SAMPLER_EVIDENCE_UNAVAILABLE')
                self.assertNotIn('secret',str(sampler.status()))
                self.assertTrue(sampler.stop(timeout=.5))

    def test_stop_invalidates_cache_and_late_success_cannot_resurrect_selection(self):
        entered=threading.Event();release=threading.Event()
        def read(**_):entered.set();release.wait(2);return decision(window())
        sampler=self.sampler(Mock(decide=Mock(side_effect=read),cached_windows=()))
        sampler.start();self.assertTrue(entered.wait(1));self.assertFalse(sampler.stop(timeout=.01))
        release.set();self.assertTrue(sampler.stop(timeout=.5))
        self.assertIsNone(sampler.latest().source);self.assertEqual(sampler.latest().reason,'SAMPLER_STOPPED')
        self.assertFalse(sampler.start())

    def test_wrong_manual_identity_from_adapter_is_held_never_published(self):
        requested=window(208,901,exe=r'C:\Browser\chrome.exe',title='Shared')
        wrong=window();adapter=Mock(decide=Mock(return_value=decision(wrong,True)),cached_windows=(wrong,requested))
        sampler=self.sampler(adapter);sampler.set_intent(manual=ManualSource('window',window=requested));sampler.start()
        self.wait_for(lambda:sampler.status()['samples_completed']>0)
        self.assertIsNone(sampler.latest().source)
        self.assertEqual(sampler.latest().reason,'SAMPLER_EVIDENCE_UNAVAILABLE')

    def test_manual_screen_intent_never_accepts_an_adapter_window_fallback(self):
        adapter=Mock(decide=Mock(return_value=decision(window(),True)),cached_windows=())
        sampler=self.sampler(adapter);sampler.set_intent(manual=ManualSource('screen',screen_id='display-1'));sampler.start()
        self.wait_for(lambda:sampler.status()['samples_completed']>0)
        self.assertIsNone(sampler.latest().source)

    def test_equivalent_source_recomputes_must_clear_against_consumer_identity(self):
        source=window();sampler=self.sampler(Mock(decide=Mock(return_value=decision(source)),cached_windows=(source,)))
        sampler.start();self.wait_for(lambda:sampler.latest().source is not None)
        self.assertFalse(sampler.latest(previous=decision(source)).must_clear)
        self.assertTrue(sampler.latest(previous=decision(window(created=124.))).must_clear)

    def test_identity_pins_include_recycled_pid_exe_and_raw_title(self):
        source=window();state=[source]
        adapter=Mock(decide=Mock(side_effect=lambda **_:decision(state[0])),cached_windows=(source,))
        sampler=self.sampler(adapter);sampler.start();self.wait_for(lambda:sampler.latest().source is not None)
        previous=sampler.latest()
        for changed in (window(created=124.),window(exe=r'C:\Games\Fixture\New.exe'),window(title='Fixture')):
            state[0]=changed;self.wait_for(lambda:sampler.latest().source==changed)
            self.assertTrue(sampler.latest(previous=previous).must_clear);previous=sampler.latest()

    def test_clock_rollback_and_nonfinite_values_hold_instead_of_extending_freshness(self):
        clock=[10.];sampler=self.sampler(Mock(decide=Mock(return_value=decision(window())),cached_windows=()),clock=lambda:clock[0])
        sampler.start();self.wait_for(lambda:sampler.latest().source is not None)
        for value in (9.,float('nan'),float('inf')):
            clock[0]=value;self.assertIsNone(sampler.latest().source)

    def test_configuration_bounds_and_stop_budget_reject_invalid_values(self):
        for changes in ({'interval':0},{'max_age':float('inf')},{'max_age':0},{'interval':float('nan')}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):self.m.GameSelectionSampler(Mock(),**changes)
        sampler=self.sampler(Mock())
        with self.assertRaises(ValueError):sampler.stop(timeout=float('inf'))


if __name__=='__main__':unittest.main()
