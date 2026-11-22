"""Owned native saved-chapter play; retained data is never temporary scratch."""
from pathlib import Path
import json
import os
import time
import uuid
from PyQt6.QtCore import QCoreApplication, QObject, QProcess, QThread, QTimer, pyqtSignal
from .project_assets import ProjectAssetClient
from .saved_play_storage import (prepare_publication, finish_publication, discard_staging,
    revalidate_publication, require_saved_player, checked_path, _json)


class SavedChapterPlayClient(QObject):
    state_changed = pyqtSignal(str)
    message = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent=None, start_timeout_ms=30000, stop_timeout_ms=15000, *, asset_cooker=None):
        super().__init__(parent)
        if (type(start_timeout_ms) is not int or type(stop_timeout_ms) is not int
                or not 1 <= start_timeout_ms <= 60000 or not 1 <= stop_timeout_ms <= 60000):
            raise ValueError('Invalid saved-play timeout')
        self.state = 'closed'
        self._process = None
        self._preparation = None
        self.publication = None
        self.snapshot = None
        self.session_id = None
        self.last_result = None
        self._executable = None
        self._context_valid = None
        self._stop_file = None
        self._receipt = None
        self._ready_head = None
        self._forced = self._protocol_failed = self._stop_requested = False
        self._reason = ''
        self._buffer = bytearray()
        self.stdout_tail = self.stderr_tail = b''
        self._deadline = None
        self._start_seconds = start_timeout_ms / 1000
        self._stop_seconds = stop_timeout_ms / 1000
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._stager = ProjectAssetClient(asset_cooker, self)
        self._stager.receipt.connect(self._stage_ready)
        self._stager.failed.connect(self._stage_failed)
        self._stager.closed.connect(self._stage_closed)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown)

    def _thread(self):
        if QThread.currentThread() != self.thread():
            raise RuntimeError('Saved play must be used on its owning Qt thread')

    @property
    def process_id(self):
        return int(self._process.processId()) if self._process is not None else 0

    @property
    def dependency_process_id(self):
        return self._stager.process_id

    @property
    def workspace_path(self):
        return self.publication.slot_directory if self.publication is not None else None

    def _state(self, state):
        self.state = state
        self.state_changed.emit(state)

    def _check_context(self):
        if self._context_valid is not None and not self._context_valid():
            raise ValueError('Saved chapter or its owner changed; save/refresh before launching again')

    def start(self, executable, snapshot, project_directory, *, context_valid=None):
        self._thread()
        if self.state != 'closed' or self._process is not None or self._stager.busy:
            raise RuntimeError('Stop the current saved chapter session first')
        if context_valid is not None and not callable(context_valid):
            raise ValueError('Saved-play context guard must be callable')
        # Perform capability admission before creating even a staging directory.
        executable = require_saved_player(executable, snapshot)
        if context_valid is not None and not context_valid():
            raise ValueError('Saved chapter changed before launch')
        self._context_valid = context_valid
        self.snapshot = snapshot
        self._executable = executable
        self.session_id = str(uuid.uuid4())
        self.publication = None
        self._stop_file = None
        self.last_result = None
        self._receipt = self._ready_head = None
        self._forced = self._protocol_failed = self._stop_requested = False
        self._reason = ''
        self._buffer.clear()
        self.stdout_tail = self.stderr_tail = b''
        self._preparation = prepare_publication(project_directory, snapshot)
        self._deadline = time.monotonic() + self._start_seconds
        self._state('staging')
        self._timer.start()
        # A queued start lets cancellation and UI ownership settle first.
        session = self.session_id
        QTimer.singleShot(0, lambda: self._begin_staging(session))

    def _begin_staging(self, session):
        if session != self.session_id or self.state != 'staging':
            return
        try:
            self._check_context()
            if self.snapshot.asset_refs:
                # A retained publication is self-contained. Always revalidate
                # its typed closure through native stage-store before reuse;
                # the original authoring asset store need not remain mounted.
                retained = self._preparation.root / 'content' / self.snapshot.fingerprint
                source = self.snapshot.asset_store
                if retained.exists():
                    checked_path(retained, directory=True)
                    source = checked_path(retained / 'assets/packs', directory=True)
                if source is None:
                    raise ValueError('Saved chapter dependency store is unavailable')
                self._stager.stage_store(source,
                    self._preparation.staging / 'assets/packs', self.snapshot.asset_refs,
                    profile=self.snapshot.asset_profile)
            else:
                self._publish_and_launch()
        except Exception as error:
            self._fail_before_player(str(error))

    def _stage_ready(self, mode, receipt):
        if mode != 'stage' or self.state != 'staging':
            return
        try:
            # ProjectAssetClient emits only after QProcess finished and its
            # exact immutable-reference receipt was checked against the request.
            if self._stager.busy:
                raise ValueError('Dependency owner has not joined')
            self._publish_and_launch()
        except Exception as error:
            self._fail_before_player(str(error))

    def _publish_and_launch(self):
        self._check_context()
        require_saved_player(self._executable, self.snapshot)
        self.publication = finish_publication(self._preparation, context_valid=self._context_valid)
        self._preparation = None
        revalidate_publication(self.publication)
        self._check_context()
        require_saved_player(self._executable, self.snapshot)
        self._launch()

    def _launch(self):
        publication = self.publication
        self._stop_file = publication.slot_directory / ('stop.' + self.session_id + '.request')
        checked_path(self._stop_file, directory=False, missing=True)
        if self._stop_file.exists():
            raise ValueError('Saved-play invocation stop marker already exists')
        args = ['--durable-world', '--content-definition', str(publication.content_path),
                '--database', str(publication.database_path), '--project', self.snapshot.scope.project,
                '--branch', self.snapshot.scope.branch, '--play-session', self.session_id,
                '--stop-file', str(self._stop_file), '--persistent-play', '--timeline-id', publication.timeline_id]
        if self.snapshot.asset_refs:
            args += ['--asset-root', str(publication.asset_root)]
        p = QProcess(self)
        self._process = p
        p.setWorkingDirectory(str(publication.slot_directory))
        p.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        p.readyReadStandardOutput.connect(lambda: self._stdout(p))
        p.readyReadStandardError.connect(lambda: self._stderr(p))
        p.finished.connect(lambda code, status: self._finished(p, code, status))
        p.errorOccurred.connect(lambda error: self._error(p, error))
        self._deadline = time.monotonic() + self._start_seconds
        self._state('starting')
        p.start(str(self._executable), args)

    def _stage_failed(self, reason):
        if self._process is None:
            self._fail_before_player('Saved chapter dependency staging failed: ' + reason)

    def _stage_closed(self):
        if self.state == 'stopping' and self._process is None and not self._stager.busy:
            self._finish_without_player()

    def _fail_before_player(self, reason):
        self._reason = reason
        self.message.emit(reason)
        if self._stager.busy:
            self._state('stopping')
            self._stager.stop()
        else:
            self._finish_without_player()

    def _cleanup_staging(self):
        if self._preparation is not None:
            try:
                discard_staging(self._preparation)
            except Exception as error:
                self._reason = (self._reason + '; ' if self._reason else '') + 'Staging retained: ' + str(error)
            self._preparation = None

    def _finish_without_player(self):
        self._cleanup_staging()
        self._timer.stop()
        self._deadline = None
        self.last_result = {'graceful': False, 'saved': False, 'forced': self._forced,
            'reason': self._reason or 'Saved chapter launch cancelled; retained saves were kept.',
            'content_fingerprint': self.snapshot.fingerprint, 'play_session': self.session_id,
            'context': 'player_world', 'timeline_id': self.publication.timeline_id if self.publication else None}
        self._state('closed')
        self.closed.emit()

    def _line(self, line):
        if not line.startswith(b'{'):
            return
        event = _json(line, 16384)
        if type(event) is not dict:
            raise ValueError('Native saved-play response must be an object')
        name = event.get('event')
        if name not in ('aibs.saved_play.ready', 'aibs.saved_play.stopped'):
            if type(name) is str and name.startswith(('aibs.play.', 'aibs.saved_play.')):
                raise ValueError('Native player used an incompatible lifecycle event')
            return
        keys = {'event', 'schema_version', 'play_session', 'project_id', 'branch_id', 'world_id',
                'timeline_id', 'context', 'content_fingerprint', 'saved', 'durable_revision', 'durable_sequence'}
        if set(event) != keys or type(event['schema_version']) is not int or event['schema_version'] != 1:
            raise ValueError('Invalid saved-play lifecycle schema')
        expected = (self.session_id, self.snapshot.scope.project, self.snapshot.scope.branch,
                    self.snapshot.scope.world_id, self.publication.timeline_id, 'player_world', self.snapshot.fingerprint)
        if tuple(event[key] for key in ('play_session', 'project_id', 'branch_id', 'world_id',
                                       'timeline_id', 'context', 'content_fingerprint')) != expected:
            raise ValueError('Native saved-play response belongs to another slot or session')
        if type(event['saved']) is not bool or any(type(event[key]) is not int or not 0 <= event[key] < 2**64
                                                 for key in ('durable_revision', 'durable_sequence')):
            raise ValueError('Invalid saved-play durability receipt')
        head = (event['durable_revision'], event['durable_sequence'])
        if name == 'aibs.saved_play.ready':
            if self._ready_head is not None or self._receipt is not None:
                raise ValueError('Duplicate/out-of-order saved-play READY')
            self._ready_head = head
            if self.state == 'starting':
                self._deadline = None
                self._state('ready')
            branch = 'Resumed' if self.publication.reused_slot else 'Started'
            self.message.emit(branch + ' saved chapter. Committed gameplay progress is retained in this content branch.')
        else:
            if self._receipt is not None or (self._ready_head is None and not self._stop_requested):
                raise ValueError('Duplicate/out-of-order saved-play STOPPED')
            if self._ready_head is not None and any(a < b for a, b in zip(head, self._ready_head)):
                raise ValueError('Saved-play durability head regressed')
            self._receipt = event
            if self.state != 'stopping':
                self._deadline = time.monotonic() + self._stop_seconds
                self._state('stopping')
            # STOPPED is a native drain receipt, not proof of process/SQLite exit.
            # The retained slot remains owned until QProcess.finished below.

    def _stdout(self, p):
        if p is not self._process:
            return
        p.setReadChannel(QProcess.ProcessChannel.StandardOutput)
        try:
            while p.bytesAvailable():
                raw = bytes(p.read(min(32768, p.bytesAvailable())))
                self.stdout_tail = (self.stdout_tail + raw)[-16384:]
                self._buffer.extend(raw)
                if len(self._buffer) > 65536:
                    raise ValueError('Saved-play output buffer limit')
                while b'\n' in self._buffer:
                    line, _, remaining = self._buffer.partition(b'\n')
                    self._buffer = bytearray(remaining)
                    if len(line) > 16384:
                        raise ValueError('Saved-play output line limit')
                    self._line(bytes(line).rstrip(b'\r'))
                if len(self._buffer) > 16384:
                    raise ValueError('Saved-play output line limit')
        except Exception as error:
            self._protocol_failed = True
            self._reason = 'Invalid native saved-play response: ' + str(error)
            self.message.emit(self._reason)
            self.stop()

    def _stderr(self, p):
        if p is not self._process:
            return
        p.setReadChannel(QProcess.ProcessChannel.StandardError)
        while p.bytesAvailable():
            self.stderr_tail = (self.stderr_tail + bytes(p.read(min(32768, p.bytesAvailable()))))[-16384:]
        p.setReadChannel(QProcess.ProcessChannel.StandardOutput)

    def stop(self):
        self._thread()
        if self.state in ('closed', 'stopping'):
            return
        self._stop_requested = True
        self._state('stopping')
        self._deadline = time.monotonic() + self._stop_seconds
        if self._process is None:
            self._stager.stop()
            if not self._stager.busy:
                self._finish_without_player()
            return
        try:
            marker = checked_path(self._stop_file, directory=False, missing=True)
            with marker.open('xb') as stream:
                stream.write(b'stop\n');stream.flush();os.fsync(stream.fileno())
        except OSError as error:
            self._force('Could not request a saved-play drain: ' + str(error))
        except ValueError as error:
            self._force('Saved-play stop path changed: ' + str(error))

    def _force(self, reason):
        self._forced = True
        self._reason = reason
        self._deadline = None
        self.message.emit(reason + ' The latest progress is unverified; retained files will be preserved.')
        if self._process is not None:
            self._process.kill()
        elif self._stager.busy:
            self._state('stopping');self._stager.stop()
        elif self.state != 'closed':
            self._finish_without_player()

    def _tick(self):
        if self.state in ('staging', 'starting'):
            try:
                self._check_context()
            except Exception as error:
                self._reason = str(error);self.message.emit(self._reason);self.stop()
        if self._deadline is not None and time.monotonic() >= self._deadline:
            self._force('Saved chapter ' + ('stop' if self.state == 'stopping' else 'startup') + ' deadline expired')

    def _error(self, p, error):
        if p is self._process and error == QProcess.ProcessError.FailedToStart:
            self._reason = p.errorString()
            self._finished(p, -1, QProcess.ExitStatus.CrashExit)

    def _finished(self, p, code, status):
        if p is not self._process:
            return
        self._stdout(p);self._stderr(p)
        if self._buffer.strip():
            self._protocol_failed = True
            self._reason = 'Native saved-play output ended with an incomplete line'
        graceful = (not self._forced and not self._protocol_failed and code == 0
                    and status == QProcess.ExitStatus.NormalExit and self._receipt is not None)
        saved = bool(graceful and self._receipt['saved'])
        reason = self._reason or ('Saved chapter closed; committed progress is retained.' if saved
            else 'Saved chapter exited without a verified save drain; retained data was preserved.')
        self.last_result = {'graceful': graceful, 'saved': saved, 'forced': self._forced, 'reason': reason,
            'content_fingerprint': self.snapshot.fingerprint, 'play_session': self.session_id,
            'project_id': self.snapshot.scope.project, 'branch_id': self.snapshot.scope.branch,
            'world_id': self.snapshot.scope.world_id, 'timeline_id': self.publication.timeline_id,
            'context': 'player_world', 'ready_seen': self._ready_head is not None,
            'durable_revision': self._receipt['durable_revision'] if self._receipt else None,
            'durable_sequence': self._receipt['durable_sequence'] if self._receipt else None}
        self._process = None
        self._timer.stop();self._deadline = None;self._buffer.clear()
        # Native holds player.lock through all archive/worker destruction. Only
        # after the process exits may this invocation's own marker be removed.
        if self._stop_file is not None:
            try:
                marker = checked_path(self._stop_file, directory=False, missing=True)
                if marker.exists():marker.unlink()
            except (OSError, ValueError):
                pass  # A retained unique marker cannot block the next session.
        p.deleteLater()
        self._state('closed');self.message.emit(reason);self.closed.emit()

    def shutdown(self):
        # Normal project/window close uses asynchronous stop/closed ownership.
        # A bounded final fallback must not call a kill request a completed join.
        self.stop();self._stager.shutdown()
        p = self._process
        if p is not None and not p.waitForFinished(500):
            self._force('Application exited before the saved chapter drained')
            p.waitForFinished(1000)
        joined = self._process is None and not self._stager.busy
        if not joined:
            self._reason = 'Saved chapter is still closing; owned processes and retained files remain pending.'
            self.message.emit(self._reason)
        return joined

    def _shutdown(self):
        return self.shutdown()
