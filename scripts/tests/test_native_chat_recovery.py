"""Private synthetic chat recovery; no models, commands, user data or services."""
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
os.environ['QT_QPA_PLATFORM']='offscreen'


class ChatStoreTests(unittest.TestCase):
    def setUp(self):
        self.m=importlib.import_module('native_studio.chat_recovery')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'recovery'/'profile'
        self.store=self.m.ChatRecoveryStore(self.root)
        self.state={'transcript':'[OPERATOR]: fixture\n[CHAT]: reply','draft':'unsent fixture','scratchpad':'print("fixture")','history':[['fixture','reply']],'model':'fixture-model'}

    def test_round_trip_preserves_transcript_unsent_draft_scratchpad_model_and_history(self):
        self.assertIsNone(self.store.load().state)
        receipt=self.store.save(self.state)
        self.assertEqual(self.store.load().state,self.state)
        self.assertTrue(receipt.path.is_file())
        self.assertEqual(self.m.ChatRecoveryStore(self.root).load().state,self.state)

    def test_every_save_retains_original_snapshot_without_replacing_it(self):
        first=self.store.save(self.state);original=first.path.read_bytes()
        updated={**self.state,'draft':'next unsent fixture'}
        second=self.store.save(updated)
        self.assertNotEqual(first.path,second.path)
        self.assertEqual(first.path.read_bytes(),original)
        self.assertEqual(self.store.load().state,updated)

    def test_incomplete_and_tampered_latest_fall_back_with_visible_warning(self):
        self.store.save(self.state)
        newest=self.store.save({**self.state,'draft':'second'})
        value=json.loads(newest.path.read_text());value['state']['draft']='tampered';newest.path.write_text(json.dumps(value))
        loaded=self.store.load()
        self.assertEqual(loaded.state,self.state)
        self.assertTrue(loaded.warning)
        self.assertTrue(newest.path.is_file())

    def test_all_invalid_is_error_and_does_not_silently_start_empty(self):
        receipt=self.store.save(self.state);receipt.path.write_bytes(b'incomplete')
        with self.assertRaises(self.m.ChatRecoveryError):self.store.load()
        self.assertEqual(receipt.path.read_bytes(),b'incomplete')

    def test_failed_disk_write_retains_previous_and_partial_evidence(self):
        first=self.store.save(self.state);original=first.path.read_bytes()
        with patch.object(self.m.os,'fsync',side_effect=OSError('fixture disk failure')):
            with self.assertRaises(self.m.ChatRecoveryError):self.store.save({**self.state,'draft':'not-confirmed'})
        self.assertEqual(first.path.read_bytes(),original)
        self.assertEqual(self.store.load().state,self.state)
        self.assertTrue(list(self.root.glob('*.partial')))

    def test_invalid_state_size_and_shape_rejected_before_any_new_snapshot(self):
        self.store.save(self.state);before=list(self.root.glob('*.json'))
        for state in [{**self.state,'history':[['one']]},{**self.state,'draft':None},{**self.state,'other':'unexpected'}]:
            with self.assertRaises(self.m.ChatRecoveryError):self.store.save(state)
        with patch.object(self.m,'MAX_BYTES',10):
            with self.assertRaises(self.m.ChatRecoveryError):self.store.save(self.state)
        self.assertEqual(before,list(self.root.glob('*.json')))

    def test_redirected_snapshot_is_refused_without_reading_target(self):
        receipt=self.store.save(self.state)
        with patch.object(self.m,'_is_redirected',side_effect=lambda p:p==receipt.path):
            with self.assertRaises(self.m.ChatRecoveryError):self.store.load()


class ChatWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.m=importlib.import_module('native_studio.chat_recovery')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=self.m.ChatRecoveryStore(Path(self.temp.name)/'recovery'/'profile')
        self.jobs=[]
        jobs=self.jobs
        class Bus:
            def submit(self,work,*,on_result,on_error):jobs.append((work,on_result,on_error))
        from native_studio.bs_chat_ide_full import BsChatIdeFullView
        self.view=BsChatIdeFullView(Bus(),session_store=self.store)
        self.addCleanup(self.view.deleteLater)
        self.addCleanup(lambda:self.view._chat_recovery.timer.stop())

    def complete(self,index=0):
        work,good,bad=self.jobs.pop(index)
        try:result=work()
        except Exception:bad('synthetic recovery failure')
        else:good(result)

    def test_load_gate_releases_after_empty_store_and_error_without_false_saved(self):
        self.assertFalse(self.view.input_edit.isEnabled())
        self.complete()
        self.assertTrue(self.view.input_edit.isEnabled())
        self.assertNotIn('Auto-Save Active',self.view.recovery_status.text())
        self.assertNotIn('saved',self.view.recovery_status.text().lower())

    def test_actual_widget_restores_without_sending_commands_or_replaying_actions(self):
        state={'transcript':'/ps dangerous-fixture-do-not-run','draft':'unsent','scratchpad':'fixture scratch','history':[['fixture','reply']],'model':'stehouwer_llm'}
        self.store.save(state)
        self.complete()
        self.assertEqual(self.view.chat_display.toPlainText(),state['transcript'])
        self.assertEqual(self.view.input_edit.text(),'unsent')
        self.assertEqual(self.view.code_editor.toPlainText(),'fixture scratch')
        self.assertEqual(self.view._conversation_history,[('fixture','reply')])
        self.assertEqual(self.jobs,[])

    def test_dirty_snapshot_saved_only_after_worker_ack_and_latest_edit_coalesces(self):
        self.complete();self.view.input_edit.setText('first')
        self.view._chat_recovery.tick();self.view.input_edit.setText('latest')
        self.assertNotIn('saved',self.view.recovery_status.text().lower())
        self.view._chat_recovery.tick();self.assertEqual(len(self.jobs),1)
        self.complete();self.view._chat_recovery.tick();self.assertEqual(len(self.jobs),1)
        self.complete()
        self.assertEqual(self.store.load().state['draft'],'latest')
        self.assertIn('saved',self.view.recovery_status.text().lower())

    def test_close_preserves_fresh_draft_before_shutdown_and_blocks_on_disk_failure(self):
        self.complete();self.view.input_edit.setText('close fixture')
        self.assertTrue(self.view._chat_recovery.flush_for_close())
        self.assertEqual(self.store.load().state['draft'],'close fixture')
        self.view.input_edit.setText('second close fixture')
        with patch.object(self.store,'save',side_effect=self.m.ChatRecoveryError('synthetic disk failure')):
            self.assertFalse(self.view._chat_recovery.flush_for_close())
        self.assertEqual(self.view.input_edit.text(),'second close fixture')

    def test_edits_during_load_are_kept_and_saved_history_is_not_overwritten(self):
        self.store.save({'transcript':'prior fixture','draft':'prior draft','scratchpad':'','history':[],'model':'stehouwer_llm'})
        self.view.input_edit.setText('new draft while loading')
        self.complete()
        self.assertEqual(self.view.input_edit.text(),'new draft while loading')
        self.assertTrue(self.view.input_edit.isEnabled())
        self.assertIn('retained',self.view.recovery_status.text().lower())
        self.assertEqual(self.store.load().state['draft'],'prior draft')

    def test_failed_load_never_writes_empty_history_on_close_or_timer(self):
        receipt=self.store.save({'transcript':'prior fixture','draft':'prior','scratchpad':'','history':[],'model':'stehouwer_llm'})
        receipt.path.write_bytes(b'damaged fixture')
        self.complete();self.assertTrue(self.view.input_edit.isEnabled())
        self.view._chat_recovery.tick();self.assertEqual(self.jobs,[])
        self.assertFalse(self.view._chat_recovery.flush_for_close())
        self.assertEqual(len(list(self.store.root.glob('*.json'))),1)
        self.assertEqual(receipt.path.read_bytes(),b'damaged fixture')

    def test_queued_old_snapshot_cannot_overwrite_final_close_draft(self):
        self.complete();self.view.input_edit.setText('queued old draft')
        self.view._chat_recovery.tick();self.assertEqual(len(self.jobs),1)
        self.view.input_edit.setText('final close draft')
        self.assertTrue(self.view._chat_recovery.flush_for_close())
        self.complete()
        self.assertEqual(self.store.load().state['draft'],'final close draft')


if __name__=='__main__':unittest.main()
