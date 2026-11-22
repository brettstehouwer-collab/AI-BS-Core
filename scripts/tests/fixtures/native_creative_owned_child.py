"""Fixed synthetic candidate; argv carries only phase, ports and test directory."""
from pathlib import Path
import hashlib
import json
import os
import socket
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
MARKER = 'NATIVE OWNED FIXTURE EDIT'
HTTP_PATHS = frozenset({'/api/screenwriting/native/redeem', '/api/screenwriting/read',
    '/api/screenwriting/write', '/api/screenwriting/export/fdx', '/api/screenwriting/export/pdf'})


def send(connection, value):
    raw = json.dumps(value, ensure_ascii=True).encode('ascii') + b'\n'
    if len(raw) > 8192: raise ValueError()
    connection.sendall(raw)


def main():
    phase, step, directory, connection = 'unknown', 'arguments', None, None
    diagnostics, http_events = False, []
    try:
        diagnostics = len(sys.argv) == 6 and sys.argv[5] == '--diagnostics'
        if (len(sys.argv) != (6 if diagnostics else 5)
                or sys.argv[1] not in {'edit-save', 'reopen-export'}): raise ValueError()
        phase = sys.argv[1]
        port, coordination_port = int(sys.argv[2]), int(sys.argv[3])
        if not 1 <= port <= 65535 or port == 8080 or not 1 <= coordination_port <= 65535: raise ValueError()
        directory = Path(sys.argv[4]).resolve()
        if not directory.is_dir() or directory.is_symlink(): raise ValueError()
        sys.path[:0] = [str(ROOT), str(ROOT / 'runtime/recovery-20261110/Lib/site-packages')]
        import httpx
        from native_studio.creative_session import CreativeSession, bootstrap_native_session
        paths = []
        class EphemeralTransport(httpx.BaseTransport):
            def __init__(self): self.inner = httpx.HTTPTransport(retries=0)
            def handle_request(self, request):
                if (request.url.scheme != 'http' or request.url.host != '127.0.0.1'
                        or request.url.port != 8080 or not request.url.path.startswith('/api/screenwriting/')):
                    raise AssertionError('Synthetic origin mismatch')
                if len(paths) >= 64: raise AssertionError('Synthetic request cap')
                paths.append(request.url.path)
                request.url = request.url.copy_with(port=port)
                request.headers['host'] = f'127.0.0.1:{port}'
                if not diagnostics:
                    return self.inner.handle_request(request)
                observation = dict(path=request.url.path if request.url.path in HTTP_PATHS else 'OTHER',
                                   status=None, exception_class=None)
                try:
                    response = self.inner.handle_request(request)
                    observation['status'] = response.status_code
                    return response
                except BaseException as error:
                    observation['exception_class'] = type(error).__name__[:80]
                    raise
                finally:
                    if len(http_events) < 64: http_events.append(observation)
            def close(self): self.inner.close()
        def session_factory():
            return CreativeSession(headers_provider=lambda: {'X-API-Key': 'synthetic-owned-workflow'},
                                   transport=EphemeralTransport())
        step = 'pipe_bootstrap_redeem'
        session, packet = bootstrap_native_session([sys.argv[0], '--native-creative-bootstrap'],
            sys.stdin.buffer, session_factory=session_factory)
        before_qt = not any(name.startswith('PyQt6') for name in sys.modules)
        os.write(1, b'fixed synthetic stdout sink probe\n')
        os.write(2, b'fixed synthetic stderr sink probe\n')
        connection = socket.create_connection(('127.0.0.1', coordination_port), timeout=10)
        connection.settimeout(50)
        send(connection, dict(kind='ready', phase=phase, pid=os.getpid(), bootstrap_before_qt=before_qt))
        if connection.recv(1) != b'R': raise ValueError()
        step = 'qt_initialization'
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        qt_site = ROOT / 'runtime/qt-layout-check-20261111/Lib/site-packages'
        sys.path.insert(0, str(qt_site))
        dll_directory = os.add_dll_directory(str(qt_site / 'PyQt6/Qt6/bin'))
        from unittest.mock import patch
        from PyQt6.QtGui import QFontDatabase, QTextCursor
        from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
        from native_studio.screenplay_client import DraftSession, ScreenplayClient
        from native_studio.native_creative_entry import create_native_creative_window
        import native_studio.screenwriting_view as writer
        app = QApplication([]); app.setQuitOnLastWindowClosed(False)
        for filename in ('segoeui.ttf', 'cour.ttf'):
            path = Path('C:/Windows/Fonts') / filename
            if path.is_file(): QFontDatabase.addApplicationFont(str(path))
        warnings = []
        def client(**kwargs): return ScreenplayClient(transport=EphemeralTransport(), **kwargs)
        def pump(predicate, seconds=12):
            deadline = time.monotonic() + seconds
            while not predicate():
                if time.monotonic() >= deadline: raise TimeoutError()
                app.processEvents(); time.sleep(.005)
            app.processEvents()
        with patch.object(writer, 'ScreenplayClient', side_effect=client), \
             patch.object(writer, 'DraftSession', side_effect=lambda: DraftSession(directory / 'recovery')), \
             patch.object(QMessageBox, 'warning', side_effect=lambda *args: warnings.append(True)), \
             patch.object(QMessageBox, 'information'), \
             patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            step = 'initial_bound_read'
            window = create_native_creative_window(session, packet); window.show(); view = window.writer
            pump(lambda: not view._writer_busy)
            if not view._delegated_editor_ready() or view.editor.isReadOnly() or warnings: raise PermissionError()
            result = dict(kind='complete', phase=phase, pid=os.getpid(), actual_rich_writer=True,
                          only_writing_page=view.suite_stack.count() == 1, exports={})
            if phase == 'edit-save':
                step = 'edit_and_save'; old_revision = view._draft.revision
                view.editor.moveCursor(QTextCursor.MoveOperation.End)
                view._insert_element_text('\n\n' + MARKER + '\n')
                if not view._draft.dirty: raise AssertionError()
                view._save_script(); pump(lambda: not view._writer_busy)
                if (view._draft.dirty or view._draft.uncertain or warnings
                        or view._draft.revision == old_revision): raise AssertionError()
                result['saved_revision'] = view._draft.revision
                result['saved_edit_present'] = MARKER in view.editor.toPlainText()
            else:
                step = 'fresh_process_reopen'
                result['reopened_edit_present'] = MARKER in view.editor.toPlainText()
                if not result['reopened_edit_present']: raise AssertionError()
                for fmt, button in (('fdx', view.btn_export_fdx), ('pdf', view.btn_export_pdf)):
                    step = 'explicit_reflow_export_' + fmt
                    action = next(a for a in button.menu().actions() if 'Reformatted' in a.text())
                    if not action.isVisible() or not action.isEnabled(): raise AssertionError()
                    target = directory / ('reformatted.' + fmt)
                    if target.exists(): raise AssertionError()
                    with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(target), '')): action.trigger()
                    pump(lambda: not view._writer_busy)
                    if warnings or not target.is_file(): raise AssertionError()
                    raw = target.read_bytes()
                    if fmt == 'fdx':
                        import xml.etree.ElementTree as ET
                        text = ' '.join(ET.fromstring(raw).itertext())
                    else:
                        from pypdf import PdfReader
                        text = ' '.join(page.extract_text() or '' for page in PdfReader(target).pages)
                    if MARKER not in ' '.join(text.split()): raise AssertionError()
                    result['exports'][fmt] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                                                  edit_present=True, profile='explicit_reflow')
            step = 'gui_close_and_drain'; window.close()
            pump(lambda: window._close_state == 'READY' and window.bus.is_drained)
            result.update(gui_worker_drained=window.bus.is_drained, session_cleared_after_close=session._lease is None,
                request_paths=paths, forbidden_modules_loaded=[name for name in (
                    'native_studio.creation_suite_subtools', 'native_studio.screenwriting_modals') if name in sys.modules])
            with (directory / 'result.json').open('x', encoding='utf-8') as stream: json.dump(result, stream, indent=2)
            send(connection, result)
            if connection.recv(1) != b'X': raise ValueError()
        dll_directory.close(); connection.close(); return 0
    except BaseException as error:
        frames = traceback.extract_tb(error.__traceback__)
        failure = dict(kind='failure', phase=phase, step=step, exception_class=type(error).__name__,
                       location=dict(file=Path(frames[-1].filename).name, line=frames[-1].lineno) if frames else None)
        if diagnostics: failure['http_events'] = http_events
        if directory is not None and directory.is_dir():
            path = directory / 'failure.json'
            if not path.exists():
                with path.open('x', encoding='utf-8') as stream: json.dump(failure, stream, indent=2)
        if connection is not None:
            try: send(connection, failure); connection.close()
            except OSError: pass
        return 2


if __name__ == '__main__': raise SystemExit(main())
