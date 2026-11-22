"""Real chapter owner + local HTTP fixture acceptance for AI authoring UI."""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from native_studio.game_engine.content_view import ContentView

ROOT = Path(__file__).resolve().parents[2]
EXE = ROOT / 'engine/out/windows-msvc/Debug/aibs_content_host.exe'


class OllamaFixture:
    def __init__(self):
        self.release = threading.Event()
        self.release.set()
        self.requests = []
        self.proposal = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, value):
                data = json.dumps(value).encode()
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

            def do_GET(self):
                self.respond({'models': [{'name': 'fixture:latest', 'size': 123}]})

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path == '/api/show':
                    self.respond({'capabilities': ['completion']})
                    return
                owner.requests.append(request)
                proposal = owner.proposal
                owner.release.wait(10)
                self.respond({'message': {'role': 'assistant', 'content': json.dumps(proposal)}, 'done': True})

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.endpoint = f'http://127.0.0.1:{self.server.server_port}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)


class ContentAIViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from native_studio.game_engine.content_ai import ContentAIClient
        self.directory = tempfile.TemporaryDirectory(prefix='aibs-chapter-ai-ui-')
        self.fixture = OllamaFixture()
        self.ai = ContentAIClient(endpoints=(self.fixture.endpoint,), discovery_timeout_ms=2000,
            generation_timeout_ms=8000)
        self.view = ContentView(EXE, ai_client=self.ai)
        self.view.new_project(Path(self.directory.name), 'AI chapter acceptance')
        self.idle()
        self.main = next(row for row in self.view.rows if row.type_id == 'firstboot.Door'
            and dict(row.fields)['role'] == 'main')
        self.view.select_entity(self.main.uuid)
        self.view.save_world()
        self.idle()
        self.saved = (Path(self.directory.name) / 'chapter.aiba').read_bytes()
        self.view.ai_refresh_button.click()
        self.spin(lambda: self.view.ai_model_combo.count() == 2 and not self.ai.busy)
        self.assertFalse(self.view.ai_generate_button.isEnabled(), 'Choose a model explicitly')
        self.view.ai_model_combo.setCurrentIndex(1)
        self.view.ai_prompt.setPlainText('Move the selected door half a unit right.')
        self.fixture.proposal = {'version': 1, 'label': 'Shift main door', 'edits': [
            {'entity_id': self.main.uuid, 'field': 'x', 'value': -32.5}]}

    def spin(self, predicate, seconds=20):
        until = time.monotonic() + seconds
        while not predicate() and time.monotonic() < until:
            self.app.processEvents()
            time.sleep(.003)
        self.assertTrue(predicate(), self.view.status.text() + '\nAI: ' + self.view.ai_status.text())

    def idle(self):
        self.spin(lambda: self.view.loaded and not self.view.busy and not self.view.client.pending_count)

    def held_generation(self):
        self.fixture.release.clear()
        count = len(self.fixture.requests)
        self.assertTrue(self.view.ai_generate_button.isEnabled())
        self.view.ai_generate_button.click()
        self.spin(lambda: len(self.fixture.requests) == count + 1)
        self.assertEqual(self.view.proposal_jobs.pending_count, 1)
        return self.ai.active_job_id

    def assert_saved_bytes_unchanged(self):
        self.assertEqual((Path(self.directory.name) / 'chapter.aiba').read_bytes(), self.saved)

    def tearDown(self):
        if hasattr(self, 'view'):
            self.fixture.release.set()
            self.view.cancel_ai_generation()
            self.spin(lambda: not self.view.busy and not self.view.client.pending_count)
            self.view.close_project(discard=True)
            self.spin(lambda: self.view.client.state == 'closed' and self.view.play.state == 'closed')
            self.view.close()
            self.view.deleteLater()
            self.app.processEvents()
        if hasattr(self, 'fixture'):
            self.fixture.close()
        if hasattr(self, 'directory'):
            self.directory.cleanup()

    def test_natural_request_uses_selected_capability_and_holds_native_preview_until_apply(self):
        revision = self.view.client.head.head_revision
        fingerprint = self.view.description.fingerprint
        ticked = []
        self.held_generation()
        QTimer.singleShot(0, lambda: ticked.append(True))
        self.spin(lambda: bool(ticked))
        self.assertTrue(self.view.outliner.isEnabled())
        self.assertTrue(self.view.save_button.isEnabled())
        request = self.fixture.requests[-1]
        data = json.loads(request['messages'][-1]['content'])
        self.assertEqual(data['instruction'], self.view.ai_prompt.toPlainText())
        prompt = data['authoring_data']
        self.assertEqual([row['uuid'] for row in prompt['objects']], [self.main.uuid])
        self.assertEqual(prompt['context']['fingerprint'], fingerprint)
        self.assertEqual(prompt['context']['revision'], revision)
        self.fixture.release.set()
        self.spin(lambda: self.view.apply_button.isEnabled() and not self.view.busy)
        self.assertEqual(self.view.proposal_jobs.pending_count, 0)
        self.assertEqual(self.view.client.head.head_revision, revision)
        self.assertEqual(self.view.description.fingerprint, fingerprint)
        self.assertFalse(self.view.client.dirty)
        self.assertIn('fixture:latest', self.view.ai_status.text())
        self.assertIn('127.0.0.1', self.view.ai_status.text())
        self.assertIn('Apply', self.view.ai_status.text())
        self.assertIn('new Play branch', self.view.preview_details.toPlainText())
        self.assertIn('Proposed field changes', self.view.preview_details.toPlainText())
        self.assertIn('"before": -33.0', self.view.preview_details.toPlainText())
        self.assertIn('"after": -32.5', self.view.preview_details.toPlainText())
        self.assert_saved_bytes_unchanged()
        self.view.apply_button.click()
        self.idle()
        self.assertEqual(self.view.client.head.head_revision, revision + 1)
        self.assertEqual(float(self.view.field_editors['x'].text()), -32.5)
        self.assert_saved_bytes_unchanged()

    def test_authoring_can_continue_and_stale_native_head_rejects_result(self):
        self.held_generation()
        self.view.add_fixture('Edit made during inference')
        self.idle()
        revision = self.view.client.head.head_revision
        self.fixture.release.set()
        self.spin(lambda: not self.ai.busy and not self.view.proposal_jobs.pending_count)
        self.assertIn('stale', self.view.ai_status.text().lower())
        self.assertFalse(self.view.apply_button.isEnabled())
        self.assertEqual(self.view.client.head.head_revision, revision)
        self.assert_saved_bytes_unchanged()

    def test_structurally_valid_but_physically_invalid_door_proposal_is_rejected_by_native_preview(self):
        # Replay a real model's semantically wrong absolute x value: the JSON
        # and selected typed capability are valid, but the door loses its route.
        self.fixture.proposal['edits'][0]['value'] = 1.5
        revision = self.view.client.head.head_revision
        fingerprint = self.view.description.fingerprint
        self.view.ai_generate_button.click()
        self.spin(lambda: not self.ai.busy and not self.view.busy
            and not self.view.client.pending_count and not self.view.proposal_jobs.pending_count)
        self.assertIn('AI proposal rejected by native preview', self.view.ai_status.text())
        self.assertIn('Door aperture no longer connects its declared regions', self.view.ai_status.text())
        self.assertIn('Door aperture no longer connects its declared regions', self.view.status.text())
        self.assertFalse(self.view.apply_button.isEnabled())
        self.assertEqual(self.view.client.head.head_revision, revision)
        self.assertEqual(self.view.description.fingerprint, fingerprint)
        self.assertFalse(self.view.client.dirty)
        self.assertEqual(float(self.view.field_editors['x'].text()), -33.)
        self.assert_saved_bytes_unchanged()

    def test_ai_prepared_review_is_cleared_before_manual_preview(self):
        revision = self.view.client.head.head_revision
        self.view.ai_generate_button.click()
        self.spin(lambda: self.view.apply_button.isEnabled())
        self.assertIn('Proposed field changes', self.view.preview_details.toPlainText())
        self.view.field_editors['x'].setText('-32.75')
        self.assertFalse(self.view.apply_button.isEnabled())
        self.assertEqual(self.view.preview_details.toPlainText(), '')
        self.assertIn('invalidated', self.view.ai_status.text())
        self.spin(lambda: not self.view.client.pending_count)
        self.view.preview_button.click()
        self.spin(lambda: self.view.apply_button.isEnabled())
        self.assertNotIn('Proposed field changes', self.view.preview_details.toPlainText())
        self.assertNotIn('fixture:latest', self.view.preview_details.toPlainText())
        self.assertEqual(self.view.client.head.head_revision, revision)
        self.view.apply_button.click()
        self.idle()
        self.assertEqual(float(self.view.field_editors['x'].text()), -32.75)
        self.assert_saved_bytes_unchanged()

    def test_changed_selection_or_inspector_inputs_rejects_result(self):
        for change in ('selection', 'inputs'):
            with self.subTest(change=change):
                self.view.select_entity(self.main.uuid)
                self.held_generation()
                if change == 'selection':
                    other = next(row for row in self.view.rows if row.uuid != self.main.uuid)
                    self.view.select_entity(other.uuid)
                else:
                    self.view.field_editors['x'].setText('-32.75')
                self.fixture.release.set()
                self.spin(lambda: not self.ai.busy and not self.view.proposal_jobs.pending_count)
                self.assertIn('stale', self.view.ai_status.text().lower())
                self.assertFalse(self.view.apply_button.isEnabled())
                self.assertFalse(self.view.client.dirty)
                self.assert_saved_bytes_unchanged()

    def test_cancel_and_late_signal_never_preview_or_write(self):
        job = self.held_generation()
        revision = self.view.client.head.head_revision
        self.view.ai_cancel_button.click()
        self.assertEqual(self.view.proposal_jobs.pending_count, 0)
        self.assertFalse(self.ai.busy)
        self.fixture.release.set()
        self.ai.proposal_ready.emit(job, json.dumps(self.fixture.proposal))
        self.app.processEvents()
        self.assertIn('cancel', self.view.ai_status.text().lower())
        self.assertFalse(self.view.apply_button.isEnabled())
        self.assertEqual(self.view.client.head.head_revision, revision)
        self.assert_saved_bytes_unchanged()

    def test_close_reopen_and_owner_death_cancel_capabilities_and_late_results(self):
        job = self.held_generation()
        self.view.close_project()
        self.spin(lambda: self.view.client.state == 'closed')
        self.assertFalse(self.ai.busy)
        self.assertEqual(self.view.proposal_jobs.pending_count, 0)
        self.fixture.release.set()
        self.view.open_project(Path(self.directory.name))
        self.idle()
        self.view.select_entity(self.main.uuid)
        self.ai.proposal_ready.emit(job, json.dumps(self.fixture.proposal))
        self.app.processEvents()
        self.assertFalse(self.view.apply_button.isEnabled())
        self.assert_saved_bytes_unchanged()
        self.held_generation()
        self.view.client.abort('Injected chapter owner failure during inference')
        self.spin(lambda: self.view.client.state == 'closed')
        self.assertFalse(self.ai.busy)
        self.assertEqual(self.view.proposal_jobs.pending_count, 0)
        self.assertFalse(self.view.apply_button.isEnabled())
        self.assert_saved_bytes_unchanged()

    def test_generation_and_explicit_apply_work_during_pinned_native_play(self):
        self.view.start_play()
        self.spin(lambda: self.view.play.state == 'ready')
        pinned = self.view.play.snapshot.fingerprint
        self.held_generation()
        self.assertTrue(self.view.stop_play_button.isEnabled())
        self.fixture.release.set()
        self.spin(lambda: self.view.apply_button.isEnabled())
        self.view.apply_button.click()
        self.idle()
        self.assertEqual(self.view.play.state, 'ready')
        self.assertEqual(self.view.play.snapshot.fingerprint, pinned)
        self.assertNotEqual(self.view.description.fingerprint, pinned)
        self.assertIn('restart Play', self.view.play_status.text())
        self.assert_saved_bytes_unchanged()


if __name__ == '__main__':
    unittest.main()
