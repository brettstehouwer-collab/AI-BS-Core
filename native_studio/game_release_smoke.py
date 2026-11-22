"""Exercise the shipped native game workspace without starting host services."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import argparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication
from native_studio.engine import EngineBus
from native_studio.game_build_view import GameBuildNativeView
from native_studio.theme import STYLESHEET


def run_game_release_smoke(report: Path) -> int:
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        font = Path('C:/Windows/Fonts/segoeui.ttf')
        if font.is_file():
            QFontDatabase.addApplicationFont(str(font))
            app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(STYLESHEET)
    bus = EngineBus(max_threads=1)
    view = None
    data = {'schema_version': 1, 'status': 'failed', 'frozen': bool(getattr(sys, 'frozen', False)),
            'checks': [], 'application_services_started': False}
    try:
        view = GameBuildNativeView(bus)
        view.resize(1150, 950)
        view.show()
        deadline = time.monotonic() + 10
        while view.pending and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()
        if view.pending or 'LOCAL DRIVE SPACE' not in view.details.toPlainText():
            raise RuntimeError('Game workspace worker refresh did not complete')
        data['checks'].append('Native game workspace and worker-driven monitor rendered')
        data['playground_available'] = view.playground_path.is_file()
        if not data['playground_available']:
            raise RuntimeError('Concept playground is unavailable to the native client')
        data['playground_path'] = str(view.playground_path)
        if data['frozen'] and not str(view.playground_path).startswith(str(Path(sys._MEIPASS))):
            raise RuntimeError('Frozen game workspace did not select its bundled playground')
        data['checks'].append('Concept playground resource resolved without launching a browser')
        report.parent.mkdir(parents=True, exist_ok=True)
        if not view.grab().save(str(report.with_suffix('.png'))):
            raise RuntimeError('Could not capture the native game workspace')
        data['checks'].append('Native workspace screenshot captured')
        data['status'] = 'passed'
    except Exception as exc:
        data['error'] = str(exc)
    finally:
        if view is not None:
            view.close()
        bus.shutdown()
        data['completed_at'] = datetime.now(timezone.utc).isoformat()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return 0 if data['status'] == 'passed' else 2


class _AuthoringHTTPFixture:
    """Deterministic test data over real HTTP; this performs no model inference."""

    model = 'release-http-fixture:latest'

    def __init__(self):
        self.paths = []
        self.chat_request = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, value):
                raw = json.dumps(value, allow_nan=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                owner.paths.append(self.path)
                if self.path != '/api/tags':
                    self.send_error(404)
                    return
                self.respond({'models': [{'name': owner.model, 'size': 123}]})

            def do_POST(self):
                owner.paths.append(self.path)
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2 * 1024 * 1024:
                    self.send_error(413)
                    return
                body = json.loads(self.rfile.read(length))
                if self.path == '/api/show':
                    self.respond({'capabilities': ['completion']})
                elif self.path == '/api/chat':
                    owner.chat_request = body
                    source = json.loads(body['messages'][1]['content'])['authoring_data']
                    row = source['objects'][0]
                    proposal = {'version': 1, 'label': 'Deterministic HTTP fixture: shift door',
                        'edits': [{'entity_id': row['uuid'], 'field': 'x', 'value': -32.5}]}
                    self.respond({'done': True, 'message': {'role': 'assistant',
                        'content': json.dumps(proposal)}})
                else:
                    self.send_error(404)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = False
        self.thread = threading.Thread(target=self.server.serve_forever,
            kwargs={'poll_interval': .05}, name='creator-smoke-http-fixture')
        self.thread.start()
        self.endpoint = f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        return not self.thread.is_alive()


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _wait(app, predicate, message, view=None, seconds=30):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.003)
    if not predicate():
        details = ('; ' + view.status.text()) if view is not None else ''
        if view is not None and hasattr(view, 'ai_status'):
            details += '; ' + view.ai_status.text()
        raise RuntimeError(message + details)


def _idle(app, view):
    _wait(app, lambda: view.loaded and not view.busy and not view.client.pending_count,
        'Native authoring owner did not become idle', view)


def _row_fields(view, identity):
    return dict(next(row for row in view.rows if row.uuid == identity).fields)


def _head_identity(view):
    head = view.client.head
    return head.scope, head.head_revision, head.checkpoint_id


def _saved_identity(view):
    head = view.client.head
    return (head.scope.project, head.scope.branch, head.scope.world_id,
        head.head_revision, head.checkpoint_id)


def _bundle_executable(path, bundle, data, name):
    path = Path(path).resolve()
    expected = (bundle / 'game_assets/player').resolve()
    _require(path.is_file() and path.parent == expected,
        f'{name} did not resolve from the frozen bundle player directory: {path}')
    data['native_executables'][name] = str(path)
    return path


def _capture(widget, path, data, name):
    _require(widget.grab().save(str(path)), 'Could not capture ' + name)
    data['captures'][name] = str(path)


def _probe_viewport(app, view, directory, bundle, data, name):
    """First observe READY, then run the real renderer's capture/self-test path."""
    view.open_viewport()
    _wait(app, lambda: view.viewport.state == 'ready', name + ' did not render', view)
    _bundle_executable(view.viewport._process.program(), bundle, data, name)
    data['observed_process_ids'][name] = view.viewport.process_id
    _require(view.viewport.displayed_tag[2] == view.client.head.head_revision,
        name + ' displayed a different authoring revision')
    view.viewport.stop()
    _wait(app, lambda: view.viewport.state == 'closed', name + ' did not join', view)
    directory.mkdir()
    view.open_viewport(probe_directory=directory)
    _wait(app, lambda: not view.busy and view.viewport.state == 'closed'
        and (directory / 'viewport.json').is_file(), name + ' did not produce a capture', view)
    proof = json.loads((directory / 'viewport.json').read_text(encoding='utf-8'))
    _require(proof['nonbackground_pixels'] > 100 and proof['debug_errors'] == 0,
        name + ' renderer capture failed validation')
    data['metrics'][name + '_render'] = proof
    data['captures'][name] = str(directory / 'viewport.bmp')


