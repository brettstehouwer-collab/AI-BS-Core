"""Synthetic native health UI fixtures; never open operational databases or hardware."""
import hashlib
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtWidgets import QApplication
from native_studio import system_health_view as subject


class Probe:
    def __init__(self, data):self.data=data
    def sample(self):return dict(self.data)


class Bus:
    def __init__(self):self.jobs=[]
    def submit(self, fn, *args, **kwargs):self.jobs.append((fn,args,kwargs))


class NativeHealthTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/'producer/system_logs.db'
        self.path_patch=patch.object(subject,'_LOG_DB_PATH',self.db)
        self.path_patch.start();self.addCleanup(self.path_patch.stop)
        self.bus=Bus()
        self.probe=Probe({'detected':False,'error':'fixture-unavailable'})

    def create_log(self, rows=()):
        self.db.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute('CREATE TABLE logs (id INTEGER PRIMARY KEY,timestamp TEXT,level TEXT,name TEXT,message TEXT)')
            conn.executemany('INSERT INTO logs VALUES (?,?,?,?,?)',rows)
            conn.commit()
        self.assert_integrity()

    def assert_integrity(self):
        with closing(sqlite3.connect(self.db.as_uri()+'?mode=ro',uri=True)) as conn:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchall(),[('ok',)])

    def view(self):
        view=subject.SystemHealthNativeView(self.bus,self.probe)
        view.timer.stop()
        self.addCleanup(view.deleteLater)
        return view

    def test_missing_log_source_does_not_create_directories_database_or_seed_events(self):
        try:subject._ensure_log_db().close()
        except (OSError,sqlite3.DatabaseError):pass
        self.assertFalse(self.db.parent.exists())

    def test_opening_empty_producer_log_preserves_exact_bytes_and_empty_history(self):
        self.create_log();before=self.db.read_bytes();view=self.view()
        self.assertEqual(view.table.rowCount(),0)
        self.assertEqual(self.db.read_bytes(),before)
        self.assertNotIn('RTX 4090',view.console.toPlainText())
        self.assert_integrity()

    def test_producer_connection_is_read_only(self):
        self.create_log();before=hashlib.sha256(self.db.read_bytes()).hexdigest()
        conn=subject._ensure_log_db()
        try:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO logs VALUES (100,'fixture','INFO','fixture','must not write')")
        finally:conn.close()
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(),before)
        self.assert_integrity()

    def test_real_gpu_probe_schema_preserves_measured_zero_values(self):
        self.create_log()
        self.probe.data={'detected':True,'name':'Fixture GPU','temp_c':0,'util_pct':0,'vram_total_gb':8,'vram_used_gb':0}
        view=self.view()
        self.assertIn('Fixture GPU',view.lbl_gpu_device.text())
        self.assertIn('0°C',view.lbl_gpu_temp.text())
        self.assertIn('0%',view.lbl_gpu_load.text())
        self.assertIn('0.00 GB',view.lbl_vram_alloc.text())
        self.assertNotIn('Llama',view.lbl_vram_alloc.text())
        self.assertEqual(view.vram_meter.value(),0)

    def test_unavailable_probe_and_unchecked_ports_never_claim_observations(self):
        self.create_log();view=self.view()
        for label in [view.lbl_gpu_device,view.lbl_gpu_temp,view.lbl_gpu_load,view.lbl_vram_alloc,view.lbl_vram_free]:
            self.assertIn('unavailable',label.text().lower())
        self.assertNotIn('ONLINE',view.lbl_ollama_status.text())
        self.assertNotIn('ACTIVE',view.lbl_comfy_status.text())

    def test_lost_probe_clears_prior_measured_labels(self):
        self.create_log();self.probe.data={'detected':True,'name':'Fixture GPU','temp_c':20,'util_pct':12,'vram_total_gb':8,'vram_used_gb':1}
        view=self.view();self.probe.data={'detected':False};view._poll_live_updates()
        self.assertIn('unavailable',view.lbl_gpu_device.text().lower())
        self.assertIn('unavailable',view.lbl_vram_alloc.text().lower())

    def test_log_markup_is_displayed_as_literal_data_not_interpreted_html(self):
        literal='<b>literal fixture</b>'
        self.create_log([(1,'2026-10-31T00:00:00Z','INFO','fixture',literal)])
        before=self.db.read_bytes();view=self.view()
        self.assertIn(literal,view.console.toPlainText())
        self.assertEqual(view.table.item(0,3).text(),literal)
        self.assertEqual(self.db.read_bytes(),before);self.assert_integrity()

    def test_missing_log_source_has_visible_unavailable_states_without_new_database(self):
        view=self.view()
        self.assertIn('unavailable',view.lbl_event_count.text().lower())
        self.assertIn('unavailable',view.lbl_page_info.text().lower())
        self.assertFalse(self.db.exists())

    def test_orphan_inspection_is_dry_run_and_does_not_claim_unobserved_host_health(self):
        self.create_log();view=self.view()
        with patch('native_studio.service_orchestrator.sweep_zombie_nodes_native',return_value={'dry_run':True,'terminated_count':0,'actions':[]}) as audit:
            view._sweep_zombies();fn,args,kwargs=self.bus.jobs[-1];result=fn(*args)
            audit.assert_called_once_with(dry_run=True)
            kwargs['on_result'](result)
        self.assertNotIn('100% clean',view.console.toPlainText())

    def test_live_preview_is_bounded_without_deleting_producer_history(self):
        self.create_log([(1,'fixture-time','INFO','fixture','preserved-record')])
        before=self.db.read_bytes();view=self.view()
        self.assertEqual(view.console.document().maximumBlockCount(),2000)
        view.console.append('preview-first')
        for index in range(2001):view.console.append('preview-'+str(index))
        self.assertLessEqual(view.console.document().blockCount(),2000)
        self.assertNotIn('preview-first',view.console.toPlainText())
        self.assertIn('preview-2000',view.console.toPlainText())
        self.assertEqual(self.db.read_bytes(),before);self.assert_integrity()

    def test_connection_progress_budget_interrupts_large_query_on_fixture_only(self):
        self.create_log();before=self.db.read_bytes()
        # Deterministic clock expiry: no wall-clock sleep or operational database.
        with patch('time.monotonic',side_effect=[0.0,1.0]):
            with closing(subject._ensure_log_db()) as conn:
                with self.assertRaisesRegex(sqlite3.OperationalError,'interrupt'):
                    conn.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<10000) SELECT SUM(x) FROM n').fetchone()
        self.assertEqual(self.db.read_bytes(),before);self.assert_integrity()

    def test_connection_does_not_trust_schema_code(self):
        self.create_log()
        with closing(subject._ensure_log_db()) as conn:
            self.assertEqual(conn.execute('PRAGMA trusted_schema').fetchone()[0],0)

    def test_connection_setup_error_closes_handle_before_propagating(self):
        conn=Mock();conn.execute.side_effect=sqlite3.OperationalError('fixture-only')
        with patch.object(subject.sqlite3,'connect',return_value=conn):
            with self.assertRaises(sqlite3.OperationalError):subject._ensure_log_db()
        conn.close.assert_called_once_with()

    def test_shutdown_stops_owned_log_timer(self):
        self.create_log();view=self.view();view.timer.start(2000)
        self.assertTrue(view.timer.isActive());view.shutdown()
        self.assertFalse(view.timer.isActive())


if __name__=='__main__':unittest.main()
