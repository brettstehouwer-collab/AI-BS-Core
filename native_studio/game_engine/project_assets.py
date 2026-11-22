"""Native-owned immutable project asset adoption and private dependency staging."""
from dataclasses import dataclass
import json
from pathlib import Path
import re
import uuid
from PyQt6.QtCore import QCoreApplication, QObject, QProcess, QThread, QTimer, pyqtSignal

ASSET_REFERENCE_FIELDS = frozenset(('asset_id', 'asset_sha256', 'pack_sha256'))
_SHA = re.compile('[0-9a-f]{64}\\Z')
LIMIT = 65536
ASSET_PROFILES = frozenset(('legacy_v1', 'warm-beginning'))


def validate_asset_profile(profile):
    if type(profile) is not str or profile not in ASSET_PROFILES:
        raise ValueError('Unknown chapter asset profile')
    return profile


@dataclass(frozen=True, order=True)
class AssetDependency:
    asset_id: str
    asset_sha256: str
    pack_sha256: str

    def __post_init__(self):
        if (type(self.asset_id) is not str or str(uuid.UUID(self.asset_id)) != self.asset_id
                or uuid.UUID(self.asset_id).version != 4 or type(self.asset_sha256) is not str
                or not _SHA.fullmatch(self.asset_sha256) or type(self.pack_sha256) is not str
                or not _SHA.fullmatch(self.pack_sha256)):
            raise ValueError('Invalid immutable asset dependency reference')


def dependencies_from_rows(rows):
    result = set()
    for row in rows:
        if row.type_id == 'authoring.AssetPlacement':
            fields = dict(row.fields)
            result.add(AssetDependency(*(fields[name] for name in ('asset_id', 'asset_sha256', 'pack_sha256'))))
    if len(result) > 64:
        raise ValueError('Chapter asset dependency limit exceeds 64')
    return tuple(sorted(result))


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate native asset receipt key')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('Nonfinite native asset receipt: ' + value)


class ProjectAssetClient(QObject):
    receipt = pyqtSignal(str, object)
    failed = pyqtSignal(str)
    closed = pyqtSignal()
    state_changed = pyqtSignal()

    def __init__(self, cooker, parent=None, timeout_ms=30000):
        super().__init__(parent)
        self.cooker = Path(cooker) if cooker is not None else None
        self._process = None
        self._mode = self._context = None
        self._out, self._err = bytearray(), bytearray()
        self._failure = ''
        self._cancelled = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(timeout_ms)
        self._timer.timeout.connect(self._timeout)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    @property
    def busy(self): return self._process is not None
    @property
    def process_id(self): return int(self._process.processId()) if self._process is not None else 0

    def inspect_pack(self, root):
        self._start(['--inspect', str(Path(root).resolve())], 'inspect')

    def adopt_pack(self, root, store):
        self._start(['--adopt', str(Path(root).resolve()), '--store', str(Path(store).resolve())], 'adopt')

    def stage_store(self, store, output, refs, *, merge=False, profile='legacy_v1'):
        validate_asset_profile(profile)
        refs = tuple(sorted(set(refs)))
        if not 1 <= len(refs) <= 64 or any(type(ref) is not AssetDependency for ref in refs):
            raise ValueError('Staging requires 1..64 immutable dependency references')
        args = ['--stage-store', str(Path(store).resolve()), '--output', str(Path(output).resolve())]
        for ref in refs:
            args += ['--ref', ref.asset_id, ref.asset_sha256, ref.pack_sha256]
        if merge: args.append('--merge')
        if profile == 'warm-beginning': args += ['--profile', profile]
        self._start(args, 'stage', refs)

    def _start(self, args, mode, context=None):
        if QThread.currentThread() != self.thread():
            raise RuntimeError('Use project asset operations on their owning Qt thread')
        if self.busy: raise RuntimeError('Wait for the pending project asset operation')
        if self.cooker is None or not self.cooker.is_file():
            raise ValueError('The native asset cooker is unavailable')
        self._mode, self._context = mode, context
        self._out.clear(); self._err.clear(); self._failure = ''; self._cancelled = False
        p = QProcess(self); self._process = p
        p.setWorkingDirectory(str(self.cooker.resolve().parent))
        p.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        p.readyReadStandardOutput.connect(lambda: self._drain(p, False))
        p.readyReadStandardError.connect(lambda: self._drain(p, True))
        p.finished.connect(lambda code, status: self._finished(p, code, status))
        p.errorOccurred.connect(lambda error: self._error(p, error))
        self._timer.start(); self.state_changed.emit()
        p.start(str(self.cooker.resolve()), args)

    def _drain(self, p, stderr):
        if p is not self._process: return
        p.setReadChannel(QProcess.ProcessChannel.StandardError if stderr else QProcess.ProcessChannel.StandardOutput)
        target = self._err if stderr else self._out
        while p.bytesAvailable():
            chunk = bytes(p.read(min(4096, p.bytesAvailable())))
            available = LIMIT - len(target); target.extend(chunk[:available])
            if len(chunk) > available:
                self._failure = 'Native project asset output exceeds 64 KiB'; p.kill(); return

    def _timeout(self):
        if self._process is not None:
            self._failure = 'Native project asset operation timed out'; self._process.kill()

    def stop(self):
        if self._process is not None:
            self._cancelled = True; self._process.kill()

    def _error(self, p, error):
        if p is self._process and error == QProcess.ProcessError.FailedToStart:
            self._failure = p.errorString(); self._finished(p, -1, QProcess.ExitStatus.CrashExit)

    def _finished(self, p, code, status):
        if p is not self._process: return
        self._drain(p, False); self._drain(p, True)
        mode, context, failure = self._mode, self._context, self._failure
        cancelled, raw, error = self._cancelled, bytes(self._out), bytes(self._err[-2048:]).decode('utf-8', 'replace')
        self._process = None; self._timer.stop(); p.deleteLater()
        try:
            if cancelled or failure or code != 0 or status != QProcess.ExitStatus.NormalExit:
                raise ValueError('Project asset operation cancelled' if cancelled else failure or error or 'Native asset operation failed')
            value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=_pairs, parse_constant=_constant)
            if type(value) is not dict or value.get('status') != 'passed':
                raise ValueError('Native asset operation did not pass')
            if mode == 'adopt':
                AssetDependency(*(value[name] for name in ('asset_id', 'asset_sha256', 'pack_sha256')))
            elif mode == 'stage':
                if type(value.get('refs')) is not list or len(value['refs']) > 64:
                    raise ValueError('Invalid native staged dependency receipt')
                actual = tuple(sorted(AssetDependency(*(row[name] for name in ('asset_id', 'asset_sha256', 'pack_sha256'))) for row in value['refs']))
                if actual != context: raise ValueError('Staged dependency receipt differs from requested references')
            elif mode == 'inspect':
                from .asset_view import AssetView
                value = dict(value, assets=AssetView._rows(value))
            self.receipt.emit(mode, value)
        except Exception as exc:
            self.failed.emit(str(exc))
        self.state_changed.emit(); self.closed.emit()

    def shutdown(self):
        self.stop(); p = self._process
        if p is not None and not p.waitForFinished(1000):
            p.kill(); p.waitForFinished(1000)
