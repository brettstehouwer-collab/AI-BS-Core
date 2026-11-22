"""Opt-in synthetic frozen writer acceptance; never imported by ordinary startup.

Each phase owns a new directory named for its phase under one backups run.
The authenticated launcher must bind PROJECT to its disposable synthetic store.
No source document, credential, or document text is included in receipts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path('C:/AI-BS/backups')
PHASES = ('preserve', 'restore-save', 'reopen-export', 'reject-export', 'fail-save')
PROJECT = 'AIBS_Writer_Acceptance'
MARKER = 'AIBS synthetic writer acceptance'
EDIT = ' acceptance edit'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def checked_path(value):
    path = Path(value)
    need(path.is_absolute() and '..' not in path.parts, 'Absolute canonical path required')
    need(path.is_relative_to(ROOT) and path != ROOT, 'Owned backups output required')
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        need(not item.is_symlink() and not (getattr(info, 'st_file_attributes', 0) & 0x400),
             'Redirected paths forbidden')
    need(path.resolve() == path, 'Canonical path required')
    return path


def parse_options(argv):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--packaged-writer-acceptance', action='store_true', required=True)
    parser.add_argument('--native-creative-pipe-bootstrap', action='store_true', required=True)
    parser.add_argument('--writer-acceptance-phase', choices=PHASES, required=True)
    parser.add_argument('--writer-acceptance-output', required=True)
    args = parser.parse_args(argv)
    # argparse accepts repeated options; an acceptance invocation must be exact.
    need(len(argv) == 6, 'Exact acceptance arguments required')
    args.output = checked_path(args.writer_acceptance_output)
    need(args.output.name == args.writer_acceptance_phase, 'Output leaf must equal phase')
    need(args.output.parent.is_dir() and not args.output.exists(), 'Existing run and new phase required')
    return args


def receipt(directory, name, value):
    checked_path(directory)
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf8')
    need(len(raw) <= 16384, 'Bounded receipt required')
    with (directory / name).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def bounded_read(path):
    checked_path(path)
    with path.open('rb') as stream:
        raw = stream.read(4 * 1024 * 1024 + 1)
    need(len(raw) <= 4 * 1024 * 1024, 'Synthetic fixture too large')
    return raw


def validate_synthetic(project, content):
    need(project == PROJECT and isinstance(content, str) and MARKER in content
         and len(content) < 65536, 'Fixed bounded synthetic fixture required')


def run_writer(session, packet, options):
    """Called only after existing authenticated pipe bootstrap succeeds."""
    need(getattr(sys, 'frozen', False), 'Frozen acceptance only')
    need(packet.project == PROJECT, 'Owned synthetic project required')
    directory = checked_path(options.output)
    directory.mkdir()  # create-only, after authentication
    phase = options.writer_acceptance_phase
    record = {'schema': 1, 'phase': phase, 'status': 'INCOMPLETE', 'pid': os.getpid(),
              'ordinary_input_verified': False, 'real_owner_verified': False}
    receipt(directory, 'started.json', record)
    window = app = None
    step = 'imports'
    try:
        if phase in ('restore-save', 'reopen-export'):
            previous_phase = 'preserve' if phase == 'restore-save' else 'restore-save'
            previous = json.loads(bounded_read(directory.parent / previous_phase / 'result.json'))
            need(previous.get('schema') == 1 and previous.get('phase') == previous_phase
                 and previous.get('status') == 'PASS', 'Prior phase must pass')
        # This authenticated synthetic acceptance mode owns no desktop window.
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from unittest.mock import patch
        from PyQt6 import sip
        from PyQt6.QtGui import QTextCursor
        from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
        from native_studio.native_creative_entry import create_native_creative_window, dispose_closed_native_creative_window
        from native_studio.screenplay_client import DraftSession
        import native_studio.screenwriting_view as writer

        def pump(predicate, seconds=20):
            deadline = time.monotonic() + seconds
            while not predicate():
                need(time.monotonic() < deadline, 'Timed out: ' + step)
                app.processEvents()
                time.sleep(.005)
            app.processEvents()

        recovery = checked_path(directory / 'recovery' if phase in ('reject-export', 'fail-save')
                                else directory.parent / 'preserve' / 'recovery')
        warnings = []

        def capture_warning(*args):
            need(len(args) >= 3 and isinstance(args[2], str) and len(args[2]) <= 8192,
                 'Bounded warning message required')
            warnings.append(hashlib.sha256(args[2].encode('utf8')).hexdigest())

        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        with patch.object(writer, 'DraftSession', side_effect=lambda: DraftSession(recovery)), \
                patch.object(QMessageBox, 'warning', side_effect=capture_warning), \
                patch.object(QMessageBox, 'information'), \
                patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            step = 'load synthetic rich project'
            window = create_native_creative_window(session, packet)
            window.show()
            view = window.writer
            pump(lambda: not view._writer_busy)
            need(view._delegated_editor_ready() and not view.editor.isReadOnly(), 'Editor unavailable')
            draft = view._draft
            need(draft.project == PROJECT and draft.rich is not None and not draft.dirty,
                 'Confirmed clean rich fixture required')
            validate_synthetic(draft.project, view.editor.toPlainText())
            revision = draft.revision
            if phase == 'reopen-export':
                need(previous.get('saved_revision_sha256') == hashlib.sha256(revision.encode('utf8')).hexdigest(),
                     'Fresh saved revision differs')
            with patch.object(session._channel, 'request', wraps=session._channel.request) as requests:
                if phase in ('preserve', 'fail-save'):
                    step = 'edit and preserve'
                    need(EDIT not in view.editor.toPlainText(), 'Fresh fixture required')
                    blocks = draft.rich.document['blocks']
                    index = next(i for i, block in enumerate(blocks) if block['type'] == 'Action' and MARKER in block['text'])
                    position = draft.rich.projection_spans[index]['start'] + len(blocks[index]['text'])
                    cursor = view.editor.textCursor()
                    cursor.setPosition(len(view.editor.toPlainText()[:position].encode('utf-16-le')) // 2)
                    view.editor.setTextCursor(cursor)
                    view.editor.insertPlainText(EDIT)
                    need(draft.dirty and not draft.rich.blocked_reason, 'Rich edit failed')
                    need(view._preserve_native_draft(), 'Recovery preservation failed')
                    raw = bounded_read(draft.recovery_path)
                    saved = json.loads(raw)
                    need(saved['schema'] == 3 and saved['rich_draft'] == draft.rich.recovery_payload(), 'Recovery mismatch')
                    record['recovery_sha256'] = hashlib.sha256(raw).hexdigest()
                    if phase == 'fail-save':
                        step = 'one synthetic refused save through real pipe'
                        first_path = draft.recovery_path
                        edited = view.editor.toPlainText()
                        view._save_script()
                        pump(lambda: not view._writer_busy)
                        need(len(warnings) == 1 and draft.dirty and draft.uncertain,
                             'Refused save must remain dirty/uncertain with one warning')
                        need(view.editor.toPlainText() == edited and draft.revision == revision,
                             'Refused save changed draft or confirmed revision')
                        need(bounded_read(first_path) == raw, 'Prior recovery was replaced')
                        need(view._preserve_native_draft(), 'Failed-save recovery not retained')
                        retained = json.loads(bounded_read(draft.recovery_path))
                        need(retained['content'] == edited
                             and retained['rich_draft'] == draft.rich.recovery_payload(),
                             'Recovery must retain complete edited rich draft')
                        record.update(expected_save_refusal=True, dirty=True, uncertain=True,
                                      revision_unchanged=True, edited_content_retained=True,
                                      previous_recovery_unchanged=True,
                                      complete_rich_recovery_retained=True, warning_count=1,
                                      warning_sha256=warnings[0])
                elif phase == 'restore-save':
                    step = 'restore retained recovery'
                    paths = list(recovery.glob('*.json'))
                    need(len(paths) == 1, 'Exactly one preserved recovery required')
                    raw = bounded_read(paths[0])
                    saved = json.loads(raw)
                    need(previous.get('recovery_sha256') == hashlib.sha256(raw).hexdigest(), 'Prior recovery differs')
                    need(saved['project'] == PROJECT and saved['baseline'] == draft.content and MARKER in saved['content'], 'Recovery fixture differs')
                    with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(paths[0]), 'Recovery copies (*.json)')):
                        view.btn_recovery.click()
                        app.processEvents()
                    need(not requests.call_count and draft.dirty and draft.rich.recovery_payload() == saved['rich_draft'], 'Restore failed')
                    need(view.editor.document().isUndoAvailable(), 'Recovery Undo unavailable')
                    view.editor.undo(); app.processEvents()
                    need(view.editor.toPlainText() == saved['baseline'], 'Recovery Undo failed')
                    view.editor.redo(); app.processEvents()
                    need(view.editor.toPlainText() == saved['content'], 'Recovery Redo failed')
                    step = 'explicit CAS save'
                    view._save_script()
                    pump(lambda: not view._writer_busy)
                    need(not draft.dirty and not draft.uncertain and draft.revision != revision, 'Save unconfirmed')
                    need(bounded_read(paths[0]) == raw, 'Preserved recovery changed')
                    record['saved_revision_sha256'] = hashlib.sha256(draft.revision.encode('utf8')).hexdigest()
                else:
                    step = 'export typed PDF through menu'
                    need(EDIT in view.editor.toPlainText(), 'Saved edit missing on fresh reopen')
                    if phase == 'reject-export':
                        need(MARKER + EDIT in view.editor.toPlainText(), 'Exact synthetic edited marker required')
                        titles = draft.rich.document['title_page']
                        need(isinstance(titles, list) and 1 <= len(titles) <= 5
                             and any('Strikeout' in run['attributes'].get('Style', '').split('+')
                                     for title in titles for run in title['runs']),
                             'Unsupported synthetic title Strikeout fixture required')
                        before = (view.editor.toPlainText(), draft.revision, draft.dirty, draft.content)
                        need(not warnings, 'Warning occurred before rejection attempt')
                    target = directory / 'typed-output.pdf'
                    with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(target), 'PDF (*.pdf)')):
                        action = next(a for a in view.btn_export_pdf.menu().actions() if 'Typed FDX professional PDF' in a.text())
                        need(action.isEnabled() and action.isVisible(), 'Typed menu unavailable')
                        action.trigger()
                        pump(lambda: not view._writer_busy, 45)
                    if phase == 'reject-export':
                        need(len(warnings) == 1 and not target.exists(), 'Expected one warning and no output')
                        need((view.editor.toPlainText(), draft.revision, draft.dirty, draft.content) == before,
                             'Rejected export changed retained document state')
                        record.update(expected_rejection=True, warning_count=1,
                                      warning_sha256=warnings[0], output_file_written=False,
                                      document_unchanged=True, revision_unchanged=True,
                                      dirty_state_unchanged=True)
                    else:
                        raw = bounded_read(target)
                        need(raw.startswith(b'%PDF-') and draft.revision == revision, 'PDF delivery failed')
                        record.update(export_bytes=len(raw), export_sha256=hashlib.sha256(raw).hexdigest())
                operations = [call.args[0] for call in requests.call_args_list]
                record['host_operations'] = operations
                expected = {'preserve': [], 'restore-save': ['save'],
                            'reopen-export': ['read', 'export_pdf', 'read'],
                            'reject-export': ['read', 'export_pdf'], 'fail-save': ['save']}[phase]
                need(operations == expected, 'Unexpected host operation')
            need(len(warnings) == (1 if phase in ('reject-export', 'fail-save') else 0), 'Unexpected writer warning count')
            step = 'normal close and drain'
            window.close()
            pump(lambda: window._close_state == 'READY' and window.bus.is_drained)
            need(session._lease is None and not session._bootstrap_resources._fds, 'Session close incomplete')
            dispose_closed_native_creative_window(window, app)
            sip.delete(app)
            window = app = None
        record.update(status='PASS', normal_close=True, drained=True)
        receipt(directory, 'result.json', record)
        return 0
    except Exception as error:
        receipt(directory, 'failure.json', dict(record, status='FAIL', step=step, exception=type(error).__name__))
        # Never label destruction of a live worker as normal close. Leave the
        # owned GUI available and the failure visible if its close barrier stalls.
        if window is not None and app is not None:
            window.setWindowTitle('AI-BS writer acceptance FAILED — see failure.json')
            window.close()
            try:
                pump(lambda: window._close_state == 'READY' and window.bus.is_drained)
                dispose_closed_native_creative_window(window, app)
                sip.delete(app)
            except Exception:
                app.exec()
        return 2


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    options = parse_options(argv)
    from native_studio.native_creative_entry import main as creative_main
    return creative_main([sys.argv[0], '--native-creative-pipe-bootstrap'],
                         run_writer=lambda session, packet: run_writer(session, packet, options))


def run_writer_acceptance(session, packet):
    """Lazy production dispatch callback; bootstrap has already authenticated."""
    return run_writer(session, packet, parse_options(list(sys.argv[1:])))
