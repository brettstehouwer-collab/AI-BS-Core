"""Actual QTextDocument signals preserve repeated styled text and UTF16 positions."""
import ast
import copy
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QApplication,QTextEdit
from native_studio.screenplay_client import DraftSession,ScreenplayError

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from core.fdx_source_documents import apply_snapshot,parse_fdx,projection_with_spans

class NativeRichQtRangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def fixture(self,raw):
        document=parse_fdx(raw);text,spans=projection_with_spans(document)
        session=DraftSession();session.load(dict(project='Fixture',revision=document['document_sha256'],content=text,
            fdx_document=document,projection_spans=spans))
        editor=QTextEdit();editor.setPlainText(text);self.addCleanup(editor.deleteLater)
        scope={}
        tree=ast.parse((ROOT/'native_studio/screenwriting_view.py').read_text(encoding='utf-8'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ScreenwritingNativeView')
        method=next(n for n in cls.body if getattr(n,'name','')=='_on_native_rich_range_changed')
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<actual-range-handler>','exec'),scope)
        state=SimpleNamespace(editor=editor,_draft=session)
        # Same signal hookups as the real view; the document range must arrive
        # before the fallback text-only update and must not track blocked loads.
        editor.textChanged.connect(lambda:setattr(session,'content',editor.toPlainText()))
        editor.document().contentsChange.connect(lambda p,r,a:scope['_on_native_rich_range_changed'](state,p,r,a))
        return session,editor

    def test_deleting_first_repeated_character_preserves_its_actual_styled_run(self):
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text Style="Bold">aa</Text><Text Style="Italic">aa</Text></Paragraph></Content></FinalDraft>'
        session,editor=self.fixture(raw);cursor=editor.textCursor();cursor.setPosition(0);cursor.deleteChar()
        self.assertEqual(session.content,'aaa');snapshot=session.capture_rich_snapshot()
        self.assertEqual((snapshot['blocks'][0]['edit_operations'][0]['start'],snapshot['blocks'][0]['edit_operations'][0]['end']),(0,1))
        output,_,_=apply_snapshot(raw,snapshot)
        self.assertEqual([(r['text'],r['attributes']) for r in parse_fdx(output)['blocks'][0]['runs']],
                         [('a',{'Style':'Bold'}),('aa',{'Style':'Italic'})])

    def test_utf16_after_non_bmp_character_maps_to_exact_python_codepoints(self):
        raw='<FinalDraft><Content><Paragraph Type="Action"><Text Style="Bold">🐈aa</Text><Text Style="Italic">aa</Text></Paragraph></Content></FinalDraft>'.encode()
        session,editor=self.fixture(raw);cursor=editor.textCursor();cursor.setPosition(2);cursor.deleteChar()
        self.assertEqual(session.content,'🐈aaa');op=session.capture_rich_snapshot()['blocks'][0]['edit_operations'][0]
        self.assertEqual((op['start'],op['end']),(1,2))

    def test_plaintext_guess_of_ambiguous_edit_is_refused_and_retained(self):
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text Style="Bold">aa</Text><Text Style="Italic">aa</Text></Paragraph></Content></FinalDraft>'
        session,editor=self.fixture(raw);session.content='aaa'
        with self.assertRaises(ScreenplayError):session.capture_rich_snapshot()
        self.assertEqual(session.rich.recovery_payload()['content'],'aaa')

    def test_programmatic_blocked_read_does_not_generate_edit_operations(self):
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text>Original.</Text></Paragraph></Content></FinalDraft>'
        session,editor=self.fixture(raw);before=copy.deepcopy(session.rich.document)
        editor.blockSignals(True);editor.setPlainText('Host load');editor.blockSignals(False)
        self.assertEqual(session.rich.document,before)

    def test_exact_same_paragraph_bulk_replacement_preserves_other_paragraph_and_notes(self):
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text Style="Bold">alpha</Text><Text Style="Italic"> beta</Text><ScriptNote><Paragraph><Text>NOTE</Text></Paragraph></ScriptNote></Paragraph><Paragraph Type="Action"><Text>Untouched.</Text></Paragraph></Content></FinalDraft>'
        session,editor=self.fixture(raw);cursor=editor.textCursor();cursor.setPosition(0);cursor.setPosition(10,QTextCursor.MoveMode.KeepAnchor);cursor.insertText('Replacement')
        snapshot=session.capture_rich_snapshot();output,_,_=apply_snapshot(raw,snapshot);current=parse_fdx(output)
        self.assertEqual(current['blocks'][0]['text'],'Replacement');self.assertEqual(current['blocks'][1]['text'],'Untouched.')
        self.assertEqual(current['blocks'][0]['notes'][0]['text'],'NOTE');self.assertEqual(current['blocks'][0]['runs'][0]['attributes']['Style'],'Bold')

    def test_cross_paragraph_bulk_change_is_retained_and_undo_restores_safe_document(self):
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text>First.</Text></Paragraph><Paragraph Type="Action"><Text>Second.</Text></Paragraph></Content></FinalDraft>'
        session,editor=self.fixture(raw);before=copy.deepcopy(session.rich.document)
        cursor=editor.textCursor();cursor.setPosition(0);cursor.setPosition(len(session.content),QTextCursor.MoveMode.KeepAnchor);cursor.insertText('Combined structural draft')
        with self.assertRaises(ScreenplayError):session.capture_rich_snapshot()
        self.assertEqual(session.rich.recovery_payload()['content'],'Combined structural draft');self.assertEqual(session.rich.document,before)
        editor.undo();self.assertEqual(session.capture_rich_snapshot(),before)

    def test_missing_exact_signal_binding_refuses_ambiguous_fallback_and_retains_full_text(self):
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text Style="Bold">aa</Text><Text Style="Italic">aa</Text></Paragraph></Content></FinalDraft>'
        session,editor=self.fixture(raw);before=copy.deepcopy(session.rich.document);editor.document().contentsChange.disconnect()
        cursor=editor.textCursor();cursor.setPosition(0);cursor.deleteChar()
        with self.assertRaises(ScreenplayError):session.capture_rich_snapshot()
        self.assertEqual(session.rich.recovery_payload()['content'],'aaa');self.assertEqual(session.rich.document,before)

    def test_undo_then_later_edit_restores_original_styles_and_revision_metadata(self):
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text Style="Bold" RevisionID="5">aa</Text><Text Style="Italic">bb</Text></Paragraph></Content></FinalDraft>'
        session,editor=self.fixture(raw);cursor=editor.textCursor();cursor.setPosition(0);cursor.setPosition(2,QTextCursor.MoveMode.KeepAnchor);cursor.removeSelectedText()
        editor.undo();cursor=editor.textCursor();cursor.movePosition(QTextCursor.MoveOperation.End);cursor.insertText('!')
        snapshot=session.capture_rich_snapshot();output,_,_=apply_snapshot(raw,snapshot);runs=parse_fdx(output)['blocks'][0]['runs']
        self.assertEqual(session.content,'aabb!');self.assertEqual(runs[0]['text'],'aa');self.assertEqual(runs[0]['attributes'],{'Style':'Bold','RevisionID':'5'})

    def test_true_qt_undo_across_acknowledged_save_retains_full_draft_and_refuses_style_loss(self):
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text Style="Bold" RevisionID="5">aa</Text><Text Style="Italic">bb</Text></Paragraph></Content></FinalDraft>'
        session,editor=self.fixture(raw);original=session.content;cursor=editor.textCursor();cursor.setPosition(0);cursor.setPosition(2,QTextCursor.MoveMode.KeepAnchor);cursor.removeSelectedText()
        submitted=session.content;snapshot=session.capture_rich_snapshot();_,document,applied=apply_snapshot(raw,snapshot)
        document['source_sha256']=snapshot['source_sha256'];document['applied_operation_ids']=list(applied)
        content,spans=projection_with_spans(document)
        session.saved(submitted,dict(status='success',project='Fixture',revision=document['document_sha256'],content=content,fdx_document=document,projection_spans=spans),snapshot)
        current=copy.deepcopy(session.rich.document);editor.undo()
        self.assertEqual(session.content,original);self.assertTrue(session.dirty)
        with self.assertRaisesRegex(ScreenplayError,'committed|working copy'):session.capture_rich_snapshot()
        self.assertEqual(session.rich.recovery_payload()['content'],original);self.assertEqual(session.rich.document,current)

    def test_malformed_typed_fields_raise_public_error_without_partial_session_replacement(self):
        from native_studio.rich_screenplay_draft import NativeRichDraft,RichDraftError
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text>Original.</Text></Paragraph></Content></FinalDraft>'
        document=parse_fdx(raw);text,spans=projection_with_spans(document)
        valid=dict(project='Fixture',revision=document['document_sha256'],content=text,fdx_document=document,projection_spans=spans)
        for kind in ('source_hash','block_type'):
            bad=copy.deepcopy(valid)
            if kind=='source_hash':bad['fdx_document']['source_sha256']=None
            else:bad['fdx_document']['blocks'][0]['type']=None
            with self.subTest(kind=kind),self.assertRaises(RichDraftError):NativeRichDraft(bad)
        session,editor=self.fixture(raw);before=session.rich.recovery_payload()
        for bad_blocks in (None,[None],{},'invalid'):
            submitted=copy.deepcopy(document);submitted['blocks']=bad_blocks
            with self.subTest(blocks=type(bad_blocks).__name__),self.assertRaises(RichDraftError):session.rich.acknowledge(valid,submitted)
            self.assertEqual(session.rich.recovery_payload(),before)

if __name__=='__main__':unittest.main()
