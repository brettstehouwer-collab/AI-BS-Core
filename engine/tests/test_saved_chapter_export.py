"""Second-owner saved export: no player, graphics or implicit SAVE."""
import hashlib, os, tempfile, unittest, uuid
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.saved_chapter_export import SavedChapterExportClient, hash_saved_journal
from native_studio.game_engine.content_commands import ContentDescription, ContentExportChunk, ContentExportDependency, open_document
from native_studio.game_engine.project_assets import AssetDependency
from native_studio.game_engine.content_preview import ContentSnapshot
from native_studio.game_engine.creator_commands import Status
from native_studio.game_engine.creator_payload import Scope
from native_studio.game_engine.creator_wire import Opcode

APP = QApplication.instance() or QApplication([])
def uid(): return str(uuid.uuid4())

class Owner(QObject):
    ready=pyqtSignal(); response=pyqtSignal(object,object)
    request_failed=pyqtSignal(object,str); closed=pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent); self.state='closed'; self.generation=11
        self.capabilities=frozenset({'chapter-content-export-v2'})
        self.process_id=0; self.calls=[]; self.head=None; self.stopped=False
    def start(self, executable, directory):
        self.state='starting'; self.process_id=123; self.directory=directory
    def announce(self): self.state='ready'; self.ready.emit()
    def request(self, opcode, payload=b'', revision=None):
        self.calls.append((opcode,payload,revision)); return len(self.calls)
    def answer(self, reply):
        self.head=reply; self.response.emit(len(self.calls),reply)
    def stop(self): self.stopped=True; self.state='closing'
    def join(self, reason='Requested close'):
        self.state='closed'; self.process_id=0; self.closed.emit(reason)

