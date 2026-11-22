"""Explicit local-only single-file proposals with a durable pre-request snapshot."""
from __future__ import annotations
import base64
import importlib.util
import json
import os
from pathlib import Path
import threading
import time

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QPlainTextEdit, QFileDialog, QMessageBox)
from native_studio.owned_process import OwnedProcess


def prepare_local_proposal(path, root, *, endpoint, model, journal=None, infer=None):
    root = Path(root).resolve(strict=True)
    worker = root / 'runtime/devtools/native_local_refactor_worker.py'
    if infer is not None or journal is not None:
        # Controlled source tests inject inference/storage. Production native
        # requests use the explicit owned worker below, never a backend import.
        spec = importlib.util.spec_from_file_location('_aibs_local_proposal_worker', worker)
        if not worker.is_file():
            # Isolated test roots keep their database/source local while using
            # the one canonical reviewed worker implementation.
            worker = Path(__file__).resolve().parents[1] / 'runtime/devtools/native_local_refactor_worker.py'
            spec = importlib.util.spec_from_file_location('_aibs_local_proposal_worker', worker)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.prepare_source(path, root, endpoint=endpoint, model=model, journal=journal, infer=infer)
    interpreter = root / 'runtime/recovery-20261110/Scripts/python.exe'
    if not worker.is_file() or not interpreter.is_file():
        raise RuntimeError('The configured local proposal worker/runtime is unavailable')
    request = json.dumps(dict(path=str(path), root=str(root), endpoint=endpoint, model=model)).encode('utf-8') + b'\n'
    if len(request) > 8192:
        raise ValueError('Local proposal request exceeds its bounded transport')
    process = OwnedProcess((str(interpreter), '-I', '-B', str(worker)), str(root), dict(os.environ))
    chunks = {'stdout': bytearray(), 'stderr': bytearray()}
    readers = []
    limit = 2 * 1024 * 1024
    def read(stream, name):
        while True:
            data = stream.read(65536)
            if not data:
                return
            room = max(0, limit - len(chunks[name]))
            chunks[name].extend(data[:room])
    try:
        for stream, name in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
            thread = threading.Thread(target=read, args=(stream, name), daemon=False)
            readers.append(thread)
            thread.start()
        process.stdin.write(request)
        process.stdin.close()
        process.stdin = None
        deadline = time.monotonic() + 190
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        code = process.poll()
    finally:
        drained = process.close()
        for thread in readers:
            thread.join()
    if code != 0 or not drained:
        raise RuntimeError('Local proposal worker did not complete; any committed snapshot remains retained')
    try:
        packet = json.loads(chunks['stdout'].decode('utf-8'))
        if packet['status'] != 'completed':
            raise ValueError('Incomplete worker response')
        result = packet['result']
        for key in ('original_bytes', 'candidate_bytes'):
            result['proposal'][key] = base64.b64decode(result['proposal'][key], validate=True)
        return result
    except (ValueError, KeyError, TypeError):
        raise RuntimeError('Local proposal worker response was not verified') from None


class LocalRefactorPanel(QWidget):
    def __init__(self, bus, root, parent=None):
        super().__init__(parent)
        self.setStyleSheet('QLineEdit, QComboBox, QPlainTextEdit {'
            'background: #111827; color: #e5e7eb; border: 1px solid #475569; padding: 3px;}')
        self.bus, self.root = bus, Path(root)
        self._result = None
        self._busy = False
        self._task = None
        bus.admission_changed.connect(self._admission_changed)
        layout = QVBoxLayout(self)
        intro = QLabel('Prepare one stateless Python refactoring proposal using the selected local Ollama instance. '
            'The original bytes are committed to a private SQLite WAL journal before the request. '
            'No cloud fallback, automatic source replacement or Git rollback.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.path = QLineEdit()
        form.addRow('Python source', self.path)
        choose = QPushButton('Choose source file')
        choose.clicked.connect(self.choose_source)
        form.addRow(choose)
        self.model = QLineEdit('stehouwer_llm:latest')
        form.addRow('Local model', self.model)
        self.endpoint = QComboBox()
        self.endpoint.addItems(['http://127.0.0.1:11434', 'http://127.0.0.1:11435'])
        form.addRow('Ollama endpoint', self.endpoint)
        layout.addLayout(form)
        self.start = QPushButton('Prepare local proposal')
        self.start.clicked.connect(self.prepare)
        layout.addWidget(self.start)
        self.status = QLabel('Idle. No inference has been requested.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumBlockCount(5000)
        layout.addWidget(self.preview, 1)
        self.export = QPushButton('Export candidate to a new file')
        self.export.setEnabled(False)
        self.export.clicked.connect(self.export_candidate)
        layout.addWidget(self.export)
        note = QLabel('Temperature 0 controls sampling; syntax checks do not establish semantic equivalence. '
            'Existing manuscripts, screenplay recovery and the selected primary chat provider retain their own contracts.')
        note.setWordWrap(True)
        layout.addWidget(note)

    def choose_source(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose one Python source', str(self.root), 'Python (*.py)')
        if path:
            self.path.setText(path)

    def prepare(self):
        if self._busy:
            return
        path, model, endpoint = self.path.text(), self.model.text(), self.endpoint.currentText()
        self._busy = True
        self.start.setEnabled(False)
        self.export.setEnabled(False)
        self._result = None
        self.preview.clear()
        self._task = None
        self.status.setText('Queued for local proposal preparation; the original file will stay unchanged.')
        try:
            self._task = self.bus.submit(prepare_local_proposal, path, self.root, endpoint=endpoint, model=model,
                            on_result=self._ready, on_error=self._failed)
        except (ValueError, RuntimeError) as exc:
            self._failed(str(exc))

    def _ready(self, result):
        self._busy = False
        self.start.setEnabled(True)
        self._result = result
        proposal = result['proposal']
        self.preview.setPlainText(proposal['candidate_bytes'].decode(proposal['source_encoding']))
        self.status.setText('Proposal journaled and syntax checked. Original unchanged. Semantic behavior remains unverified.')
        self.export.setEnabled(True)

    def _admission_changed(self, snapshot):
        if self._busy and self._task is not None and self._task.cancel_event.is_set():
            self._busy = False
            self.start.setEnabled(True)
            self.status.setText('Preparation cancelled. Any committed private snapshot is retained; source unchanged.')

    def _failed(self, message):
        self._busy = False
        self.start.setEnabled(True)
        self.status.setText('Proposal did not complete: ' + message[:300])

    def export_candidate(self):
        if not self._result:
            return
        proposal = self._result['proposal']
        default = Path(proposal['source_path']).with_suffix('.proposal.py')
        path, _ = QFileDialog.getSaveFileName(self, 'Export candidate as a new file', str(default), 'Python (*.py)')
        if not path:
            return
        try:
            # The journal already contains the exact original and candidate.
            # Exclusive create prevents replacing any pre-existing source/data.
            with open(path, 'xb') as stream:
                stream.write(proposal['candidate_bytes'])
                stream.flush()
                import os
                os.fsync(stream.fileno())
            self.status.setText('Candidate exported to a new file. Original unchanged.')
        except OSError as exc:
            QMessageBox.warning(self, 'Export not completed', type(exc).__name__ + ': existing files are never overwritten here.')
