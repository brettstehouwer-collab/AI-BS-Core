"""Actual rich writer Qt with synthetic HTTP, drafts and optional-page tripwires."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

import httpx
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtGui import QFontDatabase, QTextCursor
from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton, QTextEdit, QWidget
from core.fdx_source_documents import apply_snapshot, parse_fdx, projection_with_spans
from native_studio.creative_session import Bootstrap, CreativeSession, CreativeSessionError
from native_studio.screenplay_client import DraftSession, ScreenplayClient
import native_studio.screenwriting_view as writer


class Queue:
    def __init__(self): self.jobs = []
    def submit(self, work, *, on_result, on_error): self.jobs.append((work, on_result, on_error))
    def drain(self):
        count = 0
        while self.jobs:
            count += 1
            if count > 20: raise AssertionError('Unbounded synthetic work')
            work, result, error = self.jobs.pop(0)
            try: value = work()
            except Exception as problem: error(str(problem))
            else: result(value)


class Fixture:
    def __init__(self, rich=False):
        self.calls = []
        self.fail = False
        self.raw = (b'<FinalDraft><Content><Paragraph Type="Action"><Text Style="Bold">aa</Text>'
                    b'<Text Style="Italic">aa</Text><ScriptNote><Paragraph><Text>Fixture note</Text>'
                    b'</Paragraph></ScriptNote></Paragraph></Content></FinalDraft>')
        self.source = hashlib.sha256(self.raw).hexdigest() if rich else 'a' * 64
        if rich:
            document = parse_fdx(self.raw)
            content, spans = projection_with_spans(document)
            self.data = dict(project='Bound', content=content, revision=document['document_sha256'],
                             fdx_document=document, projection_spans=spans)
        else:
            content = 'INT. FIXTURE - DAY\nA synthetic action.\n'
            self.data = dict(project='Bound', content=content,
                             revision=hashlib.sha256(content.encode()).hexdigest())

    def handle(self, request):
        path = request.url.path
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, path, dict(request.url.params), body))
        if self.fail: return httpx.Response(503, json={'detail': 'Synthetic backend unavailable'})
        if path == '/api/screenwriting/native/redeem':
            return httpx.Response(200, json=dict(lease='nch_l_' + 'z' * 43, project='Bound',
                revision=self.data['revision'], source_sha256=self.source, expires_in=60))
        if path == '/api/screenwriting/projects':
            return httpx.Response(200, json=dict(projects=['Bound'], current='Bound'))
        if path == '/api/screenwriting/read':
            assert request.url.params['project_name'] == 'Bound'
            return httpx.Response(200, json=deepcopy(self.data))
        if path == '/api/screenwriting/write':
            assert body['project_name'] == 'Bound'
            assert body['expected_revision'] == self.data['revision']
            if 'fdx_document' in body:
                self.raw, document, applied = apply_snapshot(self.raw, body['fdx_document'])
                document['source_sha256'] = self.source
                document['applied_operation_ids'] = list(applied)
                content, spans = projection_with_spans(document)
                self.data = dict(project='Bound', content=content, revision=document['document_sha256'],
                                 fdx_document=document, projection_spans=spans)
            else:
                self.data = dict(project='Bound', content=body['content'],
                                 revision=hashlib.sha256(body['content'].encode()).hexdigest())
            return httpx.Response(200, json=dict(status='success', **deepcopy(self.data)))
        if path in ('/api/screenwriting/export/fdx', '/api/screenwriting/export/pdf'):
            assert request.url.params['project_name'] == 'Bound'
            payload = self.raw if path.endswith('/fdx') else b'%PDF-1.4\nSynthetic fixture\n%%EOF'
            return httpx.Response(200, content=payload)
        raise AssertionError('Unexpected scoped route: ' + path)


class ScopedWriterQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_ids = []
        for name in ('segoeui.ttf', 'cour.ttf'):
            path = Path('C:/Windows/Fonts') / name
            if path.is_file(): cls.font_ids.append(QFontDatabase.addApplicationFont(str(path)))

    @classmethod
    def tearDownClass(cls):
        for number in cls.font_ids:
            if number >= 0: QFontDatabase.removeApplicationFont(number)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.views = []
        self.addCleanup(self._close)
        self.bus = Queue()
        self.fixture = Fixture()
        self.now = 100.
        self.session = CreativeSession(headers_provider=lambda: {'X-Admin-Key': 'synthetic-only'},
            transport=httpx.MockTransport(self.fixture.handle), clock=lambda: self.now)
        self.packet = self._packet()
        self.session.redeem(self.packet)
        for guard in (patch.object(QMessageBox, 'warning'), patch.object(QMessageBox, 'information'),
                      patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No)):
            guard.start(); self.addCleanup(guard.stop)
        self.headers = patch('native_studio.screenplay_client.local_service_headers',
                             side_effect=AssertionError('No default credential fallback'))
        self.headers.start(); self.addCleanup(self.headers.stop)
        self.drafts = patch.object(writer, 'DraftSession', side_effect=lambda:
                                  DraftSession(Path(self.temp.name) / ('private-' + str(len(self.views)))))
        self.drafts.start(); self.addCleanup(self.drafts.stop)
        self.factory_calls = []
        def client(**kwargs):
            self.factory_calls.append(kwargs)
            return ScreenplayClient(transport=httpx.MockTransport(self.fixture.handle), **kwargs)
        self.clients = patch.object(writer, 'ScreenplayClient', side_effect=client)
        self.clients.start(); self.addCleanup(self.clients.stop)

    def _packet(self):
        return Bootstrap('nch_g_' + 'g' * 43, 'Bound', self.fixture.data['revision'], self.fixture.source, 'b' * 64)

    def _view(self, *, drain=True):
        import builtins
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name in {'native_studio.creation_suite_subtools', 'native_studio.screenwriting_modals',
                        'native_studio.audio_kernel', 'native_studio.service_orchestrator'}:
                raise AssertionError('Unrelated delegated module import: ' + name)
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=guarded):
            view = writer.ScreenwritingNativeView(self.bus, creative_session=self.session, bootstrap=self.packet)
        self.views.append(view)
        if drain: self.bus.drain()
        return view

    def _close(self):
        for view in self.views:
            view._draft_timer.stop(); view._adapt_timer.stop()
            if not view.editor.isReadOnly() and view._draft.dirty: view._preserve_native_draft()
            self.app.removeEventFilter(view)
            try: self.app.aboutToQuit.disconnect(view._preserve_native_draft)
            except TypeError: pass
            view.close(); view.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_actual_rich_writer_constructs_only_writing_page_and_bound_read(self):
        view = self._view(drain=False)
        self.assertIsInstance(view.editor, QTextEdit)
        self.assertIsNotNone(view.page_viewer)
        self.assertIsNotNone(view.split_page_viewer)
        self.assertTrue(view.editor.isReadOnly())
        self.assertEqual(view.suite_stack.count(), 1)
        self.assertFalse(hasattr(view, 'video_page'))
        self.assertFalse(hasattr(view, 'comfy_page'))
        self.assertEqual(self.factory_calls, [dict(creative_session=self.session)])
        self.bus.drain()
        self.assertFalse(view.editor.isReadOnly())
        self.assertEqual(view._draft.project, 'Bound')
        self.assertEqual(view.combo_project.count(), 1)
        self.assertFalse(view.combo_project.isEnabled())
        self.assertEqual([x[1] for x in self.fixture.calls],
                         ['/api/screenwriting/native/redeem', '/api/screenwriting/read'])

    def test_partial_unredeemed_or_mismatched_injection_is_refused(self):
        for options in (dict(creative_session=self.session), dict(bootstrap=self.packet),
                        dict(creative_session=object(), bootstrap=self.packet),
                        dict(creative_session=self.session, bootstrap=self._packet()),
                        dict(creative_session=CreativeSession(), bootstrap=self.packet)):
            with self.assertRaises(CreativeSessionError): writer.ScreenwritingNativeView(self.bus, **options)

    def test_initial_stale_snapshot_is_never_editable(self):
        self.fixture.data['revision'] = 'changed-after-bootstrap'
        view = self._view()
        self.assertTrue(view.editor.isReadOnly())
        self.assertIsNone(view._draft.project)
        self.assertEqual(view.editor.toPlainText(), '')
        self.assertIn('did not match', view.lbl_autosave.text())

    def _assert_initial_edit_actions_blocked(self, view):
        before = (view.editor.toPlainText(), view._draft.project, view._draft.revision,
                  view._draft.content, view._draft.baseline, view._draft.dirty, view._draft.recovery_path)
        char_format = view.editor.currentCharFormat()
        formatting = (char_format.fontWeight(), char_format.fontItalic(), char_format.fontUnderline())
        requests = list(self.fixture.calls)
        self.assertFalse(view._delegated_editor_ready())
        self.assertFalse(view.writing_page.isEnabled())
        view.txt_inline_find.setText('anything')
        view.txt_inline_replace.setText('unverified replacement')
        with patch.object(writer.QDialog, 'exec', side_effect=AssertionError('No pre-load editing dialog')), \
             patch.object(writer.QInputDialog, 'getItem', side_effect=AssertionError('No pre-load thesaurus')):
            view._insert_element_text('Unverified element')
            view._inline_replace_all()
            view._show_elements_palette()
            view._show_find_replace_dialog()
            view._lookup_thesaurus()
            view._toggle_bold(); view._toggle_italic(); view._toggle_underline()
            for button in view.writing_page.findChildren(QPushButton):
                self.assertFalse(button.isEnabled(), button.text())
                button.click()
        current = view.editor.currentCharFormat()
        self.assertEqual((current.fontWeight(), current.fontItalic(), current.fontUnderline()), formatting)
        self.assertEqual((view.editor.toPlainText(), view._draft.project, view._draft.revision,
                          view._draft.content, view._draft.baseline, view._draft.dirty,
                          view._draft.recovery_path), before)
        self.assertEqual(self.fixture.calls, requests)
        self.assertFalse(view._draft_timer.isActive())

    def test_pending_snapshot_blocks_programmatic_actions_and_clicks_then_enables_local_edits(self):
        view = self._view(drain=False)
        self._assert_initial_edit_actions_blocked(view)
        self.bus.drain()
        self.assertTrue(view._delegated_editor_ready())
        self.assertTrue(view.writing_page.isEnabled())
        view._insert_element_text('Verified local edit. ')
        self.assertTrue(view._draft.dirty)
        self.assertIn('Verified local edit.', view.editor.toPlainText())
        self.now = 160.  # Local editing is independent of the expired network lease.
        view._insert_element_text('Still editable after expiry. ')
        self.assertIn('Still editable after expiry.', view.editor.toPlainText())
        self.assertTrue(view._preserve_native_draft())
        self.assertEqual(json.loads(view._draft.recovery_path.read_text(encoding='utf-8'))['content'],
                         view.editor.toPlainText())

    def test_stale_initial_snapshot_keeps_programmatic_actions_and_controls_nonediting(self):
        self.fixture.data['revision'] = 'changed-after-bootstrap'
        view = self._view()
        self.assertTrue(view.editor.isReadOnly())
        self._assert_initial_edit_actions_blocked(view)
        self.assertIsNone(view._draft.project)

    def test_palette_replace_and_thesaurus_callbacks_recheck_readiness_before_mutating(self):
        view = self._view()
        before = view.editor.toPlainText()
        def blocked_dialog(dialog):
            view._creative_initial_read = True
            try:
                for button in dialog.findChildren(QPushButton):
                    if button.text() not in {'Close', 'Done'}:
                        button.click()
                dialog.reject()
            finally:
                view._creative_initial_read = False
            return 0
        with patch.object(writer.QDialog, 'exec', new=blocked_dialog):
            view._show_elements_palette()
            view._show_find_replace_dialog()
        def stale_thesaurus(*args, **kwargs):
            view._creative_initial_read = True
            return 'unverified synonym', True
        try:
            with patch.object(writer.QInputDialog, 'getText', return_value=('talked', True)), \
                 patch.object(writer.QInputDialog, 'getItem', side_effect=stale_thesaurus):
                view._lookup_thesaurus()
        finally:
            view._creative_initial_read = False
        self.assertEqual(view.editor.toPlainText(), before)
        self.assertEqual(view._draft.content, before)
        self.assertFalse(view._draft.dirty)

    def test_foreign_rich_source_is_refused_before_replacing_the_editor(self):
        self.fixture = Fixture(rich=True)
        self.session = CreativeSession(headers_provider=lambda: {'X-Admin-Key': 'synthetic-only'},
            transport=httpx.MockTransport(self.fixture.handle), clock=lambda: self.now)
        self.packet = self._packet(); self.session.redeem(self.packet)
        self.fixture.data['fdx_document']['source_sha256'] = 'c' * 64
        view = self._view()
        self.assertTrue(view.editor.isReadOnly())
        self.assertIsNone(view._draft.project)
        self.assertEqual(view.editor.toPlainText(), '')
        self.assertIn('did not match', view.lbl_autosave.text())

    def test_bound_read_save_and_fdx_pdf_export_use_existing_pipeline(self):
        view = self._view()
        view.editor.moveCursor(QTextCursor.MoveOperation.End)
        view.editor.insertPlainText('Local synthetic edit.')
        self.assertTrue(view._draft.dirty)
        view._save_script(); self.bus.drain()
        self.assertFalse(view._draft.dirty)
        self.assertFalse(view._draft.uncertain)
        for fmt in ('fdx', 'pdf'):
            target = Path(self.temp.name) / ('new-export.' + fmt)
            view._export_native_project(fmt, str(target)); self.bus.drain()
            self.assertTrue(target.is_file())
        self.assertTrue(any(x[1] == '/api/screenwriting/write' for x in self.fixture.calls))
        self.assertFalse(any(x[1] == '/api/screenwriting/projects' for x in self.fixture.calls))

    def test_rich_repeated_style_edit_and_save_retains_original_runs_and_note(self):
        self.fixture = Fixture(rich=True)
        self.session = CreativeSession(headers_provider=lambda: {'X-Admin-Key': 'synthetic-only'},
            transport=httpx.MockTransport(self.fixture.handle), clock=lambda: self.now)
        self.packet = self._packet(); self.session.redeem(self.packet)
        view = self._view()
        self.assertIsNotNone(view._draft.rich)
        self.assertFalse(view._format_buttons['B'].isEnabled())
        cursor = view.editor.textCursor(); cursor.setPosition(0); cursor.deleteChar()
        view._save_script(); self.bus.drain()
        self.assertFalse(view._draft.uncertain)
        self.assertFalse(view._draft.dirty)
        parsed = parse_fdx(self.fixture.raw)
        self.assertEqual([(x['text'], x['attributes']) for x in parsed['blocks'][0]['runs']],
                         [('a', {'Style': 'Bold'}), ('aa', {'Style': 'Italic'})])
        self.assertEqual(parsed['blocks'][0]['notes'][0]['text'], 'Fixture note')

    def test_expiry_and_backend_loss_preserve_editable_complete_local_draft(self):
        for fault in ('expiry', 'backend'):
            with self.subTest(fault=fault):
                self.now = 100.; self.session.redeem(self.packet)
                view = self._view()
                view.editor.moveCursor(QTextCursor.MoveOperation.End)
                view.editor.insertPlainText('Unsaved synthetic text — retained.')
                content = view.editor.toPlainText()
                if fault == 'expiry': self.now = 160.
                else: self.fixture.fail = True
                view._save_script(); self.bus.drain()
                self.assertTrue(view._draft.uncertain)
                self.assertTrue(view._draft.dirty)
                self.assertFalse(view.editor.isReadOnly())
                self.assertEqual(view.editor.toPlainText(), content)
                self.assertEqual(json.loads(view._draft.recovery_path.read_text(encoding='utf-8'))['content'], content)
                self.fixture.fail = False

    def test_forbidden_methods_cannot_dispatch_create_import_services_or_models(self):
        view = self._view()
        before = list(self.fixture.calls)
        actions = {
            '_scan_and_populate_projects': (), '_action_new_project': (), '_show_adapt_manuscript_dialog': (),
            '_create_native_project': ('other', 'author', 'template'),
            '_import_native_project': ('other', 'unused'), '_create_native_rich_working_copy': (),
            '_open_native_created': ('other', ''), '_start_native_adaptation': ('unused', 'other', 'script', {}),
            '_poll_native_adaptation': (), '_show_script_assistant': (), '_run_script_doctor': (),
            '_novelize_to_book': (), '_launch_table_read': (), '_launch_audio_drama': (),
            '_show_previs_dialog': (), '_export_unreal_asset': ('csv',), '_send_scene_to_video': (),
            '_parse_active_editor_into_comfy': (), '_show_character_vault': (), '_show_coverage_report': (),
            '_show_storyboard_gallery': (), '_show_production_cms_dialog': (), '_show_stageplay_breakdown_dialog': (),
            '_publish_to_cms': (), '_start_writing_sprint': (), '_toggle_revision_mode': (),
            '_show_title_page_dialog': (), '_review_active_page': (), '_generate_alt_take': (),
            '_share_subtool': (), '_show_studio_guide': (), '_show_screenwriting_guide': (),
            '_toggle_lock_studio': (), '_unlock_studio': ('unused',),
        }
        for name, args in actions.items():
            with self.subTest(action=name): getattr(view, name)(*args)
        for key in ('video', 'comfy', 'visual', 'lock'): view._switch_suite_tab(key)
        view._load_project('other'); view._read_native_project('other')
        view._export_script_format('fountain')
        view._export_native_project('fountain', str(Path(self.temp.name) / 'not-created.fountain'))
        view._set_ribbon_tab('production'); view._set_view_mode('beat')
        self.bus.drain()
        self.assertEqual(self.fixture.calls, before)
        self.assertEqual(view.suite_stack.currentIndex(), 0)
        self.assertFalse(view.btn_new_proj.isEnabled())
        self.assertTrue(view.btn_new_proj.isHidden())
        self.assertFalse(view.btn_copilot.isEnabled())
        self.assertFalse(view.btn_import.isEnabled())
        self.assertFalse(view.btn_export_fdx.menu().actions()[1].isEnabled())
        self.assertFalse((Path(self.temp.name) / 'not-created.fountain').exists())

    def test_foreign_project_save_and_both_export_entrypoints_are_refused_before_io(self):
        view = self._view()
        before = list(self.fixture.calls)
        view._draft.project = 'Foreign'
        target = Path(self.temp.name) / 'not-created.fdx'
        with patch.object(writer.QFileDialog, 'getSaveFileName',
                          side_effect=AssertionError('Foreign-project export dialog forbidden')):
            view._save_script()
            view._export_script_format('fdx')
            view._export_native_project('fdx', str(target))
        self.bus.drain()
        self.assertEqual(self.fixture.calls, before)
        self.assertFalse(target.exists())
        view._draft.project = 'Bound'

    def test_ordinary_constructor_keeps_catalogue_and_all_existing_suite_indices(self):
        pages = []
        module = types.ModuleType('native_studio.creation_suite_subtools')
        def page(*args, **kwargs): pages.append((args, kwargs)); return QWidget()
        for name in ('VideoStudioPage', 'ComfyUIStudioPage', 'VisualScriptingPage', 'LockScreenPage'):
            setattr(module, name, page)
        with patch.dict(sys.modules, {'native_studio.creation_suite_subtools': module}):
            view = writer.ScreenwritingNativeView(self.bus)
        self.views.append(view)
        with patch('native_studio.screenplay_client.local_service_headers', return_value={'X-Admin-Key': 'synthetic'}):
            self.bus.drain()
        self.assertEqual(self.factory_calls, [{}])
        self.assertEqual(len(pages), 4)
        self.assertEqual(view.suite_stack.count(), 5)
        self.assertIsNone(view._creative_bootstrap)
        self.assertTrue(view.btn_new_proj.isEnabled())
        self.assertTrue(view.combo_project.isEnabled())
        self.assertIn('/api/screenwriting/projects', [x[1] for x in self.fixture.calls])


if __name__ == '__main__': unittest.main(verbosity=2)