class SavedExport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        (self.root/'chapter.aiba').write_bytes(b'native journal fixture')
        self.payload=b'canonical saved content'; self.scope=Scope('p','main',uid(),uid())
        self.s=ContentSnapshot(self.scope,4,7,uid(),uid(),3,hashlib.sha256(self.payload).hexdigest(),self.payload,
            frozenset(),asset_store=self.root/'assets/packs',export_version=2)
        self.definition=SimpleNamespace(directory=self.root,project='p',branch='main',asset_profile='legacy_v1',opening_workshop=False)
        self.patch=patch('native_studio.game_engine.saved_chapter_export.ContentClient',Owner); self.patch.start()
        self.job=SavedChapterExportClient(); self.owner=self.job.client; self.results=[]; self.failures=[]; self.closes=[]
        self.job.completed.connect(self.results.append); self.job.failed.connect(self.failures.append); self.job.closed.connect(lambda:self.closes.append(True))
        self.valid=True
    def tearDown(self):
        if self.job.busy:self.job.stop(); self.owner.join()
        self.job.deleteLater(); self.patch.stop(); self.tmp.cleanup()
    def start(self): self.job.start(Path('host.exe'),self.definition,self.s,context_valid=lambda:self.valid)
    def reply(self, **changes):
        d=dict(status=Status.OK,message='',scope=replace(self.scope,host_epoch=uid()),head_revision=7,checkpoint_id=self.s.checkpoint_id,body=b'')
        d.update(changes); return SimpleNamespace(**d)
    def opened(self):
        self.start(); self.owner.announce(); self.owner.answer(self.reply())
    def described(self, **changes):
        self.opened(); d=ContentDescription(self.s.definition_id,3,self.s.fingerprint,False,0)
        d=replace(d,**changes)
        with patch('native_studio.game_engine.saved_chapter_export.decode_description',return_value=d):self.owner.answer(self.reply(scope=self.owner.head.scope))
    def exported(self, **changes):
        self.described(); c=ContentExportChunk(self.s.definition_id,self.s.fingerprint,3,len(self.payload),0,self.payload,version=2)
        c=replace(c,**changes)
        with patch('native_studio.game_engine.saved_chapter_export.decode_content_export',return_value=c):self.owner.answer(self.reply(scope=self.owner.head.scope))
    def test_native_open_reads_existing_saved_journal_without_save(self):
        self.opened(); self.assertEqual(self.owner.calls[0],(Opcode.OPEN,open_document('p','main',False),None))
        self.assertEqual(self.owner.calls[1][0],Opcode.DESCRIBE); self.assertNotEqual(self.owner.head.scope.host_epoch,self.scope.host_epoch)
        self.assertFalse(any(c[0]==Opcode.SAVE for c in self.owner.calls))
    def test_result_only_after_owner_gracefully_joins_then_rebinds_original_pin(self):
        self.exported(); self.assertTrue(self.owner.stopped); self.assertEqual(self.results,[])
        self.owner.join(); self.assertEqual(len(self.results),1); self.assertEqual(self.results[0].snapshot,self.s)
        self.assertEqual(self.results[0].journal_sha256,hashlib.sha256(b'native journal fixture').hexdigest())
        self.assertEqual(self.closes,[True]); self.assertEqual(self.failures,[])
    def test_dirty_description_cannot_claim_saved_export(self):
        self.described(dirty=True); self.owner.join(); self.assertEqual(self.results,[]); self.assertTrue(self.failures)
    def test_wrong_saved_head_rejected(self):
        self.start(); self.owner.announce(); self.owner.answer(self.reply(head_revision=8)); self.owner.join()
        self.assertTrue(self.failures); self.assertEqual(len(self.owner.calls),1)
    def test_wrong_world_rejected_even_matching_revision(self):
        self.start(); self.owner.announce(); self.owner.answer(self.reply(scope=replace(self.scope,world_id=uid()))); self.owner.join(); self.assertTrue(self.failures)
    def test_same_head_but_content_identity_mismatch_rejected(self):
        self.described(fingerprint='0'*64); self.owner.join(); self.assertTrue(self.failures)
    def test_complete_dependency_export_is_mandatory(self):
        self.exported(version=1); self.owner.join(); self.assertTrue(self.failures); self.assertEqual(self.results,[])
    def test_original_context_stale_during_owner_start(self):
        self.start(); self.valid=False; self.owner.announce(); self.owner.join(); self.assertEqual(self.owner.calls,[]); self.assertTrue(self.failures)
    def test_original_context_stale_after_export_before_join_rejected(self):
        self.exported(); self.valid=False; self.owner.join(); self.assertEqual(self.results,[]); self.assertTrue(self.failures)
    def test_journal_changes_after_export_before_join_rejected(self):
        self.exported(); (self.root/'chapter.aiba').write_bytes(b'changed'); self.owner.join(); self.assertFalse(self.results); self.assertTrue(self.failures)
    def test_identical_bytes_replacement_rejected(self):
        self.exported(); p=self.root/'chapter.aiba'; p.rename(self.root/'before.aiba'); p.write_bytes(b'native journal fixture')
        self.owner.join(); self.assertFalse(self.results); self.assertTrue(self.failures)
    def test_cancel_joins_without_completion(self):
        self.start(); self.job.stop(); self.assertTrue(self.job.busy); self.assertEqual(self.closes,[])
        self.owner.join(); self.assertEqual(self.results,[]); self.assertEqual(self.failures,[]); self.assertEqual(self.closes,[True])
    def test_unexpected_close_or_forced_close_cannot_publish(self):
        self.exported(); self.owner.join('Creator graceful close deadline expired'); self.assertTrue(self.failures); self.assertFalse(self.results)
    def test_request_failure_joins_before_failure_signal(self):
        self.start(); self.owner.announce(); self.owner.request_failed.emit(1,'read rejected')
        self.assertFalse(self.failures); self.owner.join(); self.assertTrue(self.failures)
    def test_missing_or_oversize_journal_never_starts_owner(self):
        p=self.root/'chapter.aiba'; p.unlink()
        with self.assertRaises(ValueError):self.start()
        p.write_bytes(b'x'*(1024*1024+1))
        with self.assertRaises(ValueError):self.start()
        self.assertEqual(self.owner.process_id,0)
    def test_unsaved_snapshot_or_legacy_export_never_starts_owner(self):
        for s in (replace(self.s,checkpoint_id=''),replace(self.s,export_version=1)):
            with self.subTest(s=s.export_version),self.assertRaises(ValueError):self.job.start(Path('host.exe'),self.definition,s)
        self.assertEqual(self.owner.process_id,0)
    def test_journal_hash_is_bounded_and_does_not_modify_bytes(self):
        p=self.root/'chapter.aiba'; before=p.read_bytes(); self.assertEqual(hash_saved_journal(self.root).bytes,len(before)); self.assertEqual(p.read_bytes(),before)
    def test_missing_complete_export_capability_refuses_open(self):
        self.owner.capabilities=frozenset(); self.start(); self.owner.announce(); self.owner.join(); self.assertTrue(self.failures); self.assertEqual(self.owner.calls,[])
    def test_chunked_native_export_uses_second_scope_and_ordered_offsets(self):
        self.described();scope=self.owner.head.scope
        for offset,payload in [(0,self.payload[:7]),(7,self.payload[7:])]:
            c=ContentExportChunk(self.s.definition_id,self.s.fingerprint,3,len(self.payload),offset,payload,version=2)
            with patch('native_studio.game_engine.saved_chapter_export.decode_content_export',return_value=c):self.owner.answer(self.reply(scope=scope))
            if offset==0:self.assertFalse(self.owner.stopped)
        self.assertTrue(self.owner.stopped);self.owner.join();self.assertEqual(self.results[0].snapshot,self.s)
        self.assertEqual(len(self.owner.calls),4)
    def test_native_complete_dependency_mismatch_cannot_publish(self):
        dependency=ContentExportDependency(0,AssetDependency(uid(),'1'*64,'2'*64))
        self.exported(dependencies=(dependency,));self.owner.join();self.assertFalse(self.results);self.assertTrue(self.failures)
    def test_secondary_epoch_change_mid_export_rejected(self):
        self.described();c=ContentExportChunk(self.s.definition_id,self.s.fingerprint,3,len(self.payload),0,self.payload,version=2)
        with patch('native_studio.game_engine.saved_chapter_export.decode_content_export',return_value=c):self.owner.answer(self.reply())
        self.owner.join();self.assertFalse(self.results);self.assertTrue(self.failures)
    def test_original_generation_tick_invalidates_without_more_requests(self):
        self.opened();self.valid=False;self.job._tick();self.assertTrue(self.owner.stopped)
        self.owner.join();self.assertFalse(self.results);self.assertTrue(self.failures)
    def test_project_foreign_asset_store_refused_before_owner(self):
        with self.assertRaisesRegex(ValueError,'dependencies'):self.job.start(Path('host.exe'),self.definition,replace(self.s,asset_store=self.root/'foreign'))
        self.assertEqual(self.owner.process_id,0)
    def test_source_journal_redirect_rejected(self):
        p=self.root/'chapter.aiba';actual=p.lstat()
        with patch('native_studio.game_engine.saved_chapter_export.Path.lstat',return_value=SimpleNamespace(
                st_mode=actual.st_mode,st_file_attributes=0x400)),self.assertRaisesRegex(ValueError,'reparse'):hash_saved_journal(self.root)

if __name__=='__main__':unittest.main()
