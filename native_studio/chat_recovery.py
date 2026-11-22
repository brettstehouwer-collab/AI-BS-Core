"""Private, append-only native chat recovery; restored text never executes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import uuid

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtWidgets import QApplication

MAX_BYTES = 32 * 1024 * 1024
_STATE_KEYS = {'transcript', 'draft', 'scratchpad', 'history', 'model'}
_FILE = re.compile(r'^(\d{20})_[0-9a-f]{32}\.json$')


class ChatRecoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class RecoveryLoad:
    state: dict | None
    warning: str = ''


@dataclass(frozen=True)
class RecoveryReceipt:
    path: Path
    checksum: str


def _is_redirected(path):
    return any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
               for p in (Path(path), *Path(path).parents))


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _validate_state(state):
    if (not isinstance(state, dict) or set(state) != _STATE_KEYS
            or any(not isinstance(state[key], str) for key in _STATE_KEYS - {'history'})
            or not isinstance(state['history'], list)
            or any(not isinstance(pair, (list, tuple)) or len(pair) != 2
                   or any(not isinstance(text, str) for text in pair) for pair in state['history'])):
        raise ChatRecoveryError('Chat recovery data is invalid; existing copies were retained.')
    if len(_encode(state)) > MAX_BYTES:
        raise ChatRecoveryError('This chat is too large for one recovery copy. Keep the session open and export it.')


class ChatRecoveryStore:
    def __init__(self, root=None, *, namespace='chat'):
        if not isinstance(namespace,str) or not re.fullmatch(r'[a-z0-9_-]{1,24}',namespace):
            raise ChatRecoveryError('A bounded private recovery namespace is required.')
        if root is None:
            from native_studio.local_connection import _current_identity
            owner = _current_identity().owner_sid
            profile = hashlib.sha256(owner.encode('utf-8')).hexdigest()[:24]
            local = os.environ.get('LOCALAPPDATA', '')
            if not local or not Path(local).is_absolute():
                raise ChatRecoveryError('Private Windows chat storage is not available.')
            folder = profile if namespace == 'chat' else profile + '_' + namespace
            root = Path(local) / 'AI-BS' / 'NativeStudio' / 'ChatRecovery' / folder
        self.root = Path(root).absolute()
        self._mutex = threading.RLock()

    def _prepare(self):
        if _is_redirected(self.root):
            raise ChatRecoveryError('Chat recovery storage cannot use links or junctions.')
        # Existing protected-folder verifier creates with current user/SYSTEM/
        # administrators only; it never rewrites an existing folder's permissions.
        from native_studio.screenplay_client import _private_recovery_directory
        _private_recovery_directory(self.root, self.root.parent)

    def _files(self):
        return sorted((p for p in self.root.iterdir() if _FILE.fullmatch(p.name)), key=lambda p: p.name, reverse=True)

    def _read(self, path):
        if _is_redirected(path) or not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise ChatRecoveryError('A chat recovery copy could not be verified.')
        value = json.loads(path.read_bytes())
        if (not isinstance(value, dict) or set(value) != {'schema', 'sequence', 'savedUTC', 'state', 'checksum'}
                or type(value['schema']) is not int or value['schema'] != 1
                or type(value['sequence']) is not int or value['sequence'] < 1
                or not isinstance(value['savedUTC'], str) or not isinstance(value['checksum'], str)):
            raise ChatRecoveryError('A chat recovery copy could not be verified.')
        checksum = value.pop('checksum')
        if hashlib.sha256(_encode(value)).hexdigest() != checksum:
            raise ChatRecoveryError('A chat recovery copy could not be verified.')
        if value['sequence'] != int(path.name[:20]):
            raise ChatRecoveryError('A chat recovery copy could not be verified.')
        _validate_state(value['state'])
        return value['state']

    def load(self):
        try:
            with self._mutex:
                self._prepare()
                files = self._files()
                for index, path in enumerate(files[:100]):
                    try:
                        return RecoveryLoad(self._read(path), 'An earlier copy was recovered; newer damaged copies were retained.' if index else '')
                    except (ChatRecoveryError, ValueError, UnicodeError, OSError):
                        continue
                if files:
                    raise ChatRecoveryError('Saved chat copies need attention. They were retained; keep this session open.')
                return RecoveryLoad(None)
        except ChatRecoveryError:
            raise
        except Exception:
            raise ChatRecoveryError('Private chat recovery could not be opened. Existing copies were retained.') from None

    def save(self, state):
        _validate_state(state)
        try:
            import msvcrt
            with self._mutex:
                self._prepare()
                lock_path = self.root / 'writer.lock'
                if _is_redirected(lock_path):
                    raise ChatRecoveryError('Private chat storage needs attention.')
                with lock_path.open('a+b') as lock:
                    if not lock.tell():
                        lock.write(b'\0'); lock.flush()
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    try:
                        files = self._files()
                        sequence = int(files[0].name[:20]) + 1 if files else 1
                        if sequence >= 10**20:
                            raise ChatRecoveryError('The chat recovery sequence is full.')
                        value = {'schema': 1, 'sequence': sequence,
                                 'savedUTC': datetime.now(timezone.utc).isoformat(), 'state': state}
                        checksum = hashlib.sha256(_encode(value)).hexdigest()
                        raw = _encode({**value, 'checksum': checksum})
                        if len(raw) > MAX_BYTES:
                            raise ChatRecoveryError('This chat is too large for one recovery copy.')
                        target = self.root / f'{sequence:020d}_{uuid.uuid4().hex}.json'
                        staging = target.with_suffix('.partial')
                        with staging.open('xb') as stream:
                            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                        if staging.read_bytes() != raw or _is_redirected(staging):
                            raise ChatRecoveryError('Chat recovery readback was not confirmed.')
                        # Windows rename is atomic and refuses an existing target.
                        os.rename(staging, target)
                        if self._read(target) != json.loads(_encode(state)):
                            raise ChatRecoveryError('Chat recovery readback was not confirmed.')
                        return RecoveryReceipt(target, checksum)
                    finally:
                        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        except ChatRecoveryError:
            raise
        except Exception:
            raise ChatRecoveryError('Chat recovery could not be saved. Keep this window open; earlier copies and partial evidence were retained.') from None


class ChatRecoveryController(QObject):
    def __init__(self, view, bus, store=None, *, store_factory=None):
        super().__init__(view)
        self.view, self.bus = view, bus
        self.store = store
        self._store_factory = store_factory or ChatRecoveryStore
        self.ready = False
        self._busy = False
        self._closed = False
        self._load_failed = False
        self._generation = 0
        self._save_lock = threading.Lock()
        self._confirmed = None
        self._initial = self.capture()
        self.timer = QTimer(self)
        self.timer.setInterval(1500)
        self.timer.timeout.connect(self.tick)
        self.view.input_edit.setEnabled(False)
        self.view.send_btn.setEnabled(False)
        self.view.recovery_status.setText('Opening private chat recovery…')
        self.view.recovery_retry.clicked.connect(self.retry)
        self.view.recovery_retry.hide()
        self._filter_application = QApplication.instance()
        if self._filter_application is not None:
            self._filter_application.installEventFilter(self)

    def begin(self):
        if self._closed:
            return
        def load():
            if self.store is None:
                self.store = self._store_factory()
            return self.store.load()
        try:
            self.bus.submit(load, on_result=self._loaded, on_error=self._load_error)
        except Exception:
            self._load_error('')

    def capture(self):
        if hasattr(self.view, 'capture_recovery_state'):
            return self.view.capture_recovery_state()
        return {'transcript': self.view.chat_display.toPlainText(), 'draft': self.view.input_edit.text(),
                'scratchpad': self.view.code_editor.toPlainText(),
                'history': [list(pair) for pair in self.view._conversation_history],
                'model': str(self.view.model_picker.currentData() or '')}

    def _enable(self):
        self.ready = True
        self.view.input_edit.setEnabled(True)
        self.view.send_btn.setEnabled(True)
        self.timer.start()

    def _loaded(self, result):
        if self._closed:
            return
        changed = self.capture() != self._initial
        self._load_failed = False
        self.view.recovery_retry.hide()
        if result.state is not None and not changed:
            state = result.state
            if hasattr(self.view, 'apply_recovery_state'):
                self.view.apply_recovery_state(state)
            else:
                self.view.chat_display.setPlainText(state['transcript'])
                self.view.input_edit.setText(state['draft'])
                self.view.code_editor.setPlainText(state['scratchpad'])
                self.view._conversation_history = [tuple(pair) for pair in state['history']]
                index = self.view.model_picker.findData(state['model'])
                if index >= 0:
                    self.view.model_picker.setCurrentIndex(index)
                if state['transcript']:
                    self.view.left_stack.setCurrentIndex(1)
            self._confirmed = self.capture()
            self.view.recovery_status.setText(result.warning or 'Chat recovered from a private local copy.')
        elif changed:
            self.view.recovery_status.setText('Your new draft was kept; earlier saved chat copies were retained.')
        else:
            self._confirmed = self.capture()
            self.view.recovery_status.setText('Private chat recovery ready.')
        self._enable()

    def _load_error(self, _message):
        if self._closed:
            return
        self.view.recovery_status.setText('Private recovery needs attention. Existing copies retained; keep this window open.')
        self._load_failed = True
        self.view.recovery_retry.show()
        self._enable()
        # Refuse to publish an empty replacement over unreadable recovery history.
        self.timer.stop()

    def tick(self):
        if not self.ready or self._busy or self._closed or self.store is None or self._load_failed:
            return
        state = self.capture()
        if state == self._confirmed:
            return
        self._busy = True
        self._generation += 1
        generation = self._generation
        self.view.recovery_status.setText('Saving private chat recovery…')
        def saved(receipt):
            self._busy = False
            if self._closed or generation != self._generation or receipt is None:
                return
            self._confirmed = state
            if not self._closed:
                self.view.recovery_retry.hide()
                self.view.recovery_status.setText('Chat saved privately.' if self.capture() == state else 'New edits waiting for private recovery.')
        def failed(_message):
            self._busy = False
            if not self._closed:
                self.view.recovery_status.setText('Private save failed. Keep this window open; earlier copies retained.')
                self.view.recovery_retry.show()
                self.timer.stop()
        def write():
            with self._save_lock:
                if generation != self._generation:
                    return None
                return self.store.save(state)
        try:
            self.bus.submit(write, on_result=saved, on_error=failed)
        except Exception:
            failed('')

    def flush_for_close(self):
        if self._closed:
            return False
        if not self.ready or self.store is None or self.view._is_streaming or self._load_failed:
            self.view.recovery_status.setText('Finish the current response/recovery before closing this chat.')
            return False
        state = self.capture()
        if state != self._confirmed:
            try:
                # Retire queued older snapshots before the final current-state
                # write. An in-flight write finishes first under this same lock.
                with self._save_lock:
                    self._generation += 1
                    self.store.save(state)
            except Exception:
                self.view.recovery_status.setText('Private save failed. Keep this window open; earlier copies retained.')
                return False
            self._confirmed = state
        return True

    def retry(self):
        if self._busy or self._closed:
            return
        if self._load_failed:
            self.ready = False
            self.view.input_edit.setEnabled(False)
            self.view.send_btn.setEnabled(False)
            self.begin()
        else:
            self.timer.start()
            self.tick()

    def eventFilter(self, watched, event):
        if self._closed:
            return False
        if event.type() == QEvent.Type.Close:
            view = getattr(self, 'view', None)
            if view is None:
                return False
            try:
                window = view.window()
            except RuntimeError:
                # Qt can deliver a final close event while the owner is released.
                return False
            if watched is window:
                if not self.flush_for_close():
                    event.ignore()
                    return True
        return super().eventFilter(watched, event)

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        self.timer.stop()
        # This filter belongs to the application, not just the chat widget.
        # Detach from the exact installer before the view can be destroyed.
        app, self._filter_application = self._filter_application, None
        if app is not None:
            try:
                app.removeEventFilter(self)
            except RuntimeError:
                # QApplication may already have released its native object.
                pass
