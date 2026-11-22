"""Read a saved chapter through a separate, joined native authoring owner.

The journal remains native-owned. Python checks its bounded identity, never
parses AIBD/AIBA or sends SAVE, and does not substitute the factory export.
"""
from dataclasses import dataclass, replace
import hashlib
import os
from pathlib import Path
import stat

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from .content_client import ContentClient
from .content_commands import (open_document, decode_description, export_content,
    decode_content_export)
from .content_preview import ContentExportAssembly, ContentSnapshot
from .creator_commands import Status, scoped
from .creator_payload import _uuid
from .creator_wire import Opcode

JOURNAL_LIMIT = 1024 * 1024
_COMPLETE = 'chapter-content-export-v2'


@dataclass(frozen=True)
class SavedJournalIdentity:
    sha256: str
    bytes: int
    device: int
    inode: int
    modified_ns: int


def _plain_path(path):
    """Reject redirected ancestors as well as the selected journal itself."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Saved chapter paths must not contain links or reparse points')
    return path


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def hash_saved_journal(directory):
    """Hash at most 1 MiB; detect replacement or writes during the read."""
    try:
        root = _plain_path(directory)
        if not root.is_dir():
            raise ValueError('Saved chapter project directory is unavailable')
        path = _plain_path(root / 'chapter.aiba')
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= JOURNAL_LIMIT:
            raise ValueError('Saved chapter journal must be a regular file of 1 byte to 1 MiB')
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            if _identity(opened) != _identity(before):
                raise ValueError('Saved chapter journal changed before it could be read')
            data = stream.read(JOURNAL_LIMIT + 1)
            after = os.fstat(stream.fileno())
        current = _plain_path(path).lstat()
        if len(data) != before.st_size or _identity(before) != _identity(after) or _identity(before) != _identity(current):
            raise ValueError('Saved chapter journal changed while it was being read')
        return SavedJournalIdentity(hashlib.sha256(data).hexdigest(), len(data),
            before.st_dev, before.st_ino, before.st_mtime_ns)
    except OSError as error:
        raise ValueError('Could not read saved chapter journal: ' + str(error)) from error


@dataclass(frozen=True)
class SavedChapterExportResult:
    snapshot: ContentSnapshot
    journal_sha256: str
    journal_bytes: int


class SavedChapterExportClient(QObject):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    message = pyqtSignal(str)
    state_changed = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = ContentClient(self)
        self.client.ready.connect(self._ready)
        self.client.response.connect(self._response)
        self.client.request_failed.connect(self._request_failed)
        self.client.closed.connect(self._joined)
        self.state = 'closed'
        self._pending = None
        self._result = None
        self._error = None
        self._cancelled = False
        self._assembly = None
        self._guard = None
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    @property
    def busy(self):
        return self.state != 'closed'

    @property
    def process_id(self):
        return self.client.process_id

    def _state(self, state):
        self.state = state
        self.state_changed.emit(state)

    def _check(self, *, journal=False):
        if self._guard is not None and not self._guard():
            raise ValueError('The creator chapter changed during saved export; save and refresh before playing')
        if journal and hash_saved_journal(self._directory) != self._journal:
            raise ValueError('The saved chapter journal changed during export')

    def start(self, executable, definition, snapshot, *, context_valid=None):
        if QThread.currentThread() != self.thread():
            raise RuntimeError('Saved export must be used on its owning Qt thread')
        if self.busy or self.client.state != 'closed' or self.client.process_id:
            raise RuntimeError('Wait for the saved chapter reader to close')
        if not isinstance(snapshot, ContentSnapshot) or snapshot.export_version != 2:
            raise ValueError('Saved chapter play requires a complete version-2 native export')
        _uuid(snapshot.checkpoint_id)
        if (snapshot.scope.project, snapshot.scope.branch, snapshot.asset_profile) != (
                definition.project, definition.branch, definition.asset_profile):
            raise ValueError('Saved chapter selection does not match the creator snapshot')
        if context_valid is not None and not callable(context_valid):
            raise ValueError('Saved export context guard must be callable')
        directory = _plain_path(definition.directory)
        journal = hash_saved_journal(directory)
        if snapshot.asset_store is not None and Path(snapshot.asset_store).absolute() != directory / 'assets/packs':
            raise ValueError('Saved chapter dependencies must belong to the selected project')
        if context_valid is not None and not context_valid():
            raise ValueError('The creator chapter changed before saved export')
        self._directory, self._journal, self._snapshot = directory, journal, snapshot
        self._guard = context_valid
        self._pending = self._assembly = self._result = self._error = None
        self._cancelled = False
        self.client.asset_profile = definition.asset_profile
        self.client.opening_workshop = definition.opening_workshop
        self._state('starting')
        self._timer.start()
        try:
            self.client.start(executable, directory)
        except Exception:
            self._timer.stop()
            self._state('closed')
            raise

    def _send(self, kind, opcode, payload, revision=None):
        identity = self.client.request(opcode, payload, revision=revision)
        self._pending = (identity, kind)

    def _ready(self):
        if self.state != 'starting':
            return
        try:
            self._check(journal=True)
            if _COMPLETE not in self.client.capabilities:
                raise ValueError('Saved chapter reader does not support complete native exports')
            self._state('reading')
            self._send('open', Opcode.OPEN, open_document(self._snapshot.scope.project,
                self._snapshot.scope.branch, create=False))
        except Exception as error:
            self._fail(str(error))

    def _matching_saved_head(self, reply):
        s = self._snapshot
        if ((reply.scope.project, reply.scope.branch, reply.scope.world_id, reply.head_revision, reply.checkpoint_id) !=
                (s.scope.project, s.scope.branch, s.scope.world_id, s.revision, s.checkpoint_id)):
            raise ValueError('Saved chapter identity or checkpoint differs from the creator; save and refresh first')

    def _response(self, identity, reply):
        if self.state != 'reading' or self._pending is None or identity != self._pending[0]:
            return
        kind = self._pending[1]
        self._pending = None
        try:
            self._check()
            if reply.status != Status.OK:
                raise ValueError('Native saved chapter read rejected: ' + reply.message)
            self._matching_saved_head(reply)
            if kind == 'open':
                self._scope = reply.scope
                self._reader_generation = self.client.generation
                self._send('describe', Opcode.DESCRIBE, scoped(reply.scope), reply.head_revision)
            elif kind == 'describe':
                if reply.scope != self._scope or self.client.generation != self._reader_generation:
                    raise ValueError('Saved chapter reader context changed')
                description = decode_description(reply.body)
                s = self._snapshot
                if description.dirty or (description.definition_id, description.content_revision, description.fingerprint) != (
                        s.definition_id, s.content_revision, s.fingerprint):
                    raise ValueError('Saved chapter content differs from the clean creator snapshot')
                self._assembly = ContentExportAssembly(reply.scope, self.client.generation,
                    reply.head_revision, reply.checkpoint_id, description, s.entity_ids,
                    asset_store=self._directory/'assets/packs', asset_profile=s.asset_profile,
                    require_complete_dependencies=True, authored_inspections=s.authored_inspections,
                    initial_view_authored=s.initial_view_authored,
                    opening_workshop_authored=s.opening_workshop_authored)
                self._export_next()
            elif kind == 'export':
                snapshot = self._assembly.accept(decode_content_export(reply.body), reply.scope,
                    self.client.generation, reply.head_revision, reply.checkpoint_id)
                if snapshot is None:
                    self._export_next()
                    return
                if (snapshot.payload, snapshot.asset_refs, snapshot.dependency_kinds) != (
                        self._snapshot.payload, self._snapshot.asset_refs, self._snapshot.dependency_kinds):
                    raise ValueError('Saved chapter export or dependency closure differs from the creator')
                self._check(journal=True)
                # Only the second owner's epoch is different. The original UI
                # pin stays authoritative throughout staging and publication.
                snapshot = replace(snapshot, scope=self._snapshot.scope, generation=self._snapshot.generation)
                self._result = SavedChapterExportResult(snapshot, self._journal.sha256, self._journal.bytes)
                self._state('stopping')
                self.client.stop()
        except Exception as error:
            self._fail(str(error))

    def _export_next(self):
        a = self._assembly
        self._send('export', Opcode.DESCRIBE, export_content(a.scope, a.offset,
            256*1024, a.description.fingerprint, complete_dependencies=True), a.revision)

    def _tick(self):
        if self.state in ('starting', 'reading'):
            try:
                self._check()
            except Exception as error:
                self._fail(str(error))

    def _request_failed(self, identity, reason):
        if self.state in ('starting', 'reading'):
            self._fail('Saved chapter reader failed: ' + reason)

    def _fail(self, message):
        self._error = message
        self._result = None
        self._state('stopping')
        self.client.stop()
        if self.client.state == 'closed' and not self.client.process_id:
            self._joined('Reader did not start')

    def stop(self):
        if not self.busy:
            return
        self._cancelled = True
        self._result = None
        self._state('stopping')
        self.client.stop()
        if self.client.state == 'closed' and not self.client.process_id:
            self._joined('Requested close')

    def _joined(self, reason):
        if not self.busy:
            return
        if self.client.state != 'closed' or self.client.process_id:
            return
        result, error = self._result, self._error
        if not self._cancelled and error is None:
            try:
                if result is None or reason != 'Requested close':
                    raise ValueError('Saved chapter reader did not complete a graceful verified export: ' + reason)
                self._check(journal=True)
            except Exception as failure:
                result, error = None, str(failure)
        self._timer.stop()
        self._pending = self._assembly = self._result = None
        self._state('closed')
        if not self._cancelled:
            if error is not None:
                self.failed.emit(error)
            else:
                self.completed.emit(result)
        self.closed.emit()
