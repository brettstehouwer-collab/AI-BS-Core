"""Explicit frozen Assets workspace acceptance without normal Studio services."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import uuid

from PyQt6.QtCore import QProcess
from PyQt6.QtGui import QFont, QFontDatabase, QGuiApplication
from PyQt6.QtWidgets import QApplication
from native_studio.engine import EngineBus
from native_studio.game_build_view import GameBuildNativeView
from native_studio.theme import STYLESHEET

REFERENCE_ASSET_ID = '8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264'
OUTPUT_LIMIT = 65536


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _wait(app, predicate, message, *, seconds=35):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.005)
    _require(predicate(), message)


def _hash(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def _bundle_path(bundle, relative):
    path = bundle / relative
    for part in (path, *path.parents):
        _require(not part.is_symlink() and not part.is_junction(), 'Redirected frozen bundle input: ' + str(part))
    resolved = path.resolve()
    _require(resolved.is_relative_to(bundle.resolve()), 'Frozen asset input escaped its bundle')
    return resolved


def _pack_hashes(root):
    rows = {}
    for path in sorted(Path(root).rglob('*')):
        _require(not path.is_symlink() and not path.is_junction(), 'Redirected proof pack entry')
        if path.is_file():
            rows[path.relative_to(root).as_posix()] = _hash(path)
    _require(bool(rows), 'Native asset pack is empty')
    return rows


def _capture(widget, path, data, name):
    _require(widget.grab().save(str(path)), 'Could not capture Assets workspace')
    data['captures'][name] = str(path)


def _observe_tool(assets, data, prefix, seen=None):
    """Observe real CLI children, including cook's automatic inspection."""
    seen = set() if seen is None else seen
    process = assets._tool
    if process is None or id(process) in seen:
        return
    seen.add(id(process))
    label = prefix + '_' + assets._context['mode']

    def started():
        pid = int(process.processId())
        if pid:
            data['observed_process_ids'][label] = pid

    process.started.connect(started)
    process.finished.connect(lambda *_: _observe_tool(assets, data, prefix, seen))
    started()


def _validate_native_proof(proof):
    _require(type(proof) is dict and proof.get('status') == 'passed', 'Native asset GPU proof did not pass')
    _require(proof.get('asset_id') == REFERENCE_ASSET_ID and proof.get('triangles') == 4788
        and proof.get('materials') == 8, 'Native GPU proof identifies a different reference part')
    metrics = proof.get('metrics', {})
    _require(metrics.get('debug_errors') == 0 and metrics.get('debug_layer') is True,
        'Native GPU proof lacks clean debug-layer validation')
    _require(metrics.get('nonbackground_pixels', 0) > 10000
        and metrics.get('asset_gpu_bytes_changed', 0) > 100
        and metrics.get('material_gpu_bytes_changed', 0) > 100,
        'Cooked mesh and material changes did not affect actual GPU pixels')
    _require(metrics.get('camera_input_verified') is True, 'Native asset camera input was not verified')
    _require(proof.get('source_fallback') is False and proof.get('save_formats_changed') is False,
        'Native proof used source fallback or changed save formats')


class _OwnedProbe:
    """One explicit native self-test child, bounded captures, no shell or detach."""
    def __init__(self):
        self.process = QProcess()
        self.stdout, self.stderr = bytearray(), bytearray()
        self.done = False
        self.code = None
        self.exit_status = None
        self.failure = ''
        self.pid = 0
        self.process.readyReadStandardOutput.connect(lambda: self._drain(False))
        self.process.readyReadStandardError.connect(lambda: self._drain(True))
        self.process.started.connect(self._started)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._error)

    def _started(self):
        self.pid = int(self.process.processId())

    def _drain(self, stderr):
        self.process.setReadChannel(QProcess.ProcessChannel.StandardError if stderr else QProcess.ProcessChannel.StandardOutput)
        buffer = self.stderr if stderr else self.stdout
        while self.process.bytesAvailable():
            chunk = bytes(self.process.read(min(4096, self.process.bytesAvailable())))
            available = OUTPUT_LIMIT - len(buffer)
            buffer.extend(chunk[:available])
            if len(chunk) > available:
                self.failure = 'Native asset self-test output exceeded 64 KiB'
                self.process.kill()
                return

    def _finished(self, code, status):
        self._drain(False)
        self._drain(True)
        self.code, self.exit_status, self.done = code, status, True

    def _error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.failure = self.process.errorString()
            self.code, self.done = -1, True

    def run(self, app, executable, arguments):
        self.process.setWorkingDirectory(str(executable.parent))
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.start(str(executable), arguments)
        _wait(app, lambda: self.done, 'Native asset GPU self-test timed out', seconds=60)
        _require(not self.failure and self.code == 0 and self.exit_status == QProcess.ExitStatus.NormalExit,
            self.failure or bytes(self.stderr[-2048:]).decode('utf-8', 'replace') or 'Native asset GPU child failed')

    def close(self, app):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            try:
                _wait(app, lambda: self.process.state() == QProcess.ProcessState.NotRunning,
                    'Native GPU child did not stop', seconds=2)
            except RuntimeError:
                self.process.kill()
                _wait(app, lambda: self.process.state() == QProcess.ProcessState.NotRunning,
                    'Owned native GPU child did not join', seconds=2)
        return int(self.process.processId()) == 0


