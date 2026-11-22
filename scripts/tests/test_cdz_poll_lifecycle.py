"""Real disposable CDZ polling lifecycle; event barriers, no live sources."""
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cdz_scan_composition import temporary_watcher, synthetic_ledger
from database import cdz_audit_db as cdz


class CDZPollLifecycleTests(unittest.TestCase):
    def test_stop_preserves_inflight_writer_and_refuses_restart_until_drain(self):
        with temporary_watcher() as (_, source, store, watcher):
            watcher.poll_interval = 3600
            first = source / 'first_audit_ledger.json'
            first.write_text(json.dumps(synthetic_ledger()), encoding='utf-8')
            entered = threading.Event()
            release = threading.Event()
            completed = threading.Event()
            original_submit = store.submit
            original_scan = watcher.scan_now

            def submit(callback):
                def blocked(connection, cancel_event):
                    entered.set()
                    if not release.wait(5):
                        raise RuntimeError('Synthetic writer barrier timed out')
                    return callback(connection, cancel_event)
                return original_submit(blocked)

            def scan():
                result = original_scan()
                completed.set()
                return result

            try:
                with patch.object(store, 'submit', side_effect=submit), \
                     patch.object(watcher, 'scan_now', side_effect=scan):
                    self.assertIs(watcher.start(), True)
                    thread = watcher._thread
                    self.assertTrue(entered.wait(3), 'Polling never reached the real writer')
                    self.assertIs(watcher.start(), False)
                    self.assertIs(watcher._thread, thread)
                    self.assertIs(watcher.stop(timeout=0), False)
                    status = watcher.get_status()
                    self.assertIs(status['running'], True)
                    self.assertIs(status['stopping'], True)
                    self.assertIs(watcher.start(), False)
                    self.assertIs(watcher._thread, thread)
                    release.set()
                    self.assertTrue(completed.wait(3), 'Released ingest did not complete')
                    self.assertIs(watcher.stop(timeout=3), True)
                    self.assertFalse(thread.is_alive())
                self.assertEqual(cdz.get_cdz_summary(store=store)['total_blocks'], 1)
                self.assertEqual(watcher.new_blocks_ingested, 1)
                self.assertIs(watcher.get_status()['running'], False)
                self.assertIs(watcher.get_status()['stopping'], False)

                second = source / 'second_audit_ledger.json'
                payload = synthetic_ledger()
                payload['records'][0].update(index=2, hash='hash-2', full_hash='full-2')
                second.write_text(json.dumps(payload), encoding='utf-8')
                completed.clear()
                with patch.object(watcher, 'scan_now', side_effect=scan):
                    self.assertIs(watcher.start(), True)
                    restarted = watcher._thread
                    self.assertIsNot(restarted, thread)
                    self.assertTrue(completed.wait(3))
                    self.assertIs(watcher.start(), False)
                    start_stop = time.monotonic()
                    self.assertIs(watcher.stop(timeout=2), True)
                    self.assertLess(time.monotonic() - start_stop, 2)
                    self.assertFalse(restarted.is_alive())
                self.assertEqual(cdz.get_cdz_summary(store=store)['total_blocks'], 2)
                self.assertEqual(watcher.new_blocks_ingested, 2)
                self.assertEqual(watcher.files_tracked, 2)
                repeated = watcher.scan_now()
                self.assertEqual(repeated['new_blocks_ingested'], 0)
                self.assertEqual(watcher.new_blocks_ingested, 2)
            finally:
                release.set()
                watcher.stop(timeout=5)
                if watcher._thread is not None:
                    self.assertFalse(watcher._thread.is_alive(), 'Owned poll thread leaked')

    def test_idle_long_interval_poll_wakes_for_bounded_stop(self):
        with temporary_watcher() as (_, _, _, watcher):
            watcher.poll_interval = 3600
            scanned = threading.Event()
            original_scan = watcher.scan_now

            def scan():
                result = original_scan()
                scanned.set()
                return result

            try:
                with patch.object(watcher, 'scan_now', side_effect=scan):
                    self.assertIs(watcher.start(), True)
                    thread = watcher._thread
                    self.assertTrue(scanned.wait(3))
                    self.assertIs(watcher.start(), False)
                    self.assertIs(watcher._thread, thread)
                    started = time.monotonic()
                    self.assertIs(watcher.stop(timeout=2), True)
                    self.assertLess(time.monotonic() - started, 2)
                    self.assertFalse(thread.is_alive())
                    self.assertEqual(watcher.total_scans, 1)
                    self.assertIs(watcher.stop(timeout=0), True)
            finally:
                watcher.stop(timeout=5)
                if watcher._thread is not None:
                    self.assertFalse(watcher._thread.is_alive(), 'Owned idle poll thread leaked')


if __name__ == '__main__':
    unittest.main(verbosity=2)
