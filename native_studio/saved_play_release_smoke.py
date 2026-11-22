"""Explicit frozen saved-chapter baseline acceptance, without Studio services.

Admission is stdlib-only. Qt, the curated factory and the game's own windows
are reached only after an explicit window flag and verified bundled resources.
Every output is retained; existing reports/projects/saves are never replaced.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

KIND = 'frozen_saved_chapter_baseline'
TOOLS = {'host': 'aibs_content_host.exe', 'player': 'aibs_motherboard.exe',
    'cooker': 'aibs_assetc.exe', 'factory': 'aibs_warm_opening_project.exe'}
FEATURES = frozenset(('chapter-saved-play-v1', 'durable_world', 'first_boot_chapter',
    'first_boot_content_play', 'chapter_content_export_v2', 'chapter_content_v3',
    'chapter_asset_surfaces', 'mesh_asset_v1', 'character_asset_v2', 'audio_asset_v2',
    'chapter-memory-audio-v1', 'chapter-authored-inspections-v1', 'chapter-initial-view-v1',
    'chapter-workshop-commissioning-v1'))


def _require(value, message):
    if not value:
        raise ValueError(message)


def _plain(path, *, exists=True):
    path = Path(path)
    _require('..' not in path.parts, 'Parent traversal is not an owned smoke path')
    path = path.absolute()
    for part in (path, *path.parents):
        _require(not part.is_symlink() and not part.is_junction(), 'Redirected smoke or bundle path is forbidden')
    return path.resolve(strict=exists)


def _owned_paths(report, work):
    report, work = _plain(report, exists=False), _plain(work, exists=False)
    _require(report.drive.lower() == work.drive.lower() == 'd:', 'Smoke outputs require explicitly owned D: paths')
    _require(report != work and work not in report.parents and report not in work.parents,
        'Smoke report and new work directory must be separate')
    _require(not report.exists() and report.parent.is_dir(), 'Choose a new report in an existing D: directory')
    _require(not work.exists() and work.parent.is_dir(), 'Choose a new work child in an existing D: directory')
    return report, work


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path, maximum):
    path = _plain(path)
    with path.open('rb') as stream:
        raw = stream.read(maximum+1)
    _require(0 < len(raw) <= maximum, 'Bundled metadata exceeds its byte bound')
    def pairs(items):
        result = {}
        for key,value in items:
            _require(key not in result, 'Duplicate bundled metadata field')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Nonfinite bundled metadata')
    value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)
    _require(type(value) is dict, 'Bundled metadata must be an object')
    return value


def _inventory(root, *, maximum=256):
    values = {}
    total = 0
    for path in root.rglob('*'):
        _plain(path)
        if not path.is_file():
            continue
        total += path.stat().st_size
        _require(len(values) < maximum and path.stat().st_size <= 48*1024*1024
            and total <= 128*1024*1024, 'Smoke input/retained inventory exceeds its bounded profile')
        values[path.relative_to(root).as_posix()] = {'bytes': path.stat().st_size, 'sha256': _sha(path)}
    return values


def _origin(module, bundle):
    _require(Path(module.__file__).resolve().is_relative_to(bundle), 'Smoke dependency did not resolve inside the frozen bundle')
    return str(Path(module.__file__).resolve())


def _bundle_inputs(data):
    _require(bool(getattr(sys, 'frozen', False)) and bool(getattr(sys, '_MEIPASS', None)),
        'Saved-play release smoke requires a frozen bundle; source fallback is forbidden')
    bundle = _plain(Path(sys._MEIPASS))
    _require(Path(__file__).resolve().is_relative_to(bundle), 'Bundled saved-play smoke module resolved outside its bundle')
    metadata = _json(bundle/'game_release.json', 1024*1024)
    _require(type(metadata.get('saved_chapter_play_included')) is bool
        and metadata['saved_chapter_play_included'] is True
        and type(metadata.get('require_saved_play')) is bool,
        'Bundled saved-play inclusion/requirement metadata is absent or inconsistent')
    binary = _plain(bundle/'game_assets/player')
    tools = {label: _plain(binary/name) for label,name in TOOLS.items()}
    _require(all(p.is_file() for p in tools.values()), 'Bundled saved-play native tools are incomplete')
    caps = _json(binary/'aibs_capabilities.json', 16*1024)
    version, features = caps.get('sdk_version'), caps.get('features')
    _require(type(caps.get('schema_version')) is int and caps['schema_version'] == 1
        and caps.get('target') == 'windows-x64' and type(version) is str
        and re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version)
        and tuple(map(int,version.split('.'))) >= (0,16,0) and type(features) is dict
        and all(type(key) is str and type(value) is bool for key,value in features.items())
        and all(features.get(key) is True for key in FEATURES), 'Bundled saved-play requires complete SDK0.16 capabilities')
    from native_studio.game_engine import opening_assets
    _origin(opening_assets,bundle)
    opening = _plain(bundle/'game_assets/opening')
    assets = opening_assets.read_opening_assets(opening, verify_pack_contents=True)
    data.update(bundle_root=str(bundle), native_executables={k:str(v) for k,v in tools.items()},
        bundled_sdk_version=version, opening_manifest_sha256=assets.manifest_sha256,
        bundled_native_inputs=_inventory(binary), bundled_opening_inputs=_inventory(opening))
    return {'bundle':bundle, 'binary':binary, 'tools':tools, 'opening':opening}


def _run_frozen(inputs, work, data):
    # Deliberately does not construct EngineBus, MainWindow or a provider service.
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import QApplication
    from native_studio.game_engine import content_view, saved_play, saved_play_storage, saved_chapter_export, opening_project
    bundle, tools = inputs['bundle'], inputs['tools']
    data['module_origins'] = {module.__name__:_origin(module,bundle) for module in
        (content_view,saved_play,saved_play_storage,saved_chapter_export,opening_project)}
    app = QApplication.instance() or QApplication([])
    app.setFont(QFont('Segoe UI',10))
    work.mkdir()
    project = work/'chapter'
    data['work_directory'], data['project_directory'] = str(work), str(project)
    view = content_view.ContentView(tools['host'], asset_cooker=tools['cooker'],
        opening_factory=tools['factory'], opening_assets_root=inputs['opening'])

    def check(value,message):
        _require(value,message)
        data['checks'].append(message)
    def spin(predicate,message,seconds=75,abort_when=None):
        deadline = time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:
            app.processEvents()
            if abort_when is not None and abort_when():
                raise ValueError(message+': '+view.status.text())
            time.sleep(.003)
        check(bool(predicate()),message+': '+view.status.text())
    def idle():
        spin(lambda:view.loaded and not view.busy and not view.client.pending_count, 'Bundled creator owner coherent')
    def invoke(label):
        journal = saved_chapter_export.hash_saved_journal(project)
        before = time.monotonic()
        previous_session = view.saved_play.session_id
        view.start_saved_play()
        spin(lambda:view.saved_play.state=='ready',label+' actual native READY',
            abort_when=lambda:view.saved_play.session_id!=previous_session and view.saved_play.state=='closed')
        client = view.saved_play
        pub = saved_play_storage.revalidate_publication(client.publication)
        check(client.process_id>0 and view.saved_export.process_id==client.dependency_process_id==0,
            label+' saved export and native dependency stage joined before READY')
        data['native_windows_started'] += 1
        check(view._saved_play_binary()==tools['player'],label+' selected the actual bundled native player')
        check(len(client.snapshot.asset_refs)==6 and 2 not in client.snapshot.dependency_kinds,
            label+' complete six-pack non-audio closure')
        head = tuple(client._ready_head)
        session = client.session_id
        view.stop_saved_play()
        spin(lambda:client.state=='closed' and client.process_id==client.dependency_process_id==0,
            label+' native STOPPED and actual child exit',30)
        result = dict(client.last_result or {})
        check(result.get('saved') is True and result.get('graceful') is True and result.get('forced') is False
            and result.get('ready_seen') is True and result.get('play_session')==session
            and result.get('timeline_id')==pub.timeline_id and result.get('context')=='player_world',
            label+' verified player-world save-drain receipt')
        check(all(result[key]>=old for key,old in zip(('durable_revision','durable_sequence'),head)),
            label+' durable head did not regress')
        check(pub.database_path.is_file(),label+' retained native database exists')
        check(saved_chapter_export.hash_saved_journal(project)==journal,label+' gameplay launch did not implicitly save authoring')
        data['invocations'].append({'label':label,'session_id':session,'timeline_id':pub.timeline_id,
            'fingerprint':client.snapshot.fingerprint,'reused_slot':pub.reused_slot,'reused_publication':pub.reused_publication,
            'database':str(pub.database_path),'database_sha256':_sha(pub.database_path),'result':result,
            'wall_seconds':time.monotonic()-before,'stdout_tail':client.stdout_tail.decode('utf-8','replace'),
            'stderr_tail':client.stderr_tail.decode('utf-8','replace')})
        return pub
    try:
        view.resize(1200,900)
        view.show()
        view.create_first_boot_opening(project)
        spin(lambda:view.loaded and not view.busy and not view.opening_client.busy
            and not view.client.pending_count,'Actual bundled curated factory created and opened a new chapter')
        check(view.opening_client.process_id==0 and view.definition.directory==project,
            'Bundled factory/inspect children joined before authoring')
        check(view.definition.opening_workshop and not any(row.type_id=='authoring.MemoryBinding' for row in view.rows),
            'Actual curated Workshop chapter has no original-memory playback binding')
        view.add_fixture('Frozen saved-play verification marker')
        idle()
        check(view.client.dirty,'Authored marker is unsaved before explicit Save')
        view.save_world()
        idle()
        check(not view.client.dirty and not view.description.dirty,'Authored marker explicitly saved')
        first = invoke('first authored saved chapter')
        first_session = data['invocations'][-1]['session_id']
        fingerprint = view.description.fingerprint
        view.save_world()
        idle()
        check(view.description.fingerprint==fingerprint,'Unchanged explicit Save keeps content identity')
        second = invoke('resume unchanged saved chapter')
        check(second.timeline_id==first.timeline_id and second.database_path==first.database_path
            and data['invocations'][-1]['session_id']!=first_session and second.reused_slot,
            'Resume uses a new invocation and the same retained timeline/database')
        old_slot, old_content = _inventory(first.slot_directory), _inventory(first.content_directory)
        view.add_fixture('Frozen saved-play new content branch marker')
        idle()
        rejected = False
        try:view.start_saved_play()
        except ValueError:rejected=True
        check(rejected and view.saved_play.state=='closed','Unsaved authored edit cannot auto-save or launch')
        view.save_world()
        idle()
        check(view.description.fingerprint!=fingerprint,'Second actual authored Save changes immutable content identity')
        third = invoke('new saved content branch')
        check(third.timeline_id!=first.timeline_id and third.database_path!=first.database_path and not third.reused_slot,
            'Changed saved content receives a distinct retained timeline/database')
        check(_inventory(first.slot_directory)==old_slot and _inventory(first.content_directory)==old_content,
            'Every old database/claim/slot/publication byte preserved after new branch')
    finally:
        view.opening_client.stop()
        view.saved_export.stop()
        view.saved_play.stop()
        view.play.stop()
        view.viewport.stop()
        view.asset_client.stop()
        deadline = time.monotonic()+18
        while (not view._children_closed() or view.opening_client.busy) and time.monotonic()<deadline:
            app.processEvents();time.sleep(.003)
        if not view._children_closed():
            view.saved_play.shutdown();view.play._shutdown();view.viewport._shutdown();view.asset_client.shutdown()
        view.client.stop()
        deadline = time.monotonic()+5
        while (view.client.process_id or view.saved_export.process_id or view.opening_client.process_id) and time.monotonic()<deadline:
            app.processEvents();time.sleep(.003)
        ids = {'host':view.client.process_id,'factory':view.opening_client.process_id,
            'saved_export':view.saved_export.process_id,'saved_player':view.saved_play.process_id,
            'saved_dependency':view.saved_play.dependency_process_id,'isolated_play':view.play.process_id,
            'preview':view.viewport.process_id,'project_asset':view.asset_client.process_id}
        data['final_process_ids']=ids
        data['last_saved_play_diagnostics']={'state':view.saved_play.state,'result':view.saved_play.last_result,
            'stdout_tail':view.saved_play.stdout_tail.decode('utf-8','replace'),
            'stderr_tail':view.saved_play.stderr_tail.decode('utf-8','replace'),
            'creator_status':view.status.text(),'factory_state':view.opening_client.state,
            'factory_availability':view.opening_client.availability_error}
        data['all_owned_processes_joined']=not any(ids.values())
        if data['all_owned_processes_joined']:
            view.definition=None;view.close();view.deleteLater();app.processEvents()
        check(data['all_owned_processes_joined'],'Every factory/owner/export/stager/player actually joined')
        check(_inventory(inputs['binary'])==data['bundled_native_inputs']
            and _inventory(inputs['opening'])==data['bundled_opening_inputs'],'All bundled input bytes remained unchanged')


def run_saved_play_release_smoke(report, work, *, allow_native_window=False):
    data = {'schema_version':1,'kind':KIND,'status':'failed','frozen':bool(getattr(sys,'frozen',False)),
        'application_services_started':False,'actual_model_inference':False,'original_family_media_used':False,
        'route_or_action_durability_verified':False,'performance_or_pacing_verified':False,'likeness_approved':False,
        'native_windows_started':0,'checks':[],'invocations':[],
        'limitations':['Launch/resume/explicit authoring Save/branching baseline only; no route or gameplay-action durability claimed.',
            'No normal Studio services, provider requests, desktop input/capture, original family media or source-project fallback.',
            'Projects, publications and native saves remain retained in the explicit new work directory.']}
    destination = None
    report_admitted = False
    try:
        destination = _plain(report,exists=False)
        _require(destination.drive.lower()=='d:' and not destination.exists() and destination.parent.is_dir(),
            'Choose a new report in an existing D: directory; existing evidence is preserved')
        report_admitted = True
        _require(type(allow_native_window) is bool and allow_native_window,
            'Saved-play smoke requires explicit --allow-native-window before Qt or native execution')
        inputs = _bundle_inputs(data)
        destination, work = _owned_paths(destination,work)
        _run_frozen(inputs,work,data)
        _require(data['native_windows_started']==3 and len(data['invocations'])==3
            and data.get('all_owned_processes_joined') is True,
            'Frozen saved-play baseline did not complete three native invocations and actual joins')
        data['status']='passed'
    except Exception as error:
        data['error']=str(error)
    finally:
        data['completed_at']=datetime.now(timezone.utc).isoformat()
        if report_admitted and destination is not None and not destination.exists() and destination.parent.is_dir():
            raw=(json.dumps(data,indent=2)+'\n').encode('utf-8')
            _require(len(raw)<=1024*1024,'Smoke report byte limit')
            with destination.open('xb')as stream:stream.write(raw)
    return 0 if data['status']=='passed'else 2


def saved_play_release_smoke_main(argv):
    parser=argparse.ArgumentParser(description='Explicit frozen saved-chapter baseline acceptance')
    parser.add_argument('--saved-play-release-smoke',required=True,type=Path,metavar='NEW_REPORT')
    parser.add_argument('--saved-play-work',required=True,type=Path,metavar='NEW_D_WORKDIR')
    parser.add_argument('--allow-native-window',action='store_true')
    args=parser.parse_args(argv)
    return run_saved_play_release_smoke(args.saved_play_release_smoke,args.saved_play_work,
        allow_native_window=args.allow_native_window)
