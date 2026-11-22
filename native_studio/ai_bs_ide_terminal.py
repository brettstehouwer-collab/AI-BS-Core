"""Queued native shell terminal with a local, JobObject-owned shell helper.

QProcess supplies asynchronous transport. Its pure-stdlib helper starts the actual
shell suspended inside the existing Windows JobObject before it executes. This
is lifetime containment, not a filesystem/network sandbox. WSL Windows process
drain does not certify that every Linux descendant has stopped.
"""
from __future__ import annotations
import codecs
import base64
from collections import deque
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time


def shell_argv(runtime, command, cwd):
    """Return literal argument arrays, never a cmd.exe string or interpolated cd."""
    if runtime == 'PowerShell':
        executable = str(Path(os.environ.get('SystemRoot', r'C:\Windows')) /
                         'System32/WindowsPowerShell/v1.0/powershell.exe')
        encoding = '$OutputEncoding=[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); '
        return [executable, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-NonInteractive',
                '-Command', encoding + command]
    if runtime == 'WSL':
        executable = shutil.which('wsl.exe') or str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/wsl.exe')
        return [executable, '--cd', cwd, '--exec', 'bash', '-c', command]
    raise ValueError('Select PowerShell or WSL')


def _helper_main():
    """Private QProcess entry: no Qt, provider imports, source writes or installs."""
    import importlib.util
    process = None
    readers = []
    watcher = None
    stop = threading.Event()
    output_lock = threading.Lock()
    def emit(packet):
        with output_lock:
            sys.stdout.buffer.write((json.dumps(packet) + '\n').encode('utf-8'))
            sys.stdout.buffer.flush()
    try:
        # Use raw pipe reads consistently: mixing buffered readline with later
        # raw reads can hide an already-prefetched cancellation frame.
        pending = b''
        while b'\n' not in pending:
            chunk = os.read(0, 8192)
            if not chunk:
                raise ValueError('Owning terminal transport closed before launch')
            pending += chunk
            if len(pending) > 524288:
                raise ValueError('Terminal launch frame exceeds its limit')
        launch, pending = pending.split(b'\n', 1)
        packet = json.loads(launch)
        command, runtime, cwd = packet['command'], packet['runtime'], packet['cwd']
        if not isinstance(command, str) or not command or len(command) > 65536:
            raise ValueError('Invalid terminal command')
        if not isinstance(cwd, str) or not Path(cwd).is_dir():
            raise ValueError('Working directory is unavailable')
        # The source entry and reviewed frozen DATA helper have the same
        # sibling layout. Do not import backend or select mechanics via CWD.
        owned_module = Path(__file__).resolve().with_name('owned_process.py')
        spec = importlib.util.spec_from_file_location('_aibs_terminal_owned_process', owned_module)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        process = module.OwnedProcess(shell_argv(runtime, command, cwd), cwd, dict(os.environ))
        emit({'kind': 'started', 'pid': process.pid})
        process.stdin.close()
        process.stdin = None

        def watch_input():
            # No blocked Python BufferedReader may survive interpreter teardown.
            # Peek the Windows pipe, read only available bytes, then join this
            # non-daemon owner before returning from the helper.
            import ctypes
            import msvcrt
            from ctypes import wintypes
            api = ctypes.WinDLL('kernel32', use_last_error=True)
            peek = api.PeekNamedPipe
            peek.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                             ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
            peek.restype = wintypes.BOOL
            handle = msvcrt.get_osfhandle(0)
            buffer = pending
            while not stop.is_set():
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if line.strip() == b'cancel':
                        stop.set()
                        return
                count = wintypes.DWORD()
                if not peek(handle, None, 0, None, ctypes.byref(count), None):
                    stop.set()
                    return
                if count.value:
                    chunk = os.read(0, min(count.value, 128))
                    if not chunk:
                        stop.set()
                        return
                    buffer += chunk
                    if len(buffer) > 1024:
                        stop.set()
                        return
                else:
                    stop.wait(.02)

        def forward(source, stream):
            try:
                while True:
                    data = source.read(8192)
                    if not data:
                        return
                    emit({'kind': 'data', 'stream': stream, 'data': base64.b64encode(data).decode('ascii')})
            except (OSError, ValueError):
                stop.set()

        watcher = threading.Thread(target=watch_input, daemon=False)
        watcher.start()
        for source, stream in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
            worker = threading.Thread(target=forward, args=(source, stream), daemon=False)
            worker.start()
            readers.append(worker)
        code = None
        while not stop.is_set():
            code = process.poll()
            if code is not None:
                break
            stop.wait(.02)
        drained = process.close()
        process = None
        stop.set()
        watcher.join()
        for worker in readers:
            worker.join()
        # Qt's int signal uses signed32; retain the same Windows status bit pattern.
        code = code if code is not None else 130
        if code >= 2 ** 31:
            code -= 2 ** 32
        emit({'kind': 'result', 'exit_code': code, 'drained': drained})
        return 0 if drained else 125
    except Exception as exc:
        # Never echo command arguments, environment values or source text.
        if process is not None:
            safe = process.close()
            process = None
        else:
            safe = True
        emit({'kind': 'error', 'error': type(exc).__name__})
        emit({'kind': 'result', 'exit_code': 127, 'drained': safe})
        return 127
    finally:
        stop.set()
        if process is not None:
            process.close()
        if watcher is not None:
            watcher.join()
        for worker in readers:
            worker.join()