def _close_document(app, view):
    view.close_project()
    _wait(app, lambda: view.client.state == 'closed' and view.viewport.state == 'closed'
        and (not hasattr(view, 'play') or view.play.state == 'closed'),
        'Native project close did not join its children', view)


def run_creator_release_smoke(report: Path, *, provider='fixture', model=None,
                              endpoint=None) -> int:
    """Explicit packaged creator acceptance; normal app startup never calls this.

    A source-only invocation deliberately fails rather than using checkout native
    binaries. The default fixture verifies QtNetwork and native admission without
    claiming AI inference. Live Ollama needs an explicitly selected model.
    """
    report = Path(report).resolve()
    started = time.monotonic()
    app = view = bus = fixture = None
    data = {'schema_version': 1, 'status': 'failed', 'checks': [], 'metrics': {},
        'frozen': bool(getattr(sys, 'frozen', False)), 'application_services_started': False,
        'provider_origin': 'not_started', 'actual_model_inference': False,
        'native_executables': {}, 'observed_process_ids': {}, 'captures': {},
        'all_owned_processes_joined': False}
    try:
        _require(provider in ('fixture', 'ollama'), 'Unknown creator smoke provider')
        _require(provider != 'ollama' or bool(model and model.strip()),
            'Live creator smoke requires an explicit model')
        _require(data['frozen'] and bool(getattr(sys, '_MEIPASS', None)),
            'Creator release smoke requires a frozen bundle; source fallback is forbidden')
        bundle = Path(sys._MEIPASS).resolve()
        data['bundle_root'] = str(bundle)
        report.parent.mkdir(parents=True, exist_ok=True)
        # The directory is preserved beside the report for review. Its project
        # root contains no source tree, installed engine, or native fallback.
        import tempfile
        work = Path(tempfile.mkdtemp(prefix=report.stem + '-work-', dir=report.parent))
        root = work / 'synthetic-checkout'
        root.mkdir()
        data['work_directory'] = str(work)
        data['workspace_root'] = str(root)
        required = ('aibs_creator_host.exe', 'aibs_content_host.exe',
            'aibs_creator_viewport.exe', 'aibs_motherboard.exe')
        for name in required:
            _require((bundle / 'game_assets/player' / name).is_file(),
                'Missing frozen native asset: ' + name)
        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(STYLESHEET)
        bus = EngineBus(max_threads=1)
        view = GameBuildNativeView(bus, root=root)
        view.resize(1500, 1100)
        view.show()
        _wait(app, lambda: not view.pending, 'Synthetic workspace monitor did not complete')
        view.timer.stop()
        _require(view.creator_view is None and view.content_view is None,
            'Creator tabs were not opened lazily')
        _require(view.playground_path.resolve().is_relative_to(bundle),
            'Playground did not resolve from the bundle')
        data['checks'].append('Actual GameBuildNativeView opened with a synthetic source-free project root')

        view.workspace_tabs.setCurrentIndex(1)
        numeric = view.creator_view
        _require(numeric is not None and view.content_view is None,
            'Numeric creator did not open lazily')
        _bundle_executable(numeric.executable, bundle, data, 'numeric_host')
        world = work / 'numeric-project'
        world.mkdir()
        numeric.new_project(world, 'Frozen numeric acceptance')
        _idle(app, numeric)
        data['observed_process_ids']['numeric_host'] = numeric.client.process_id
        numeric.add_node('release-cube', 'Packaged cube')
        _idle(app, numeric)
        identity = numeric.selected_id
        numeric.save_world()
        _idle(app, numeric)
        saved = (world / 'world.aibs').read_bytes()
        head = _head_identity(numeric)
        # Keep geometry centered for the native Win32 center-click capture
        # probe while editing a real numeric field through the same UI path.
        numeric.field_editors['capacity'].setText('7.5')
        numeric.preview_button.click()
        _wait(app, lambda: numeric.apply_button.isEnabled() and not numeric.busy,
            'Numeric native preview was not prepared', numeric)
        _require(_head_identity(numeric) == head and (world / 'world.aibs').read_bytes() == saved
            and _row_fields(numeric, identity)['capacity'] == 0., 'Numeric preview published private changes')
        data['metrics']['numeric_preview_private'] = True
        numeric.apply_button.click()
        _idle(app, numeric)
        _require(_row_fields(numeric, identity)['capacity'] == 7.5
            and (world / 'world.aibs').read_bytes() == saved, 'Numeric Apply/Save separation failed')
        numeric.undo_button.click()
        _idle(app, numeric)
        _require(_row_fields(numeric, identity)['capacity'] == 0., 'Numeric Undo failed')
        numeric.redo_button.click()
        _idle(app, numeric)
        _require(_row_fields(numeric, identity)['capacity'] == 7.5, 'Numeric Redo failed')
        numeric.save_world()
        _idle(app, numeric)
        numeric_head = _saved_identity(numeric)
        _capture(view, work / 'numeric-creator.png', data, 'numeric_creator')
        _probe_viewport(app, numeric, work / 'numeric-render', bundle, data, 'numeric_viewport')
        _close_document(app, numeric)
        numeric.open_project(world)
        _idle(app, numeric)
        # Each process has a fresh host_epoch. Persisted identity, revision,
        # checkpoint and authoring fields must survive that epoch transition.
        data['metrics']['numeric_reopen_head_before'] = numeric_head
        data['metrics']['numeric_reopen_head_after'] = _saved_identity(numeric)
        _require(_saved_identity(numeric) == numeric_head and _row_fields(numeric, identity)['capacity'] == 7.5,
            'Saved numeric world did not reopen identically')
        _close_document(app, numeric)
        data['checks'].append('Bundled numeric host: Preview/Apply/Undo/Redo/Save/reopen and native DX12 viewport')

        view.workspace_tabs.setCurrentIndex(2)
        chapter = view.content_view
        _require(chapter is not None, 'Chapter creator did not open lazily')
        _bundle_executable(chapter.executable, bundle, data, 'content_host')
        chapter_root = work / 'chapter-project'
        chapter_root.mkdir()
        chapter.new_project(chapter_root, 'Frozen First Boot acceptance')
        _idle(app, chapter)
        data['observed_process_ids']['content_host'] = chapter.client.process_id
        chapter.add_fixture('Typed fixture')
        _idle(app, chapter)
        fixture_id = chapter.selected_id
        chapter.save_world()
        _idle(app, chapter)
        document = chapter_root / 'chapter.aiba'
        saved = document.read_bytes()
        head, fingerprint = _head_identity(chapter), chapter.description.fingerprint
        original = _row_fields(chapter, fixture_id)
        chapter.field_editors['x'].setText('-34.5')
        chapter.field_editors['name'].setText('Packaged typed fixture')
        chapter.field_editors['selectable'].setChecked(False)
        chapter.preview_button.click()
        _wait(app, lambda: chapter.apply_button.isEnabled() and not chapter.busy,
            'Typed native preview was not prepared', chapter)
        _require(_head_identity(chapter) == head and chapter.description.fingerprint == fingerprint
            and document.read_bytes() == saved and _row_fields(chapter, fixture_id) == original,
            'Typed preview published private changes')
        data['metrics']['typed_preview_private'] = True
        chapter.apply_button.click()
        _idle(app, chapter)
        expected = dict(original, x=-34.5, name='Packaged typed fixture', selectable=False)
        _require(_row_fields(chapter, fixture_id) == expected and document.read_bytes() == saved,
            'Typed Apply did not preserve separate Save')
        chapter.undo_button.click()
        _idle(app, chapter)
        _require(_row_fields(chapter, fixture_id) == original, 'Typed grouped Undo failed')
        chapter.redo_button.click()
        _idle(app, chapter)
        _require(_row_fields(chapter, fixture_id) == expected, 'Typed grouped Redo failed')
        data['metrics']['typed_fields_verified'] = ['number', 'text', 'boolean']
        chapter.save_world()
        _idle(app, chapter)
        data['checks'].append('Bundled typed chapter host: private number/text/boolean Preview and grouped Apply/Undo/Redo')

        # Replace the idle, uncontacted default endpoint client. Every request
        # below uses the same production QtNetwork path used by the creator UI.
        from native_studio.game_engine.content_ai import ContentAIClient
        old_ai = chapter.ai_client
        old_ai.inventory_ready.disconnect(chapter._ai_inventory_ready)
        old_ai.proposal_ready.disconnect(chapter._ai_proposal_ready)
        old_ai.failed.disconnect(chapter._ai_failed)
        old_ai.cancel()
        old_ai.deleteLater()
        if provider == 'fixture':
            fixture = _AuthoringHTTPFixture()
            endpoint, model = fixture.endpoint, fixture.model
            data['provider_origin'] = 'deterministic_loopback_http_fixture'
        else:
            endpoint = endpoint or 'http://127.0.0.1:11434'
            data['provider_origin'] = 'explicit_installed_local_ollama_model'
        ai = ContentAIClient(chapter, endpoints=(endpoint,), generation_timeout_ms=120000)
        chapter.ai_client = ai
        ai.inventory_ready.connect(chapter._ai_inventory_ready)
        ai.proposal_ready.connect(chapter._ai_proposal_ready)
        ai.failed.connect(chapter._ai_failed)
        ai.state_changed.connect(lambda *_: chapter._controls())
        data['provider_endpoint'], data['selected_model'] = endpoint, model
        data['ai_states'] = []
        ai.state_changed.connect(data['ai_states'].append)
        proposals = []
        ai.proposal_ready.connect(lambda job, raw: proposals.append((job, raw)))
        main = next(row for row in chapter.rows if row.type_id == 'firstboot.Door'
            and dict(row.fields)['role'] == 'main')
        chapter.select_entity(main.uuid)
        chapter.refresh_ai_models()
        _wait(app, lambda: not ai.busy, 'Local HTTP model discovery did not finish', chapter)
        index = next((i for i in range(chapter.ai_model_combo.count())
            if getattr(chapter.ai_model_combo.itemData(i), 'name', None) == model), None)
        _require(index is not None, 'Explicit selected local model is absent from inventory: ' + str(model))
        chapter.ai_model_combo.setCurrentIndex(index)
        chapter.ai_prompt.setPlainText('Move the selected main door exactly 0.5 units right. '
            'Its current x is -33.0 and its required final absolute x is -32.5. '
            'Change only x; preserve every other field. Return one set-field proposal.')
        saved = document.read_bytes()
        head, fingerprint = _head_identity(chapter), chapter.description.fingerprint
        data['model_inference_requested'] = provider == 'ollama'
        chapter.generate_ai_proposal()
        _wait(app, lambda: not ai.busy and not chapter.busy and not chapter.client.pending_count,
            'Local HTTP generation/native Preview did not finish', chapter, seconds=125)
        data['actual_model_inference'] = provider == 'ollama' and bool(proposals)
        if proposals:
            proposal = json.loads(proposals[-1][1])
            data['metrics']['provider_proposal'] = proposal
        else:
            proposal = None
        _require(chapter.apply_button.isEnabled() and chapter._ai_prepared_token is not None,
            'Provider proposal was not admitted by native Preview: ' + chapter.ai_status.text())
        _require(_head_identity(chapter) == head and chapter.description.fingerprint == fingerprint
            and document.read_bytes() == saved and _row_fields(chapter, main.uuid)['x'] == -33.,
            'AI Preview changed published authoring state or saved bytes')
        data['metrics']['ai_preview_private'] = True
        data['metrics']['ai_preview_details'] = chapter.preview_details.toPlainText()
        _capture(view, work / 'chapter-ai-preview.png', data, 'chapter_ai_preview')
        _require(proposal is not None and proposal['edits'] == [
            {'entity_id': main.uuid, 'field': 'x', 'value': -32.5}],
            'Provider did not propose exactly the requested absolute coordinate; proposal was not applied')
        chapter.apply_button.click()
        _idle(app, chapter)
        _require(_row_fields(chapter, main.uuid)['x'] == -32.5 and document.read_bytes() == saved,
            'Provider output failed requested coordinate or Apply/Save separation')
        chapter.save_world()
        _idle(app, chapter)
        data['checks'].append('Production QtNetwork inventory/capability/generation and native proposal admission; explicit Apply/Save')
        if fixture:
            data['http_paths'] = fixture.paths[:]
            request = fixture.chat_request
            _require(request is not None and request['keep_alive'] == 0 and request['stream'] is False,
                'Fixture did not exercise the production bounded request')
            authoring = json.loads(request['messages'][1]['content'])['authoring_data']
            _require([row['uuid'] for row in authoring['objects']] == [main.uuid],
                'AI request was not restricted to the selected object')

        _probe_viewport(app, chapter, work / 'chapter-render', bundle, data, 'chapter_viewport')
        chapter.start_play()
        _wait(app, lambda: chapter.play.state == 'ready', 'Native isolated Play did not become ready', chapter)
        _bundle_executable(chapter.play._process.program(), bundle, data, 'chapter_player')
        data['observed_process_ids']['chapter_player'] = chapter.play.process_id
        scratch = chapter.play.workspace_path
        _require(scratch is not None and scratch.is_dir() and not scratch.is_relative_to(chapter_root),
            'Play did not own isolated scratch storage')
        _require(chapter.play.snapshot.fingerprint == chapter.description.fingerprint
            and chapter.play.snapshot.payload == (scratch / 'chapter.aibd').read_bytes(),
            'Play did not consume the immutable native content export')
        saved = document.read_bytes()
        expected_head, expected_fingerprint = _saved_identity(chapter), chapter.description.fingerprint
        # Keep both real children alive so project close must drain and join
        # owner, renderer and Play before the workspace is considered closed.
        chapter.open_viewport()
        _wait(app, lambda: chapter.viewport.state == 'ready', 'Chapter viewport did not reopen', chapter)
        _capture(view, work / 'chapter-play.png', data, 'chapter_creator')
        _close_document(app, chapter)
        data['play_scratch_removed'] = not scratch.exists()
        data['metrics']['play_stop'] = chapter.play.last_result
        _require(data['play_scratch_removed'] and chapter.play.last_result
            and chapter.play.last_result['graceful'] and chapter.play.last_result['saved'],
            'Play close did not save, drain, join and remove its owned scratch')
        _require(document.read_bytes() == saved, 'Play modified the authored chapter save')
        chapter.open_project(chapter_root)
        _idle(app, chapter)
        _require(_saved_identity(chapter) == expected_head
            and chapter.description.fingerprint == expected_fingerprint
            and _row_fields(chapter, fixture_id) == expected
            and _row_fields(chapter, main.uuid)['x'] == -32.5,
            'Saved typed authoring did not reopen identically')
        data['metrics']['saved_reopen_matches'] = True
        _close_document(app, chapter)
        data['checks'].append('Native chapter capture and isolated Play; project close joined owner, viewport and player; saved authoring reopened')
        data['status'] = 'passed'
    except Exception as exc:
        data['error'] = str(exc)
    finally:
        cleanup_errors = []
        if view is not None:
            for child in (view.creator_view, view.content_view):
                if child is None:
                    continue
                try:
                    if hasattr(child, 'cancel_ai_generation'):
                        child.cancel_ai_generation('Release smoke completed')
                    _wait(app, lambda: not child.busy and not child.client.pending_count,
                        'Pending authoring operation did not drain', child, seconds=15)
                    if child.definition is not None or child.client.state != 'closed':
                        child.close_project(discard=True)
                    _wait(app, lambda: child.client.state == 'closed' and child.viewport.state == 'closed'
                        and (not hasattr(child, 'play') or child.play.state == 'closed'),
                        'Owned native processes did not join during cleanup', child, seconds=20)
                except Exception as exc:
                    cleanup_errors.append(str(exc))
                    # Only owned children are eligible for forced termination.
                    child.viewport._shutdown()
                    if hasattr(child, 'play'):
                        child.play._shutdown()
                    child.client.abort('Release smoke cleanup')
            data['final_process_ids'] = {
                label: {'owner': child.client.process_id, 'viewport': child.viewport.process_id,
                    'play': child.play.process_id if hasattr(child, 'play') else 0}
                for label, child in (('numeric', view.creator_view), ('chapter', view.content_view))
                if child is not None}
            data['all_owned_processes_joined'] = bool(data['final_process_ids']) and all(
                pid == 0 for states in data['final_process_ids'].values() for pid in states.values())
            if data['all_owned_processes_joined']:
                view.close()
                view.deleteLater()
                app.processEvents()
        if fixture is not None:
            data['fixture_thread_joined'] = fixture.close()
            if not data['fixture_thread_joined']:
                cleanup_errors.append('Deterministic HTTP fixture thread did not join')
        if bus is not None:
            bus.shutdown()
        if cleanup_errors:
            data['status'] = 'failed'
            data['cleanup_errors'] = cleanup_errors
        if data['status'] == 'passed' and not data['all_owned_processes_joined']:
            data['status'], data['error'] = 'failed', 'Owned native processes remain alive'
        data['elapsed_seconds'] = round(time.monotonic() - started, 3)
        data['completed_at'] = datetime.now(timezone.utc).isoformat()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return 0 if data['status'] == 'passed' else 2


def release_smoke_main(argv) -> int:
    """Small early CLI dispatch, before the application's service/view imports."""
    parser = argparse.ArgumentParser(description='Explicit native release acceptance')
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--game-build-smoke', type=Path)
    target.add_argument('--creator-release-smoke', type=Path)
    parser.add_argument('--creator-smoke-provider', choices=('fixture', 'ollama'), default='fixture')
    parser.add_argument('--creator-smoke-model')
    parser.add_argument('--creator-smoke-url')
    options = parser.parse_args(argv)
    if options.game_build_smoke is not None:
        return run_game_release_smoke(options.game_build_smoke)
    return run_creator_release_smoke(options.creator_release_smoke,
        provider=options.creator_smoke_provider, model=options.creator_smoke_model,
        endpoint=options.creator_smoke_url)
