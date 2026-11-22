"""Scratchpad adapter over the existing shared owned-process controller."""
from pathlib import Path
import hashlib
import json
import sys
import uuid
from PyQt6.QtCore import QObject, pyqtSignal
from native_studio.process_batch import JobSpec
from native_studio.process_batch_view import shared_batch_controller
from native_studio.screenplay_client import _private_recovery_directory, write_new_export
from native_studio.syntax_worker import MAX_BYTES, STORE


class SyntaxCheck(QObject):
    completed = pyqtSignal(object)

    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.controller = shared_batch_controller(bus)
        self.controller.changed.connect(self._changed)
        self.pending = None
        self.stopping = False

    def submit(self, text):
        if self.stopping or self.pending or not self.controller.is_drained:
            raise ValueError('Wait for the current background batch to drain.')
        raw = text.encode('utf-8')
        if len(raw) > MAX_BYTES:
            raise ValueError('Syntax check supports up to one MiB; the editor is unchanged.')
        digest = hashlib.sha256(raw).hexdigest()
        operation = uuid.uuid4().hex
        directory = STORE / operation
        _private_recovery_directory(directory, STORE)
        path = directory / 'source.txt'
        write_new_export(path, raw)
        if getattr(sys, 'frozen', False):
            executable = Path(sys.executable)
            arguments = ('--scratchpad-syntax-worker', str(path), digest)
        else:
            executable = Path(sys.executable)
            arguments = ('-I', '-B', str(Path(__file__).with_name('syntax_worker.py')),
                         '--scratchpad-syntax-worker', str(path), digest)
        job = JobSpec('syntax-' + operation, str(executable), arguments, str(directory), timeout_seconds=10)
        self.pending = {'job_id': job.job_id, 'sha256': digest, 'bytes': len(raw)}
        try:
            self.controller.submit([job])
        except Exception:
            self.pending = None
            raise
        return digest

    def _changed(self, snapshot):
        if self.pending and snapshot.get('is_drained'):
            row = next((row for row in snapshot['jobs'] if row['job_id'] == self.pending['job_id']), None)
            if row is not None:
                self._event({'kind': 'finished', **row})

    def _event(self, event):
        pending = self.pending
        if not pending or event.get('job_id') != pending['job_id'] or event.get('kind') != 'finished':
            return
        self.pending = None
        result = {**pending, 'status': 'unavailable', 'executed': False}
        if (event.get('state') == 'passed' and event.get('exit_code') == 0
                and event.get('job_drained') and not event.get('output_truncated')):
            try:
                raw = event['output']
                if len(raw.encode('utf-8')) > 4096:
                    raise ValueError('Bounded syntax receipt required')
                data = json.loads(raw)
                if (type(data) is not dict or data.get('schema') != 1 or data.get('sha256') != pending['sha256']
                        or data.get('bytes') != pending['bytes'] or data.get('executed') is not False
                        or data.get('status') not in ('valid', 'invalid')):
                    raise ValueError('Syntax receipt identity mismatch')
                if data['status'] == 'invalid':
                    if data.get('error') not in ('SyntaxError', 'IndentationError', 'TabError', 'ValueError', 'RecursionError'):
                        raise ValueError('Unexpected compiler error')
                    for key in ('line', 'column'):
                        if data.get(key) is not None and (type(data[key]) is not int or not 0 <= data[key] <= MAX_BYTES):
                            raise ValueError('Invalid compiler location')
                result = {**result, **{key: data[key] for key in ('status', 'error', 'line', 'column') if key in data}}
            except (KeyError, TypeError, ValueError, UnicodeError):
                pass
        if not self.stopping:
            self.completed.emit(result)

    def shutdown(self):
        # The shared controller is stopped/joined by the existing window barrier.
        self.stopping = True