def run_asset_release_smoke(report: Path) -> int:
    report = Path(report).resolve()
    started = time.monotonic()
    app = bus = view = assets = probe = None
    data = {'schema_version': 1, 'status': 'failed', 'checks': [], 'metrics': {},
        'frozen': bool(getattr(sys, 'frozen', False)), 'module_frozen': False,
        'application_services_started': False, 'actual_model_inference': False,
        'model_downloads_started': False, 'source_fallback': False,
        'native_executables': {}, 'observed_process_ids': {}, 'captures': {},
        'all_owned_processes_joined': False}
    try:
        _require(data['frozen'] and bool(getattr(sys, '_MEIPASS', None)),
            'Asset release smoke requires a frozen bundle; source fallback is forbidden')
        bundle = _bundle_path(Path(sys._MEIPASS).absolute(), '.')
        data['bundle_root'] = str(bundle)
        data['module_frozen'] = Path(__file__).resolve().is_relative_to(bundle)
        _require(data['module_frozen'], 'Asset acceptance module did not resolve from the frozen bundle')
        binary = bundle / 'game_assets/player'
        for name in ('aibs_assetc.exe', 'aibs_motherboard.exe', 'shaders/motherboard.vs.cso', 'shaders/motherboard.ps.cso'):
            _require(_bundle_path(bundle, 'game_assets/player/' + name).is_file(), 'Missing frozen native asset: ' + name)
        sample = _bundle_path(bundle, 'game_assets/reference_part')
        _require(_bundle_path(bundle, 'game_assets/reference_part/catalog.aibcat').is_file(), 'Missing frozen reference asset catalog')
        sample_hashes = _pack_hashes(sample)
        report.parent.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix=report.stem + '-work-', dir=report.parent))
        root = work / 'synthetic-checkout'
        root.mkdir()
        data.update(work_directory=str(work), workspace_root=str(root), report_path=str(report))
        _require(not (root / 'engine').exists(), 'Synthetic proof root must not contain an installed engine')
        app = QApplication.instance() or QApplication([])
        if not QFontDatabase.families():
            font = Path('C:/Windows/Fonts/segoeui.ttf')
            if font.is_file():
                QFontDatabase.addApplicationFont(str(font))
        app.setFont(QFont('Segoe UI', 10))
        app.setStyleSheet(STYLESHEET)
        data['qt_platform'] = QGuiApplication.platformName()
        data['font_family'] = app.font().family()
        data['font_families_available'] = len(QFontDatabase.families())
        _require(data['font_families_available'] > 0, 'No readable Windows Qt font is available')
        bus = EngineBus(max_threads=1)
        view = GameBuildNativeView(bus, root=root)
        view.resize(1500, 1100)
        view.show()
        _wait(app, lambda: not view.pending, 'Synthetic game workspace monitor did not complete')
        view.timer.stop()
        _require(view.asset_view is None and view.creator_view is None and view.content_view is None,
            'Assets and creator workspaces did not open lazily')
        view.workspace_tabs.setCurrentIndex(3)
        assets = view.asset_view
        _require(assets is not None and view.workspace_tabs.tabText(3) == 'Assets', 'Actual Assets tab did not open')
        for label, path, expected in (('asset_cooker', assets.cooker, binary / 'aibs_assetc.exe'),
                ('asset_player', assets.player, binary / 'aibs_motherboard.exe')):
            _require(Path(path).resolve() == expected.resolve(), label + ' used a checkout or SDK fallback')
            data['native_executables'][label] = str(Path(path).resolve())
        _require(assets.sample_pack.resolve() == sample.resolve(), 'Assets tab did not select the bundled sample')
        assets.inspect_pack(sample)
        _observe_tool(assets, data, 'reference')
        _wait(app, lambda: not assets.busy, 'Bundled sample inspection did not finish')
        _require(len(assets.asset_rows) == 1, 'Bundled sample native inspection failed: ' + assets.status.text())
        reference = assets.asset_rows[0]
        _require(reference['asset_id'] == REFERENCE_ASSET_ID and reference['triangles'] == 4788
            and reference['materials'] == 8, 'Native inspection identifies a different reference part')
        data['metrics']['reference_asset'] = reference
        _capture(view, work / 'assets-reference.png', data, 'assets_reference')
        data['checks'].append('Actual lazy Assets tab inspected the bundled 4788-triangle / 8-material reference part')

        assets.preview_selected()
        _wait(app, lambda: assets.preview_process_id > 0, 'Owned Assets preview did not start', seconds=10)
        data['observed_process_ids']['interactive_preview'] = assets.preview_process_id
        shown_at = time.monotonic()
        _wait(app, lambda: time.monotonic() - shown_at >= .2, 'Preview event pump failed', seconds=2)
        _require(assets.preview_process_id > 0, 'Native preview exited unexpectedly: ' + assets.status.text())
        assets.stop_preview()
        _wait(app, lambda: assets.preview_process_id == 0, 'Assets preview did not join', seconds=5)
        data['checks'].append('Assets Preview selected launched and Stop preview joined its owned native child')

        capture, native_report = work / 'reference-native.bmp', work / 'reference-native.json'
        data['native_gpu_report'] = str(native_report)
        probe = _OwnedProbe()
        probe.run(app, binary / 'aibs_motherboard.exe', ['--asset-showcase', '--asset-root', str(sample),
            '--asset-id', REFERENCE_ASSET_ID, '--self-test', '--capture', str(capture), '--report', str(native_report)])
        data['observed_process_ids']['gpu_probe'] = probe.pid
        _require(native_report.is_file() and native_report.stat().st_size <= 1024 * 1024,
            'Native GPU report is absent or too large')
        native = json.loads(native_report.read_text(encoding='utf-8'))
        _validate_native_proof(native)
        _require(capture.is_file() and capture.stat().st_size > 10000, 'Native GPU capture is absent')
        data['metrics']['native_gpu'] = native
        data['captures']['native_gpu'] = str(capture)
        (work / 'gpu.stdout.log').write_bytes(probe.stdout)
        (work / 'gpu.stderr.log').write_bytes(probe.stderr)
        data['checks'].append('Bundled native self-test verified geometry/material GPU pixel differences and camera input')

        inputs = work / 'owned-user-inputs'
        inputs.mkdir()
        source, materials, license = inputs / 'Owned triangle.obj', inputs / 'part.aibmat', inputs / 'LICENSE.txt'
        source.write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl copper\nf 1 2 3\n', encoding='utf-8')
        materials.write_text('AIBMAT 1\ncopper 0.8 0.35 0.05 0\n', encoding='utf-8')
        license.write_text('Original synthetic triangle supplied for this private acceptance run.\n', encoding='utf-8')
        input_hashes = _pack_hashes(inputs)
        cooked = work / 'new-user-pack'
        data.update(user_input_directory=str(inputs), cooked_output_root=str(cooked))
        identity = str(uuid.uuid4())
        assets.cook_asset(source, materials, license, cooked, identity, 'Owned native triangle')
        _observe_tool(assets, data, 'owned')
        _wait(app, lambda: not assets.busy, 'Actual native cook / automatic inspect did not finish')
        _require(len(assets.asset_rows) == 1 and assets.asset_rows[0]['asset_id'] == identity
            and assets.asset_rows[0]['triangles'] == 1 and assets.asset_rows[0]['materials'] == 1,
            'Native user cook / automatic inspect failed: ' + assets.status.text())
        mesh_files = list(cooked.glob('*.aibmesh'))
        _require(len(mesh_files) == 1 and _hash(mesh_files[0]) == assets.asset_rows[0]['sha256'],
            'Cooked native file bytes do not match the inspected identity')
        cooked_hashes = _pack_hashes(cooked)
        data['metrics']['cooked_asset'] = assets.asset_rows[0]
        _capture(view, work / 'assets-owned-cook.png', data, 'assets_owned_cook')
        assets.inspect_pack(cooked)
        _observe_tool(assets, data, 'reopen')
        _wait(app, lambda: not assets.busy, 'Reopening cooked user pack did not finish')
        _require(assets.asset_rows[0]['asset_id'] == identity, 'Cooked user pack identity changed on reopen')
        _require(view.creator_view is None and view.content_view is None, 'Asset acceptance opened unrelated authoring workspaces')
        _require(all(data['observed_process_ids'].get(name, 0) > 0
            for name in ('reference_inspect', 'owned_cook', 'owned_inspect', 'reopen_inspect')),
            'Native cooker/inspection child identities were not observed')
        _require(assets.prepare_close(), 'Idle Assets workspace did not close')
        data['metrics']['input_bytes_unchanged'] = _pack_hashes(inputs) == input_hashes
        data['metrics']['cooked_bytes_unchanged'] = _pack_hashes(cooked) == cooked_hashes
        data['metrics']['bundled_sample_bytes_unchanged'] = _pack_hashes(sample) == sample_hashes
        _require(all(data['metrics'][name] for name in ('input_bytes_unchanged', 'cooked_bytes_unchanged', 'bundled_sample_bytes_unchanged')),
            'Asset acceptance changed input, published output or bundled sample bytes')
        data['input_hashes'], data['cooked_hashes'], data['bundled_sample_hashes'] = input_hashes, cooked_hashes, sample_hashes
        data['checks'].append('Real native cooker / automatic inspection / reopen preserved exact owned inputs and published pack bytes')
        data['status'] = 'passed'
    except Exception as error:
        data['error'] = str(error)
    finally:
        cleanup_errors = []
        if assets is not None:
            try:
                assets.prepare_close()
                _wait(app, lambda: assets.tool_process_id == 0 and assets.preview_process_id == 0,
                    'Assets children did not join during cleanup', seconds=5)
            except Exception as error:
                cleanup_errors.append(str(error))
                assets.shutdown()
        if probe is not None:
            try:
                _require(probe.close(app), 'Native GPU probe did not join')
            except Exception as error:
                cleanup_errors.append(str(error))
            if 'work_directory' in data:
                (Path(data['work_directory']) / 'gpu.stdout.log').write_bytes(probe.stdout)
                (Path(data['work_directory']) / 'gpu.stderr.log').write_bytes(probe.stderr)
            data['native_gpu_process'] = {'exit_code': probe.code, 'error': probe.failure}
        data['final_process_ids'] = {'asset_tool': assets.tool_process_id if assets is not None else 0,
            'interactive_preview': assets.preview_process_id if assets is not None else 0,
            'gpu_probe': int(probe.process.processId()) if probe is not None else 0}
        data['all_owned_processes_joined'] = all(pid == 0 for pid in data['final_process_ids'].values())
        if view is not None:
            view.close()
            view.deleteLater()
            app.processEvents()
        if bus is not None:
            bus.shutdown()
        if cleanup_errors or not data['all_owned_processes_joined']:
            data['status'] = 'failed'
            data['cleanup_errors'] = cleanup_errors or ['Owned asset processes remain alive']
        data['elapsed_seconds'] = round(time.monotonic() - started, 3)
        data['completed_at'] = datetime.now(timezone.utc).isoformat()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return 0 if data['status'] == 'passed' else 2


def asset_release_smoke_main(argv) -> int:
    parser = argparse.ArgumentParser(description='Explicit frozen native asset acceptance')
    parser.add_argument('--asset-release-smoke', required=True, type=Path)
    options = parser.parse_args(argv)
    return run_asset_release_smoke(options.asset_release_smoke)