if __name__ == '__main__' and '--terminal-owned-helper' in sys.argv:
    raise SystemExit(_helper_main())


from PyQt6.QtCore import QProcess, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit,
                            QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)


class AIBSTerminal(QWidget):
    command_finished = pyqtSignal(int)
    circuit_breaker_tripped = pyqtSignal(int, str)
    drained = pyqtSignal()
    MAX_QUEUE = 128
    MAX_DISPLAY = 120000

    def __init__(self, parent=None, *, cwd=None, helper_python=None):
        super().__init__(parent)
        root = Path(os.environ.get('AI_BS_ROOT', r'C:\AI-BS')).resolve()
        frozen = bool(getattr(sys, 'frozen', False))
        self._helper_script = (Path(getattr(sys, '_MEIPASS', root)) / 'native_helpers/ai_bs_ide_terminal.py'
                               if frozen else root / 'native_studio/ai_bs_ide_terminal.py')
        default_python = root / 'runtime/recovery-20261110/Scripts/python.exe'
        # A frozen Studio executable is not a Python interpreter. If the
        # declared external recovery runtime is absent, FailedToStart must
        # surface normally instead of recursively launching the application.
        self.helper_python = str(helper_python or (
            default_python if frozen or default_python.is_file() else sys.executable))
        self._queue = deque()
        self._active = None
        self._process = None
        self._closing = False
        self._halted = False
        self._cancelled = False
        self._last_failure = None
        self._failure_count = 0
        self._decoders = {}
        self._cleanup_failed = False
        self._finishing = False
        self.last_completion = None
        self._failed_start = False
        self._envelope = b''
        self._result = None
        self._shell_pid = None
        self._admission_paused = False
        self._start_interval_ms = 0
        self._batch_size = 128
        self._batch_cooldown_ms = 0
        self._batch_started = 0
        self._next_start = 0.0
        self._admission_timer = QTimer(self)
        self._admission_timer.setSingleShot(True)
        self._admission_timer.timeout.connect(self._admit)
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.runtime_selector = QComboBox()
        self.runtime_selector.addItems(['PowerShell', 'WSL'])
        self.cwd_edit = QLineEdit(str(cwd or root))
        top.addWidget(self.runtime_selector)
        top.addWidget(self.cwd_edit, 1)
        layout.addLayout(top)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet('QPlainTextEdit { background-color: #0b061c; color: #f4e8ff; '
                                 'selection-background-color: #375a7f; border: 1px solid #2e1c59; }')
        self.output.setMaximumBlockCount(1000)
        layout.addWidget(self.output, 1)
        bottom = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText('Local shell command')
        self.command_input.returnPressed.connect(self._from_input)
        bottom.addWidget(self.command_input, 1)
        for title, callback in (('Run / queue', self._from_input), ('Cancel', self.cancel),
                                ('Reset failure halt', self.reset_circuit_breaker)):
            button = QPushButton(title)
            button.clicked.connect(callback)
            bottom.addWidget(button)
        layout.addLayout(bottom)
        self.status = QLabel('Ready — local commands run with your account permissions.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    @property
    def is_drained(self):
        return self._active is None and not self._queue and not self._cleanup_failed

    @property
    def halted(self):
        return self._halted

    def snapshot(self):
        return {'running': self._active is not None, 'queued': len(self._queue),
                'is_drained': self.is_drained, 'halted': self._halted,
                'paused': self._admission_paused, 'shell_pid': self._shell_pid,
                'cleanup_failed': self._cleanup_failed, 'max_workers': 1,
                'start_interval_ms': self._start_interval_ms, 'batch_size': self._batch_size,
                'batch_cooldown_ms': self._batch_cooldown_ms}

    def configure_admission(self, *, start_interval_ms=0, batch_size=128, batch_cooldown_ms=0):
        for name, value, maximum in (('start_interval_ms', start_interval_ms, 3600000),
                ('batch_size', batch_size, 128), ('batch_cooldown_ms', batch_cooldown_ms, 3600000)):
            if type(value) is not int or not (1 if name == 'batch_size' else 0) <= value <= maximum:
                raise ValueError('Terminal admission setting is outside its bounded range')
        self._start_interval_ms = start_interval_ms
        self._batch_size = batch_size
        self._batch_cooldown_ms = batch_cooldown_ms
        self._admit()

    def pause_admission(self):
        self._admission_paused = True
        self._admission_timer.stop()
        self.status.setText('Terminal queue paused; active command may finish.')

    def resume_admission(self):
        self._admission_paused = False
        self._admit()

    def _from_input(self):
        command = self.command_input.text()
        if command.strip():
            try:
                self.execute_command(command)
                self.command_input.clear()
            except (ValueError, RuntimeError) as exc:
                self.status.setText(str(exc))

    def execute_command(self, command, runtime=None, cwd=None):
        if self._closing:
            raise RuntimeError('Terminal is closing')
        if not isinstance(command, str) or not command.strip() or len(command) > 65536 or '\0' in command:
            raise ValueError('Enter a nonempty local command within the length limit')
        runtime = runtime or self.runtime_selector.currentText()
        cwd = str(Path(cwd or self.cwd_edit.text()).absolute())
        if not Path(cwd).is_dir():
            raise ValueError('Working directory does not exist')
        shell_argv(runtime, command, cwd)
        if len(self._queue) >= self.MAX_QUEUE:
            raise RuntimeError('Terminal queue is full')
        self._queue.append((runtime, cwd, command))
        self._admit()

    run_command = execute_command

    def _admit(self):
        if self._active is not None or self._finishing or self._closing or self._halted or self._admission_paused or not self._queue:
            return
        remaining = self._next_start - time.monotonic()
        if remaining > 0:
            self._admission_timer.start(max(1, int(remaining * 1000) + 1))
            return
        self._admission_timer.stop()
        self._active = self._queue.popleft()
        self._batch_started += 1
        self._next_start = time.monotonic() + self._start_interval_ms / 1000
        self._cancelled = False
        self._finishing = False
        self._failed_start = False
        self._envelope = b''
        self._result = None
        self._shell_pid = None
        self._decoders = {name: codecs.getincrementaldecoder('utf-8')('replace') for name in ('stdout', 'stderr')}
        process = QProcess(self)
        self._process = process
        process.setProgram(self.helper_python)
        process.setArguments(['-I', '-B', str(self._helper_script), '--terminal-owned-helper'])
        process.setWorkingDirectory(self._active[1])
        process.readyReadStandardOutput.connect(lambda p=process: self._read(p, 'stdout'))
        process.readyReadStandardError.connect(lambda p=process: self._read(p, 'stderr'))
        process.started.connect(lambda p=process: self._started(p))
        process.finished.connect(lambda code, status, p=process: self._finished(p, code, status))
        process.errorOccurred.connect(lambda error, p=process: self._error(p, error))
        self.status.setText('Starting local command; additional commands are queued.')
        process.start()

    def _started(self, process):
        if process is not self._process or self._active is None:
            return
        runtime, cwd, command = self._active
        packet = {'runtime': runtime, 'cwd': cwd, 'command': command}
        process.write((json.dumps(packet) + '\n').encode('utf-8'))
        if self._cancelled:
            process.write(b'cancel\n')
            process.closeWriteChannel()
        self.status.setText('Launching local shell inside its owned Windows job.')

    def _append(self, text):
        if not text:
            return
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        excess = self.output.document().characterCount() - self.MAX_DISPLAY
        if excess > 0:
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, excess)
            cursor.removeSelectedText()
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _read(self, process, stream):
        if process is not self._process:
            return
        process.setReadChannel(QProcess.ProcessChannel.StandardOutput if stream == 'stdout' else QProcess.ProcessChannel.StandardError)
        while process.bytesAvailable():
            data = bytes(process.read(16384))
            if stream == 'stderr':
                self._append(self._decoders[stream].decode(data))
                continue
            self._envelope += data
            while b'\n' in self._envelope:
                line, self._envelope = self._envelope.split(b'\n', 1)
                try:
                    packet = json.loads(line)
                    if packet['kind'] == 'data':
                        channel = packet['stream']
                        if channel not in self._decoders:
                            raise ValueError('Invalid output channel')
                        self._append(self._decoders[channel].decode(base64.b64decode(packet['data'], validate=True)))
                    elif packet['kind'] == 'result':
                        self._result = packet
                    elif packet['kind'] == 'started':
                        self._shell_pid = packet['pid']
                        runtime = self._active[0] if self._active else ''
                        self.status.setText(f'Running local {runtime} process {self._shell_pid}.' +
                            (' Linux descendant cleanup is not qualified.' if runtime == 'WSL' else ''))
                    elif packet['kind'] == 'error':
                        self._append('Terminal launch failed: ' + packet['error'] + '\n')
                except (ValueError, KeyError, TypeError):
                    self._cleanup_failed = True
            if len(self._envelope) > 65536:
                self._envelope = b''
                self._cleanup_failed = True

    def _error(self, process, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._append('Local terminal helper could not start.\n')
            self._result = {'exit_code': 127, 'drained': True}
            self._failed_start = True
            self._finished(process, 127, QProcess.ExitStatus.NormalExit)

    def _finished(self, process, code, exit_status):
        if process is not self._process or self._active is None or self._finishing:
            return
        self._finishing = True
        for stream in ('stdout', 'stderr'):
            self._read(process, stream)
            self._append(self._decoders[stream].decode(b'', final=True))
        result = self._result
        if result is None or result.get('drained') is not True:
            self._cleanup_failed = True
        helper_code = code
        helper_normal = not self._failed_start and exit_status == QProcess.ExitStatus.NormalExit
        command_code = result.get('exit_code', 125) if result is not None else None
        # A result packet precedes interpreter teardown; it cannot turn an
        # aborting helper or nonzero transport exit into successful execution.
        code = command_code if helper_normal and helper_code == 0 and result is not None else (helper_code or 125)
        if code >= 2 ** 31:
            code -= 2 ** 32
        self.last_completion = {'exit_code': code, 'command_exit_code': command_code,
            'helper_exit_code': helper_code, 'helper_normal_exit': helper_normal,
            'job_drained': bool(result and result.get('drained') is True),
            'helper_python': self.helper_python}
        signature = (*self._active, code)
        self._active = None
        self._process = None
        process.deleteLater()
        if self._cleanup_failed:
            self._halted = True
        if self._cancelled:
            self._last_failure = None
            self._failure_count = 0
        elif code != 0:
            self._failure_count = self._failure_count + 1 if signature == self._last_failure else 1
            self._last_failure = signature
            if self._failure_count >= 2:
                self._halted = True
                self.circuit_breaker_tripped.emit(code, 'Two consecutive identical command/runtime/directory failures; queued work retained.')
        else:
            self._failure_count = 0
            self._last_failure = None
        self.status.setText('Cleanup needs attention; terminal retained.' if self._cleanup_failed else
                            ('Failure halt — reset explicitly to continue queued commands.' if self._halted else
                             ('Cancelled.' if self._cancelled else f'Command exited {code}.')))
        if not self._failed_start and (not helper_normal or helper_code != 0):
            self.status.setText(f'Local terminal helper failed (exit {helper_code}); command was not qualified as successful.')
        self.command_finished.emit(code)
        self._finishing = False
        if self._batch_started >= self._batch_size:
            self._batch_started = 0
            self._next_start = max(self._next_start, time.monotonic() + self._batch_cooldown_ms / 1000)
        self._admit()
        if self.is_drained:
            self.drained.emit()

    def reset_circuit_breaker(self):
        if self._cleanup_failed:
            self.status.setText('Owned-process cleanup must be investigated before continuing.')
            return
        self._halted = False
        self._last_failure = None
        self._failure_count = 0
        self._admit()

    def cancel(self):
        self._admission_timer.stop()
        self._queue.clear()
        self._cancelled = True
        if self._process is not None:
            if self._process.state() == QProcess.ProcessState.Running:
                self._process.write(b'cancel\n')
                self._process.closeWriteChannel()
        elif self.is_drained:
            self.drained.emit()

    def shutdown(self):
        self._closing = True
        self.cancel()

    cancel_all = cancel

    def closeEvent(self, event):
        if self.is_drained:
            event.accept()
        else:
            self.shutdown()
            self.drained.connect(self.close)
            event.ignore()
