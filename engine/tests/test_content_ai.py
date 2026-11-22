"""Actual loopback HTTP/Qt integration for the local authoring transport."""
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
import unittest
import uuid
import sys

from PyQt6.QtWidgets import QApplication
from native_studio.game_engine.content_ai import ContentAIClient, LocalModel


class OllamaFixture:
    def __init__(self):
        self.requests = []
        self.delay = 0
        self.tags = {'models': [{'name': 'fixture:latest', 'size': 123}]}
        self.proposal = None
        self.chat_body = None
        self.show = {'capabilities': ['completion', 'tools'], 'remote_host': None, 'remote_model': None}
        self.show_delay = 0
        self.chunked = False
        self.status = 200
        self.redirect = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                owner.requests.append(('GET', self.path, None))
                self.send(owner.tags)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append(('POST', self.path, body))
                if self.path == '/api/show':
                    self.send(owner.show, owner.show_delay)
                    return
                proposal = owner.proposal
                if proposal is None:
                    source = json.loads(body['messages'][1]['content'])['authoring_data']
                    row = source['objects'][0]
                    proposal = json.dumps({'version': 1, 'label': 'Move doorway', 'edits': [
                        {'entity_id': row['uuid'], 'field': 'x', 'value': -32.5}]})
                result = owner.chat_body if owner.chat_body is not None else {'done': True, 'message': {'role': 'assistant', 'content': proposal}}
                self.send(result)

            def send(self, result, request_delay=None):
                delay = owner.delay if request_delay is None else request_delay
                status = owner.status
                redirect = owner.redirect
                raw = result if isinstance(result, bytes) else json.dumps(result).encode()
                if delay:
                    time.sleep(delay)
                try:
                    self.send_response(status)
                    if redirect:
                        self.send_header('Location', redirect)
                    self.send_header('Content-Type', 'application/json')
                    if owner.chunked:
                        self.send_header('Transfer-Encoding', 'chunked')
                    else:
                        self.send_header('Content-Length', str(len(raw)))
                    self.end_headers()
                    if owner.chunked:
                        for start in range(0, len(raw), 32768):
                            chunk = raw[start:start + 32768]
                            self.wfile.write(f'{len(chunk):x}\r\n'.encode() + chunk + b'\r\n')
                        self.wfile.write(b'0\r\n\r\n')
                    else:
                        self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = 'http://127.0.0.1:' + str(self.server.server_port)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)


class ContentAITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.fixture = OllamaFixture()
        self.client = ContentAIClient(endpoints=(self.fixture.endpoint,), discovery_timeout_ms=200, generation_timeout_ms=250)
        self.inventory = []
        self.proposals = []
        self.failures = []
        self.states = []
        self.client.inventory_ready.connect(lambda models, diagnostics: self.inventory.append((models, diagnostics)))
        self.client.proposal_ready.connect(lambda job, raw: self.proposals.append((job, raw)))
        self.client.failed.connect(lambda job, error: self.failures.append((job, error)))
        self.client.state_changed.connect(self.states.append)

    def tearDown(self):
        self.client.cancel()
        self.client.deleteLater()
        self.app.processEvents()
        self.fixture.close()

    def spin(self, predicate, seconds=2):
        end = time.monotonic() + seconds
        while not predicate() and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.002)
        self.assertTrue(predicate(), (self.client.state, self.failures))

    def settle(self, seconds=.1):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.002)

    def discover(self):
        self.client.refresh_models()
        self.spin(lambda: bool(self.inventory))
        self.assertEqual(self.inventory[-1][0], (LocalModel(self.fixture.endpoint, 'fixture:latest', 123),))
        self.assertEqual(self.client.models, self.inventory[-1][0])
        return self.client.models[0]

    def prompt(self, job='job-1'):
        return {'job_id': job, 'context': {'project': 'test', 'branch': 'main', 'world_id': str(uuid.uuid4()),
            'definition_id': str(uuid.uuid4()), 'revision': 3, 'fingerprint': 'a' * 64},
            'objects': [{'uuid': str(uuid.uuid4()), 'name': 'Main doorway', 'type': 'firstboot.Door',
                'fields': {'x': -33.0, 'caption': 'Original authored text', 'active': True}}],
            'response_format': {'version': 1, 'label': 'Proposed edit', 'edits': []}}

    def test_actual_request_pins_schema_context_and_finite_typed_fields(self):
        model = self.discover()
        prompt = self.prompt()
        self.client.generate('job-1', model, prompt, 'Move doorway slightly right')
        prompt['objects'][0]['fields']['x'] = 999
        self.assertEqual(self.client.active_job_id, 'job-1')
        self.spin(lambda: bool(self.proposals or self.failures))
        self.assertFalse(self.failures)
        self.assertEqual(self.proposals[0][0], 'job-1')
        self.assertEqual(json.loads(self.proposals[0][1])['edits'][0]['value'], -32.5)
        method, path, body = self.fixture.requests[-1]
        self.assertEqual((method, path), ('POST', '/api/chat'))
        self.assertEqual(self.fixture.requests[-2], ('POST', '/api/show', {'model': model.name}))
        self.assertFalse(body['stream'])
        self.assertEqual(body['keep_alive'], 0)
        self.assertEqual(body['options'], {'temperature': 0, 'num_predict': 1024, 'num_ctx': 8192})
        self.assertEqual(body['format']['properties']['version']['const'], 1)
        self.assertFalse(body['format']['additionalProperties'])
        edits = body['format']['properties']['edits']['items']['oneOf']
        self.assertEqual({item['properties']['field']['const']: item['properties']['value']['type'] for item in edits},
            {'x': 'number', 'caption': 'string', 'active': 'boolean'})
        authoring = json.loads(body['messages'][1]['content'])['authoring_data']
        self.assertEqual(authoring['objects'][0]['fields']['x'], -33.)
        system = body['messages'][0]['content'].lower()
        self.assertIn('historical', system)
        self.assertIn('absolute replacement', system)
        self.assertIn('current_value + signed_delta', system)
        self.assertIn('including its sign', system)
        self.assertIn('x, y, z are position coordinates', system)
        self.assertIn('half_x, half_y, half_z are half-extents', system)
        self.assertIn("never copy another field's value", system)
        self.assertEqual(json.loads(body['messages'][1]['content'])['instruction'], 'Move doorway slightly right')
        self.assertEqual(self.client.state, 'idle')
        self.assertIsNone(self.client.active_job_id)

    def test_partial_inventory_has_diagnostics_and_strict_json(self):
        other = OllamaFixture()
        try:
            other.tags = b'{"models":[],"models":[]}'
            self.client.deleteLater()
            self.client = ContentAIClient(endpoints=(self.fixture.endpoint, other.endpoint), discovery_timeout_ms=200)
            self.client.inventory_ready.connect(lambda models, diagnostics: self.inventory.append((models, diagnostics)))
            self.client.refresh_models()
            self.spin(lambda: bool(self.inventory))
            self.assertEqual(len(self.inventory[0][0]), 1)
            self.assertEqual(len(self.inventory[0][1]), 1)
            self.assertIn(other.endpoint, self.inventory[0][1][0])
        finally:
            other.close()

    def test_malformed_duplicate_nonfinite_and_out_of_capability_outputs_fail(self):
        model = self.discover()
        prompt = self.prompt()
        uid = prompt['objects'][0]['uuid']
        sources = ('not json', '{"version":1,"version":1,"label":"x","edits":[]}',
            json.dumps({'version': 1, 'label': 'x', 'edits': [{'entity_id': uid, 'field': 'x', 'value': float('nan')}]}),
            json.dumps({'version': 1, 'label': 'x', 'edits': [{'entity_id': uid, 'field': 'foreign', 'value': 1}]}))
        for source in sources:
            with self.subTest(source=source):
                self.fixture.proposal = source
                before = len(self.failures)
                self.client.generate('job-1', model, prompt, 'Move')
                self.spin(lambda: len(self.failures) > before)
                self.assertEqual(self.failures[-1][0], 'job-1')
                self.assertFalse(self.proposals)
                self.assertFalse(self.client.busy)

    def test_oversized_http_and_proposal_are_rejected_and_client_reusable(self):
        model = self.discover()
        prompt = self.prompt()
        for body in (b'x' * (1024 * 1024 + 1), {'done': True, 'message': {'content': 'x' * (256 * 1024 + 1)}}):
            self.fixture.chat_body = body
            before = len(self.failures)
            self.client.generate('job-1', model, prompt, 'Move')
            self.spin(lambda: len(self.failures) > before)
            self.assertFalse(self.proposals)
        self.fixture.chat_body = None
        self.client.generate('job-1', model, prompt, 'Move')
        self.spin(lambda: bool(self.proposals))

    def test_timeout_cancel_replaced_job_and_late_reply_are_suppressed(self):
        model = self.discover()
        self.fixture.delay = .35
        self.client.generate('job-1', model, self.prompt(), 'Move')
        self.spin(lambda: bool(self.failures))
        self.assertIn('timed out', self.failures[-1][1].lower())
        self.settle(.15)
        self.assertFalse(self.proposals)
        self.failures.clear()
        self.client.generate('job-1', model, self.prompt(), 'Move')
        self.spin(lambda: len([r for r in self.fixture.requests if r[1] == '/api/chat']) >= 2)
        self.client.cancel('different-job')
        self.assertTrue(self.client.busy)
        self.client.cancel('job-1')
        self.assertFalse(self.client.busy)
        self.fixture.delay = 0
        self.client.generate('job-2', model, self.prompt('job-2'), 'Move')
        self.spin(lambda: bool(self.proposals))
        self.settle(.4)
        self.assertEqual([job for job, _ in self.proposals], ['job-2'])
        self.assertFalse(self.failures)
        self.proposals.clear()
        self.fixture.delay = .15
        self.client.generate('job-3', model, self.prompt('job-3'), 'Move')
        self.spin(lambda: len([r for r in self.fixture.requests if r[1] == '/api/chat']) >= 4)
        self.fixture.delay = 0
        self.client.generate('job-4', model, self.prompt('job-4'), 'Move')
        self.spin(lambda: bool(self.proposals))
        self.settle(.2)
        self.assertEqual([job for job, _ in self.proposals], ['job-4'])
        self.assertFalse(self.failures)

    def test_no_redirect_no_uninstalled_model_and_bounded_inputs(self):
        model = self.discover()
        prompt = self.prompt()
        before = len(self.fixture.requests)
        for candidate, source, instruction in ((LocalModel(self.fixture.endpoint, 'not-installed'), prompt, 'Move'),
            (model, prompt, 'x' * 8193), (model, {**prompt, 'padding': 'x' * (256 * 1024)}, 'Move')):
            self.client.generate('job-1', candidate, source, instruction)
            self.assertTrue(self.failures)
            self.assertFalse(self.client.busy)
        self.assertEqual(len(self.fixture.requests), before)
        self.failures.clear()
        self.fixture.status = 302
        self.fixture.redirect = 'http://example.invalid/api/chat'
        self.client.generate('job-1', model, prompt, 'Move')
        self.spin(lambda: bool(self.failures))
        self.assertIn('302', self.failures[0][1])
        for endpoint in ('https://127.0.0.1:11434', 'http://example.com:11434', 'http://user:secret@127.0.0.1:11434', 'http://127.0.0.1:11434/path'):
            with self.assertRaises(ValueError):
                ContentAIClient(endpoints=(endpoint,))

    def test_selected_model_preflight_rejects_remote_embeddings_and_has_shared_deadline(self):
        model = self.discover()
        for response in ({'capabilities': ['embedding']},
                {'capabilities': ['completion'], 'remote_model': 'cloud-alias'},
                {'capabilities': ['completion'], 'details': {'remote_host': 'https://example.invalid'}},
                {'error': 'Selected model unavailable'}):
            self.fixture.show = response
            before = len(self.failures)
            self.client.generate('job-1', model, self.prompt(), 'Move')
            self.spin(lambda: len(self.failures) > before)
            self.assertFalse(any(path == '/api/chat' for _, path, _ in self.fixture.requests))
        self.fixture.show = {'capabilities': ['completion']}
        self.fixture.show_delay = .15
        self.fixture.delay = .15
        before = len(self.failures)
        self.client.generate('job-1', model, self.prompt(), 'Move')
        self.spin(lambda: len(self.failures) > before)
        self.assertIn('timed out', self.failures[-1][1].lower())
        self.assertFalse(self.proposals)

    def test_cancelled_preflight_never_forwards_snapshot_and_inventory_excludes_cloud(self):
        self.fixture.tags['models'].extend([
            {'name': 'remote:cloud', 'size': 123},
            {'name': 'remote-alias', 'size': 123, 'remote_model': 'cloud'},
            {'name': 'not-installed', 'size': 0}])
        model = self.discover()
        self.assertEqual(len(self.inventory[0][1]), 3)
        self.fixture.show_delay = .15
        self.client.generate('job-1', model, self.prompt(), 'Move')
        self.spin(lambda: any(path == '/api/show' for _, path, _ in self.fixture.requests))
        self.client.cancel()
        self.settle(.2)
        self.assertFalse(any(path == '/api/chat' for _, path, _ in self.fixture.requests))
        self.assertFalse(self.proposals)
        self.assertFalse(self.failures)

    def test_deep_json_is_a_clean_failure_and_chunked_receive_buffer_is_bounded(self):
        model = self.discover()
        nested = '[' * 1200 + '0' + ']' * 1200
        envelope = ('{"done":true,"padding":' + nested + ',"message":{}}').encode()
        old_hook = sys.excepthook
        callback_errors = []
        sys.excepthook = lambda *error: callback_errors.append(error)
        try:
            for result in (envelope, {'done': True, 'message': {'content': nested}}):
                self.fixture.chat_body = result
                before = len(self.failures)
                self.client.generate('job-1', model, self.prompt(), 'Move')
                self.spin(lambda: len(self.failures) > before or bool(callback_errors))
                self.assertFalse(callback_errors, 'Malformed provider JSON escaped a Qt callback')
                self.assertGreater(len(self.failures), before)
        finally:
            sys.excepthook = old_hook
        self.fixture.chunked = True
        self.fixture.chat_body = b'x' * (1024 * 1024 + 1)
        self.fixture.delay = .1
        before = len(self.failures)
        self.client.generate('job-1', model, self.prompt(), 'Move')
        self.spin(lambda: any(p.kind == 'proposal' for p in self.client._requests.values()))
        reply = next(p.reply for p in self.client._requests.values() if p.kind == 'proposal')
        self.assertGreater(reply.readBufferSize(), 0)
        self.assertLessEqual(reply.readBufferSize(), 1024 * 1024)
        self.spin(lambda: len(self.failures) > before)
        self.assertFalse(self.proposals)


if __name__ == '__main__':
    unittest.main()
