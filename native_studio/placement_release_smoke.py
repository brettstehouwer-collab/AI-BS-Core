"""Explicit two-process frozen placement acceptance; no normal Studio services."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import uuid

from PyQt6.QtGui import QFont, QFontDatabase, QGuiApplication
from PyQt6.QtWidgets import QApplication
from native_studio.engine import EngineBus
from native_studio.game_build_view import GameBuildNativeView
from native_studio.theme import STYLESHEET

KIND = 'frozen_placement_two_process'
REFERENCE_FIELDS = ('asset_id', 'asset_sha256', 'pack_sha256')
REQUIRED_BINARIES = {'content_host': 'aibs_content_host.exe', 'asset_cooker': 'aibs_assetc.exe',
                     'chapter_viewport': 'aibs_creator_viewport.exe', 'chapter_player': 'aibs_motherboard.exe'}


def _require(value, message):
    if not value:
        raise RuntimeError(message)


def _hash(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def _plain(path, *, exists=True):
    path = Path(path)
    _require('..' not in path.parts, 'Parent traversal is not an owned proof path')
    path = path.absolute()
    _require('..' not in path.parts, 'Parent traversal is not an owned proof path')
    for part in (path, *path.parents):
        _require(not part.is_symlink() and not part.is_junction(), 'Redirected proof/bundle path is forbidden: ' + str(part))
    return path.resolve(strict=exists)


def _json(path):
    path = _plain(path)
    _require(path.is_file() and 0 < path.stat().st_size <= 1024 * 1024, 'Source proof JSON is absent or exceeds its byte bound')
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'Duplicate source proof JSON key')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def _load_source_report(path):
    """Validate phase-one ownership before reading or renaming project inputs."""
    path = _plain(path)
    data = _json(path)
    _require(type(data) is dict and data.get('schema_version') == 1 and data.get('kind') == KIND
        and data.get('phase') == 'create' and data.get('status') == 'passed'
        and data.get('frozen') is True and data.get('all_owned_processes_joined') is True,
        'Source proof must be a passed, joined frozen create phase')
    work = _plain(data.get('work_directory', ''))
    _require(work.is_dir() and work.parent == path.parent and work.name.startswith(path.stem + '-work-'),
        'Source proof work directory is not owned by its first phase')
    project = _plain(data.get('project_root', ''))
    _require(project == work / 'project' and data.get('saved_project_root') == str(project),
        'Source proof project is not the exact owned project directory')
    marker = _plain(work / 'placement-proof-owner.json')
    _require(_hash(marker) == data.get('owner_marker_sha256'), 'Source proof ownership marker changed')
    token = data.get('owner_token', '')
    _require(type(token) is str and str(uuid.UUID(token)) == token, 'Source proof ownership token is invalid')
    _require(_json(marker) == {'schema_version': 1, 'kind': KIND, 'owner_token': token,
        'work_directory': str(work), 'project_root': str(project), 'create_report': str(path)},
        'Source proof ownership marker does not identify this project/report')
    _require(type(data.get('app_process_id')) is int and data['app_process_id'] > 0,
        'Source proof application identity is missing')
    _require(re.fullmatch('[0-9a-f]{64}', data.get('asset_reference', {}).get('pack_sha256', '')) is not None,
        'Source proof pack identity is invalid')
    return data, work, project


def _four_hashes(root, asset_sha):
    root = _plain(root)
    _require(root.is_dir() and re.fullmatch('[0-9a-f]{64}', asset_sha) is not None, 'Invalid owned asset pack directory/hash')
    names = {'catalog.aibcat', asset_sha + '.aibmesh', 'LICENSE.txt', 'provenance.json'}
    _require({path.name for path in root.iterdir()} == names, 'Expected exactly four immutable pack files')
    result = {}
    for name in sorted(names):
        path = _plain(root / name)
        _require(path.is_file() and 0 < path.stat().st_size <= 32 * 1024 * 1024, 'Invalid bounded immutable pack file')
        result[name] = _hash(path)
    _require(result[asset_sha + '.aibmesh'] == asset_sha, 'Owned mesh differs from its pinned immutable SHA')
    return result


def _bundle_inputs(data):
    _require(bool(getattr(sys, 'frozen', False)) and bool(getattr(sys, '_MEIPASS', None)),
        'Placement release smoke requires a frozen bundle; source fallback is forbidden')
    bundle = _plain(Path(sys._MEIPASS))
    _require(Path(__file__).resolve().is_relative_to(bundle), 'Placement smoke module did not resolve from the frozen bundle')
    data['bundle_root'] = str(bundle)
    for label, name in REQUIRED_BINARIES.items():
        path = _plain(bundle / 'game_assets/player' / name)
        _require(path.is_file(), 'Missing frozen native executable: ' + name)
        data['native_executables'][label] = str(path)
    for name in ('motherboard.vs.cso', 'motherboard.ps.cso'):
        _require(_plain(bundle / 'game_assets/player/shaders' / name).is_file(), 'Missing frozen renderer shader: ' + name)
    sample = _plain(bundle / 'game_assets/reference_part')
    _require((sample / 'catalog.aibcat').is_file(), 'Bundled reference asset catalog is missing')
    data['bundled_sample_root'] = str(sample)
    return bundle, sample


def _module_paths(bundle, data):
    names = ('native_studio.placement_release_smoke', 'native_studio.game_build_view',
        'native_studio.game_engine.content_view', 'native_studio.game_engine.project_assets',
        'native_studio.game_engine.content_commands', 'native_studio.game_engine.content_preview',
        'native_studio.game_engine.content_play')
    data['module_paths'] = {}
    for name in names:
        module = sys.modules.get(name)
        _require(module is not None and getattr(module, '__file__', None), 'Frozen placement module is missing: ' + name)
        path = Path(module.__file__).resolve()
        _require(path.is_relative_to(bundle), 'Placement module used checkout/source fallback: ' + name)
        data['module_paths'][name] = str(path)


def _row(chapter, identity):
    return next(row for row in chapter.rows if row.uuid == identity)


def _state(chapter, identity):
    head, description = chapter.client.head, chapter.description
    row = _row(chapter, identity)
    fields = dict(row.fields)
    return {'placement_id': identity, 'fields': fields,
        'asset_reference': {name: fields[name] for name in REFERENCE_FIELDS},
        'trs': {name: fields[name] for name in ('x', 'y', 'z', 'scale_x', 'scale_y', 'scale_z',
            'rotation_x', 'rotation_y', 'rotation_z', 'rotation_w')},
        'world_id': head.scope.world_id, 'project_id': head.scope.project, 'branch_id': head.scope.branch,
        'head_revision': head.head_revision, 'fingerprint': description.fingerprint,
        'content_revision': description.content_revision, 'checkpoint_id': head.checkpoint_id,
        'undo_depth': head.undo_depth, 'redo_depth': head.redo_depth, 'host_epoch': head.scope.host_epoch}


def _assert_saved_state(chapter, source):
    actual = _state(chapter, source['placement_id'])
    for key in ('placement_id', 'fields', 'asset_reference', 'trs', 'world_id', 'project_id', 'branch_id',
                'head_revision', 'fingerprint', 'content_revision', 'checkpoint_id', 'undo_depth', 'redo_depth'):
        _require(actual[key] == source[key], 'Saved placement reopen differs in ' + key)
    return actual


def _missing_dependency_probe(session, data, pack, held):
    """Fault only an already-validated owned pack and restore it before cleanup."""
    chapter = session.chapter
    player_count = sum(row['kind'] == 'chapter_player' for row in data.get('observed_processes', []))
    messages = []
    callback = messages.append
    chapter.play.message.connect(callback)
    try:
        pack.rename(held)
        try:
            chapter.start_play()
            session.wait(lambda: not chapter.busy and chapter.play.state == 'closed'
                and chapter.play.dependency_process_id == 0,
                'Missing dependency did not stop before player launch', seconds=35)
            session.observe()
            _require(chapter.play.process_id == 0 and
                sum(row['kind'] == 'chapter_player' for row in data.get('observed_processes', [])) == player_count
                and any('staging failed' in message.lower() for message in messages),
                'Missing immutable dependency was not rejected before launching a native player')
            data['metrics']['missing_dependency_rejected_before_player'] = True
            data['metrics']['missing_dependency_messages'] = messages
        finally:
            _require(held.is_dir() and not pack.exists(), 'Owned missing-dependency restore paths changed unexpectedly')
            held.rename(pack)
            data['missing_dependency_restored'] = True
    finally:
        chapter.play.message.disconnect(callback)


class _Session:
    def __init__(self, data, work, bundle):
        self.data, self.work, self.bundle = data, work, bundle
        self.app = self.bus = self.view = self.chapter = None
        self.seen = set()
        self.artifact_id = uuid.uuid4().hex

    def observe(self):
        chapter = self.chapter
        if chapter is None:
            return
        children = [('content_host', chapter.client._process), ('asset_cooker', chapter.asset_client._process),
            ('viewport_stage', chapter.viewport._stager._process), ('chapter_viewport', chapter.viewport._process),
            ('play_stage', chapter.play._stager._process), ('chapter_player', chapter.play._process)]
        for kind, process in children:
            if process is None or process in self.seen:
                continue
            self.seen.add(process)
            expected = self.data['native_executables'][
                'asset_cooker' if kind in ('viewport_stage', 'play_stage') else kind]
            def started(process=process, kind=kind, expected=expected):
                try:
                    path = str(Path(process.program()).resolve())
                    if path != expected:
                        self.data.setdefault('observer_errors', []).append(kind + ' used a non-bundled executable: ' + path)
                    pid = int(process.processId())
                    if pid:
                        label = kind + '_' + str(len(self.data['observed_process_ids']) + 1)
                        self.data['observed_process_ids'][label] = pid
                        self.data.setdefault('observed_processes', []).append({'kind': kind, 'pid': pid, 'executable': path})
                except RuntimeError as error:
                    self.data.setdefault('observer_errors', []).append(str(error))
            process.started.connect(started)
            if process.processId():
                started()

    def wait(self, predicate, message, seconds=35):
        deadline = time.monotonic() + seconds
        while not predicate() and time.monotonic() < deadline:
            self.observe()
            self.app.processEvents()
            self.observe()
            _require(not self.data.get('observer_errors'), '; '.join(self.data.get('observer_errors', [])))
            time.sleep(.004)
        details = '' if self.chapter is None else '; ' + self.chapter.status.text() + '; ' + self.chapter.asset_status.text()
        _require(predicate(), message + details)

    def idle(self):
        self.wait(lambda: self.chapter.loaded and not self.chapter.busy and not self.chapter.client.pending_count,
                  'Native chapter authoring did not become idle')

    def setup(self):
        self.app = QApplication.instance() or QApplication([])
        if not QFontDatabase.families() and Path('C:/Windows/Fonts/segoeui.ttf').is_file():
            QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
        self.app.setFont(QFont('Segoe UI', 10))
        self.app.setStyleSheet(STYLESHEET)
        self.data.update(qt_platform=QGuiApplication.platformName(), font_family=self.app.font().family(),
                         font_families_available=len(QFontDatabase.families()))
        _require(self.data['font_families_available'] > 0, 'A readable Windows Qt font is required')
        synthetic = self.work / ('synthetic-checkout-' + self.data['phase'] + '-' + self.artifact_id)
        synthetic.mkdir()
        self.data['workspace_root'] = str(synthetic)
        self.bus = EngineBus(max_threads=1)
        self.view = GameBuildNativeView(self.bus, root=synthetic)
        self.view.resize(1580, 1100)
        self.view.show()
        self.wait(lambda: not self.view.pending, 'Synthetic native workspace monitor did not complete')
        self.view.timer.stop()
        _require(self.view.creator_view is None and self.view.content_view is None and self.view.asset_view is None,
                 'Creator and Assets tabs must remain lazy')
        self.view.workspace_tabs.setCurrentIndex(2)
        self.chapter = self.view.content_view
        _require(self.chapter is not None and self.view.creator_view is None and self.view.asset_view is None,
                 'Actual Chapter creator tab did not open lazily')
        chapter = self.chapter
        _require(chapter.executable.resolve() == Path(self.data['native_executables']['content_host'])
            and chapter.asset_cooker.resolve() == Path(self.data['native_executables']['asset_cooker'])
            and chapter.sample_asset_pack.resolve() == Path(self.data['bundled_sample_root']),
            'Chapter creator selected source/SDK fallback paths')
        _require(chapter._play_binary().resolve() == Path(self.data['native_executables']['chapter_player']),
                 'Chapter Play selected a source/SDK fallback')
        _module_paths(self.bundle, self.data)
        for signal in (chapter.client.state_changed, chapter.asset_client.state_changed,
                       chapter.play.state_changed, chapter.viewport.message,
                       chapter.viewport._stager.state_changed, chapter.play._stager.state_changed):
            signal.connect(lambda *_: self.observe())

    def capture(self, name):
        path = self.work / (self.data['phase'] + '-' + self.artifact_id + '-' + name + '.png')
        self.app.processEvents()
        _require(self.view.grab().save(str(path)), 'Could not capture readable native placement GUI')
        self.data['captures'][name] = str(path)

    def close(self):
        errors = []
        chapter = self.chapter
        if chapter is not None:
            try:
                chapter.cancel_ai_generation('Placement acceptance completed')
                self.wait(lambda: not chapter.busy and not chapter.client.pending_count,
                          'Pending chapter operation did not drain', seconds=15)
                if chapter.definition is not None or chapter.client.state != 'closed':
                    chapter.close_project(discard=True)
                self.wait(lambda: chapter.client.state == 'closed' and chapter.viewport.state == 'closed'
                    and chapter.play.state == 'closed' and not chapter.asset_client.busy,
                    'Owned placement processes did not join', seconds=25)
            except Exception as error:
                errors.append(str(error))
                chapter.viewport._shutdown()
                chapter.play._shutdown()
                chapter.asset_client.shutdown()
                chapter.client._at_exit()
            self.data['final_process_ids'] = {'content_host': chapter.client.process_id,
                'asset_cooker': chapter.asset_client.process_id, 'viewport': chapter.viewport.process_id,
                'viewport_stage': chapter.viewport.dependency_process_id, 'play': chapter.play.process_id,
                'play_stage': chapter.play.dependency_process_id}
        else:
            self.data['final_process_ids'] = {}
        self.data['all_owned_processes_joined'] = all(pid == 0 for pid in self.data['final_process_ids'].values())
        if self.view is not None and self.data['all_owned_processes_joined']:
            self.view.close()
            self.view.deleteLater()
            self.app.processEvents()
        if self.bus is not None:
            self.bus.shutdown()
        if errors or not self.data['all_owned_processes_joined']:
            self.data['status'] = 'failed'
            self.data['cleanup_errors'] = errors or ['Owned placement children remain alive']


def _create(session, data, project):
    chapter = session.chapter
    project.mkdir()
    chapter.new_project(project, 'Frozen persisted placement proof')
    session.idle()
    _require('chapter-assets-v1' in chapter.client.capabilities, 'Bundled host lacks placement capability')
    chapter.save_world()
    session.idle()
    saved = _hash(project / 'chapter.aiba')
    baseline_head, baseline_fp = chapter.client.head.head_revision, chapter.description.fingerprint
    chapter.asset_name_input.setText('Frozen bundled reference part')
    _require(chapter.sample_asset_button is not None and chapter.sample_asset_button.isEnabled(),
             'Use bundled sample part button is unavailable')
    chapter.sample_asset_button.click()
    session.wait(lambda: chapter.adopted_asset is not None and not chapter.asset_client.busy,
                 'Bundled sample inspection/adoption did not complete')
    _require(chapter.asset_place_button.isEnabled(), 'Native placement Preview button is unavailable')
    chapter.asset_place_button.click()
    session.wait(lambda: chapter.apply_button.isEnabled() and not chapter.busy, 'Native placement preview was not prepared')
    _require(chapter.client.head.head_revision == baseline_head and chapter.description.fingerprint == baseline_fp
        and not any(row.type_id == 'authoring.AssetPlacement' for row in chapter.rows)
        and _hash(project / 'chapter.aiba') == saved, 'Private placement Preview published changes or rewrote the save')
    data['metrics']['placement_preview_private'] = True
    data['metrics']['placement_preview_details'] = chapter.preview_details.toPlainText()
    session.capture('private-preview')
    chapter.apply_button.click()
    session.idle()
    placement = next(row for row in chapter.rows if row.type_id == 'authoring.AssetPlacement')
    identity = placement.uuid
    _require(_hash(project / 'chapter.aiba') == saved, 'Placement Apply implicitly saved the authored journal')
    chapter.undo_button.click()
    session.idle()
    _require(not any(row.uuid == identity for row in chapter.rows), 'Placement Undo did not restore the baseline')
    chapter.redo_button.click()
    session.idle()
    _require(chapter.select_entity(identity), 'Placement Redo lost its stable UUID')
    edits = {'name': 'Frozen persisted motherboard part', 'x': '-13', 'y': '2.8', 'z': '-5',
             'scale_x': '0.75', 'scale_y': '1', 'scale_z': '0.75',
             'rotation_x': '0', 'rotation_y': str(math.sin(math.pi / 8)),
             'rotation_z': '0', 'rotation_w': str(math.cos(math.pi / 8))}
    for name, value in edits.items():
        chapter.field_editors[name].setText(value)
    before = _state(chapter, identity)
    chapter.preview_button.click()
    session.wait(lambda: chapter.apply_button.isEnabled() and not chapter.busy, 'Typed placement transform Preview failed')
    _require(_state(chapter, identity) == before and _hash(project / 'chapter.aiba') == saved,
             'Transform Preview changed published placement state or saved bytes')
    data['metrics']['transform_preview_private'] = True
    chapter.apply_button.click()
    session.idle()
    _require(_hash(project / 'chapter.aiba') == saved, 'Typed placement Apply implicitly saved the journal')
    fields = dict(_row(chapter, identity).fields)
    _require(fields['name'] == edits['name'] and fields['x'] == -13.0 and fields['scale_x'] == .75,
             'Typed name/TRS authoring did not reach the native owner')
    _require(all(chapter.field_editors[name].isReadOnly() for name in REFERENCE_FIELDS),
             'Immutable asset references are not read-only in the actual native GUI')
    chapter.save_button.click()
    session.idle()
    _require(not chapter.client.dirty, 'Explicit Save did not mark the placement journal saved')
    data.update(_state(chapter, identity))
    data['save_sha256'] = _hash(project / 'chapter.aiba')
    data['metadata_sha256'] = _hash(project / '.aibs-chapter-project.json')
    reference = data['asset_reference']
    pack = project / 'assets/packs' / reference['pack_sha256']
    data['pack_hashes'] = _four_hashes(pack, reference['asset_sha256'])
    data['bundled_sample_hashes'] = _four_hashes(Path(data['bundled_sample_root']), reference['asset_sha256'])
    _require(data['pack_hashes'] == data['bundled_sample_hashes'], 'Native project adoption changed bundled sample bytes')
    session.capture('saved-placement')
    data['checks'] += ['Actual lazy frozen Chapter creator used its bundled sample button and native adoption',
        'Native private Preview, explicit Apply, Undo/Redo and typed name/TRS editing passed',
        'Explicit Save retained placement UUID, immutable references, history and four exact dependency files']


def _reopen(session, data, source, work, project):
    _require(data['app_process_id'] != source['app_process_id'], 'Reopen requires a new application process')
    _require(_hash(project / 'chapter.aiba') == source['save_sha256']
        and _hash(project / '.aibs-chapter-project.json') == source['metadata_sha256'],
        'Saved first-phase project bytes changed before reopening')
    chapter = session.chapter
    chapter.open_project(project)
    session.idle()
    actual = _assert_saved_state(chapter, source)
    _require(actual['host_epoch'] != source['host_epoch'], 'Reopen did not create a new native authoring owner epoch')
    data.update(actual)
    data.update(prior_host_epoch=source['host_epoch'], source_app_process_id=source['app_process_id'],
                source_report_sha256=source['_source_report_sha256'])
    _require(chapter.select_entity(source['placement_id']), 'Reopened placement UUID is absent from the native outliner')
    data['checks'].append('A new frozen app/native owner reopened exact saved UUID/reference/TRS/fingerprint/head/history and a new epoch')
    session.capture('reopened-placement')
    probe = work / ('reopen-native-preview-' + str(uuid.uuid4()))
    probe.mkdir()
    # The initial publisher has no selection argument in the product API. Pin
    # the actual outliner selection for the native Win32 self-test's click target.
    publish = chapter.viewport.publish
    def selected_publish(scope, revision, checkpoint, snapshot, first_boot=False, selected_id=None):
        selected_id = selected_id or chapter.selected_id
        _require(selected_id == source['placement_id'] and selected_id in snapshot.entity_ids,
                 'Native probe selection is not the actual persisted outliner UUID')
        return publish(scope, revision, checkpoint, snapshot, first_boot, selected_id)
    chapter.viewport.publish = selected_publish
    try:
        chapter.open_viewport(probe_directory=probe)
        session.wait(lambda: not chapter.busy and chapter.viewport.state == 'closed' and (probe / 'viewport.json').is_file(),
                     'Reopened native viewport did not capture and join', seconds=50)
    finally:
        chapter.viewport.publish = publish
    native = _json(probe / 'viewport.json')
    _require(native.get('selected_uuid') == source['placement_id'] and native.get('debug_errors') == 0
        and native.get('nonbackground_pixels', 0) > 100, 'Actual native viewport did not render/pick the persisted placement')
    data['metrics']['native_viewport'] = native
    data['captures']['native_viewport'] = str(probe / 'viewport.bmp')
    data['checks'].append('Bundled native viewport rendered and selected the persisted placement UUID, then joined')
    chapter.start_play()
    session.wait(lambda: chapter.play.state == 'ready', 'Reopened isolated Play did not become ready', seconds=50)
    scratch = chapter.play.workspace_path
    _require(scratch is not None and scratch.is_dir() and not scratch.is_relative_to(project),
             'Play did not own isolated scratch storage')
    ref = source['asset_reference']
    private_pack = scratch / 'assets/packs' / ref['pack_sha256']
    data['private_play_pack_hashes'] = _four_hashes(private_pack, ref['asset_sha256'])
    _require(data['private_play_pack_hashes'] == source['pack_hashes']
        and chapter.play.snapshot.fingerprint == source['fingerprint'], 'Play did not consume the exact private immutable dependency closure')
    session.capture('isolated-play')
    chapter.stop_play()
    session.wait(lambda: chapter.play.state == 'closed' and chapter.play.dependency_process_id == 0,
                 'Reopened Play did not drain and join', seconds=35)
    data['metrics']['play_stop'] = chapter.play.last_result
    _require(chapter.play.last_result and chapter.play.last_result['graceful'] and chapter.play.last_result['saved']
        and not scratch.exists(), 'Native Play close did not verify a saved drain and remove owned scratch')
    data['play_scratch_removed'] = True
    data['checks'].append('Isolated Play copied exact private packs, rendered READY, then Stop drained/joined and removed its scratch')

    # Reversible fault injection is constrained to the exact first-phase-owned
    # pack child; authored metadata and save files are never moved or edited.
    pack = _plain(project / 'assets/packs' / ref['pack_sha256'])
    held = _plain(work / ('held-pack-' + ref['pack_sha256']), exists=False)
    _require(pack.is_relative_to(work) and held.parent == work and not held.exists(),
             'Missing-dependency test paths are not confined to the owned proof directory')
    _missing_dependency_probe(session, data, pack, held)
    _assert_saved_state(chapter, source)
    _require(_hash(project / 'chapter.aiba') == source['save_sha256']
        and _hash(project / '.aibs-chapter-project.json') == source['metadata_sha256']
        and _four_hashes(pack, ref['asset_sha256']) == source['pack_hashes']
        and _four_hashes(Path(data['bundled_sample_root']), ref['asset_sha256']) == source['bundled_sample_hashes'],
        'Reopen/viewport/Play/negative proof changed saved metadata, journal or immutable pack inputs')
    data['save_sha256'], data['metadata_sha256'], data['pack_hashes'] = source['save_sha256'], source['metadata_sha256'], source['pack_hashes']
    data['checks'].append('A missing owned pack blocked Play before player launch; exact folder restored and all original bytes preserved')


def _run(report, phase, source_report=None):
    report = Path(report).resolve()
    if report.exists():
        return 2
    started = time.monotonic()
    data = {'schema_version': 1, 'kind': KIND, 'phase': phase, 'status': 'failed', 'checks': [], 'metrics': {},
        'frozen': bool(getattr(sys, 'frozen', False)), 'app_process_id': os.getpid(),
        'application_services_started': False, 'actual_model_inference': False, 'model_downloads_started': False,
        'source_fallback': False, 'native_executables': {}, 'observed_process_ids': {}, 'captures': {},
        'all_owned_processes_joined': False}
    session = None
    try:
        bundle, sample = _bundle_inputs(data)
        if phase == 'create':
            report.parent.mkdir(parents=True, exist_ok=True)
            work = Path(tempfile.mkdtemp(prefix=report.stem + '-work-', dir=report.parent))
            project = work / 'project'
            owner = str(uuid.uuid4())
            marker = work / 'placement-proof-owner.json'
            _write_json(marker, {'schema_version': 1, 'kind': KIND, 'owner_token': owner,
                'work_directory': str(work), 'project_root': str(project), 'create_report': str(report)})
            data.update(owner_token=owner, owner_marker_sha256=_hash(marker))
            source = None
        else:
            source, work, project = _load_source_report(source_report)
            source['_source_report_sha256'] = _hash(source_report)
            data['source_report'] = str(Path(source_report).resolve())
        data.update(work_directory=str(work), project_root=str(project), saved_project_root=str(project))
        session = _Session(data, work, bundle)
        session.setup()
        if phase == 'create':
            _create(session, data, project)
        else:
            _reopen(session, data, source, work, project)
        data['status'] = 'passed'
    except Exception as error:
        data['error'] = str(error)
    finally:
        if session is not None:
            try:
                session.close()
            except Exception as error:
                data['status'] = 'failed'
                data['all_owned_processes_joined'] = False
                data.setdefault('cleanup_errors', []).append(str(error))
        else:
            data['final_process_ids'] = {}
            data['all_owned_processes_joined'] = True
        data['elapsed_seconds'] = round(time.monotonic() - started, 3)
        data['completed_at'] = datetime.now(timezone.utc).isoformat()
        _write_json(report, data)
    return 0 if data['status'] == 'passed' else 2


def run_placement_release_smoke(report):
    return _run(report, 'create')


def run_placement_reopen_smoke(report, source_report):
    return _run(report, 'reopen', source_report)


def placement_release_smoke_main(argv):
    parser = argparse.ArgumentParser(description='Explicit frozen two-process placement acceptance')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--placement-release-smoke', type=Path)
    mode.add_argument('--placement-reopen-smoke', type=Path)
    parser.add_argument('--placement-source-report', type=Path)
    options = parser.parse_args(argv)
    if options.placement_release_smoke is not None:
        if options.placement_source_report is not None:
            parser.error('--placement-source-report belongs to --placement-reopen-smoke')
        return run_placement_release_smoke(options.placement_release_smoke)
    if options.placement_source_report is None:
        parser.error('--placement-reopen-smoke requires --placement-source-report')
    return run_placement_reopen_smoke(options.placement_reopen_smoke, options.placement_source_report)
