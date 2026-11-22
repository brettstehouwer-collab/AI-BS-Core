"""User-started combined opening review. Default inspection never launches."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import uuid

SESSIONS = Path('D:/AI-BS-Game-Resources/GameplayReviews')
ATTEMPTS = Path('D:/AI-BS-Game-Resources/ReviewLaunches')
ROOT = Path(__file__).resolve().parents[2]
EXPECTED_BUNDLE = ROOT / 'native_studio/releases/v5.329.107/AI_BS_Studio/_internal'
EXPECTED_SDK_PREFIX = Path('D:/AI-BS-Game-Resources/SDK/0.17.1/release')
SDK_VERSION = '0.17.1'
STUDIO_VERSION = '5.329.107'


def decode_json(payload):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate review metadata key: ' + key)
            result[key] = value
        return result
    def invalid_number(value):
        raise ValueError('Nonfinite review metadata number: ' + value)
    return json.loads(payload, object_pairs_hook=unique, parse_constant=invalid_number)


def read_json(path, limit=65536):
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Missing or oversized review metadata: ' + str(path))
    return decode_json(path.read_text(encoding='utf-8'))


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def resources(pins_path=None):
    # The review executes the installed preview's own player and closed assets.
    # SDK hashes additionally prove it matches the separately qualified runtime.
    spec = importlib.util.spec_from_file_location('gameplay_review_assets', ROOT / 'native_studio/game_engine/opening_assets.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    pins = read_json(pins_path or Path(__file__).with_name('gameplay_review_runtime_studio107.json'))
    root = Path(pins['prefix'])
    if root != EXPECTED_SDK_PREFIX or pins['sdk_version'] != SDK_VERSION or pins['studio_version'] != STUDIO_VERSION:
        raise ValueError('Unexpected review SDK identity')
    if Path(pins['studio_bundle']) != EXPECTED_BUNDLE:
        raise ValueError('Unexpected review Studio bundle')
    bundle = module.plain_path(EXPECTED_BUNDLE, directory=True)
    binary = module.plain_path(bundle / 'game_assets/player', boundary=bundle, directory=True)
    required = {'bin/aibs_motherboard.exe', 'bin/aibs_warm_opening_project.exe', 'bin/aibs_capabilities.json'} | {
        'bin/shaders/' + n for n in ['character.ps.cso', 'character.vs.cso', 'motherboard.ps.cso',
            'motherboard.vs.cso', 'shadow.vs.cso', 'textured.ps.cso', 'textured.vs.cso']}
    if set(pins['files']) != required:
        raise ValueError('Incomplete runtime pin set')
    for name, identity in pins['files'].items():
        path = root / name
        if '..' in Path(name).parts or Path(name).drive or Path(name).root or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
            raise ValueError('Review runtime path must not redirect')
        if type(identity.get('bytes')) is not int or identity['bytes'] <= 0 or not re.fullmatch('[0-9a-f]{64}', identity.get('sha256', '')):
            raise ValueError('Invalid runtime pin')
        if not path.is_file() or path.stat().st_size != identity['bytes'] or digest(path) != identity['sha256']:
            raise ValueError('Review runtime differs from qualified SDK: ' + name)
        installed = module.plain_path(binary / name.removeprefix('bin/'), boundary=binary, file=True)
        if installed.stat().st_size != identity['bytes'] or digest(installed) != identity['sha256']:
            raise ValueError('Installed review runtime differs from qualified SDK: ' + name)
    if read_json(binary / 'aibs_capabilities.json')['sdk_version'] != SDK_VERSION:
        raise ValueError('Review SDK metadata differs')
    assets = module.read_opening_assets(bundle / 'game_assets/opening', verify_pack_contents=True)
    if assets.manifest_sha256 != pins['opening_manifest_sha256']:
        raise ValueError('Installed opening assets differ from the qualified review')
    return binary / 'aibs_motherboard.exe', binary / 'aibs_warm_opening_project.exe', assets


def command(player, project, session, invocation, timeline):
    return [str(player), '--durable-world', '--content-definition', str(project / 'opening.aibd'),
        '--asset-root', str(project / 'assets/packs'), '--database', str(session / 'world.sqlite'),
        '--project', 'combined-opening-review', '--branch', 'user-gameplay-review',
        '--persistent-play', '--timeline-id', timeline, '--play-session', invocation,
        '--stop-file', str(session / ('stop.' + invocation + '.request')),
        '--width', '1920', '--height', '1080', '--performance-gameplay',
        '--performance-report', str(session / 'performance.json'),
        '--performance-seconds', '900', '--performance-warmup', '2', '--capture', str(session / 'after.bmp')]


def validate(report, exit_code, request, notices):
    def need(ok, why):
        if not ok:
            raise ValueError('No accepted gameplay measurement: ' + why)
    need(type(report.get('version')) is int and report['version'] == 1, 'unsupported report version')
    need(type(exit_code) is int and exit_code == 0 and report.get('status') == 'measured' and report.get('error') == '', 'native failure')
    need(report.get('measurement_profile') == 'gameplay' and report.get('gameplay_includes_reading_inspection_and_saving') is True, 'wrong profile')
    need(report.get('actual_client_width') == 1920 and report.get('actual_client_height') == 1080, 'wrong physical dimensions')
    for key in ['gpu_debug_layer_observed', 'synthetic_chapter_ticks_used_for_fps', 'engine_requested_inference', 'recording_enabled']:
        need(report.get(key) is False, 'invalid mode: ' + key)
    need(all(type(report.get(k)) is int and report[k] == 0 for k in ['gpu_debug_errors', 'gpu_debug_warnings']), 'GPU diagnostics')
    need(report.get('requested_measure_seconds') == 900 and report.get('warmup_min_seconds') == 2, 'requested window')
    count, wall = report.get('frame_count'), report.get('measured_wall_seconds')
    need(type(count) is int and count > 0 and type(report.get('actual_present_delta')) is int and report['actual_present_delta'] == count, 'Present accounting')
    need(type(wall) in (int, float) and math.isfinite(wall) and 15 <= wall <= 1050, 'elapsed duration')
    need(type(report.get('normal_player_close')) is bool and (report['normal_player_close'] or wall >= 900), 'premature timer completion')
    values = [report.get('fps'), *(report.get('frame_ms', {}).get(k) for k in ['mean', 'p50', 'p95', 'p99'])]
    need(all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in values), 'frame statistics')
    need(abs(values[0] - count / wall) < .01 and abs(values[1] - 1000 * wall / count) < .001, 'inconsistent statistics')
    need(values[2] <= values[3] <= values[4] <= wall * 1000, 'percentile ordering')
    need(report.get('content_fingerprint') == request['definition_sha256'] and report.get('scope') == {'world_id': request['world_id'], 'timeline_id': request['timeline_id']}, 'wrong content/session scope')
    need(report.get('visible_revision') == report.get('durable_revision') and type(report.get('durable_revision')) is int and report['durable_revision'] >= 0, 'unacknowledged outcomes')
    need([x.get('event') for x in notices] == ['aibs.saved_play.ready', 'aibs.saved_play.stopped'], 'missing ready/stopped lifecycle')
    for row in notices:
        need(type(row.get('schema_version')) is int and row['schema_version'] == 1 and row.get('play_session') == request['invocation'] and row.get('timeline_id') == request['timeline_id'] and row.get('world_id') == request['world_id'] and row.get('content_fingerprint') == request['definition_sha256'] and row.get('context') == 'player_world' and row.get('saved') is True and row.get('project_id') == 'combined-opening-review' and row.get('branch_id') == 'user-gameplay-review', 'lifecycle scope/save state')
    need(notices[-1].get('durable_revision') == report['durable_revision'], 'stopped revision differs')
    for group in ['private_bytes', 'working_set_bytes', 'scene_content_gpu_bytes']:
        data = report.get(group, {})
        need(all(type(data.get(k)) is int and data[k] >= 0 for k in ['start', 'end', 'maximum_sampled']), 'memory accounting')
        need(data['maximum_sampled'] >= max(data['start'], data['end']), 'memory maximum')
    need(type(report.get('instrumentation_owned_bytes')) is int and 0 < report['instrumentation_owned_bytes'] <= 8 * 1024**2, 'instrumentation budget')
    for name in ['measured_reading_frames', 'measured_inspection_frames', 'measured_saving_frames']:
        need(type(report.get(name)) is int and 0 <= report[name] <= count, 'UI/save accounting')
    long = report.get('long_frames', {})
    need(all(type(long.get(k)) is int for k in ['over16_67ms', 'over33_33ms', 'over50ms']), 'long-frame accounting')
    need(0 <= long['over50ms'] <= long['over33_33ms'] <= long['over16_67ms'] <= count, 'long-frame bounds')
    outcome = report.get('opening_outcomes', {})
    need(outcome.get('first_route') in {'none', 'repair', 'bypass', 'alternative'} and all(type(outcome.get(k)) is bool for k in ['shelter_secured', 'pencil_visited']), 'outcome schema')
    need((not outcome['pencil_visited'] or outcome['shelter_secured']) and outcome['shelter_secured'] == (outcome['first_route'] != 'none'), 'outcome coherence')
    return {'status': 'valid_gameplay_render_sample', 'fps': report['fps'], 'frame_ms': report['frame_ms'],
        'long_frames': long, 'opening_outcomes': outcome, 'human_pacing_accepted': False,
        'private_bytes': report['private_bytes'], 'scene_content_gpu_bytes': report['scene_content_gpu_bytes'],
        'memory_scope': 'Sampled maxima; scene GPU excludes swapchain/depth/descriptors/driver heaps.',
        'scope': 'Actual rendered play including reading/inspection/saves; human active time, clarity and final opening acceptance still require review.'}


def run_interactive(attempt, state):
    def stage(name, **extra):
        state.update(stage=name, **extra)
        write(attempt / 'launch.json', state)
    if not sys.stdin.isatty():
        raise ValueError('Run this yourself in an interactive console; no unattended launch')
    stage('validating_resources')
    player, factory, assets = resources()
    if shutil.disk_usage('D:/').free < 2 * 1024**3:
        raise ValueError('Keep at least2GiB free on D:')
    print('This uses Studio107 / SDK0.17.1 and current Adam assets in a separate review world; existing saves stay untouched.')
    print('Play normally: repair OR build the bypass, then reach shelter and the Pencil Room.')
    print('Keep the game or its reading panel active. Reading and saving are included; switching apps invalidates the sample.')
    print('Close normally when finished. This check has a15minute maximum, not a target to wait for.')
    print('Results need at least15seconds of measured play. Do not rush or wait to match8–12minutes.')
    stage('waiting_for_enter')
    input('Press Enter to open the game, or Ctrl+C to cancel: ')
    SESSIONS.mkdir(parents=True, exist_ok=True)
    session = SESSIONS / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + str(uuid.uuid4()))
    session.mkdir()
    stage('creating_project', session=str(session))
    project = session / 'chapter'
    create = [str(factory), '--output', str(project), '--workshop']
    for role in assets.roles:
        create += ['--' + role.role + '-pack', str(role.directory)]
    with (session / 'factory.stdout.log').open('xb') as out, (session / 'factory.stderr.log').open('xb') as err:
        result = subprocess.run(create, stdin=subprocess.DEVNULL, stdout=out, stderr=err, shell=False, timeout=60)
    if result.returncode:
        raise RuntimeError('Opening factory failed; see retained session logs')
    manifest = read_json(project / 'opening-manifest.json')
    if manifest.get('opening_workshop') is not True or manifest.get('recording_bound') is not False or manifest['fingerprint'] != digest(project / 'opening.aibd'):
        raise ValueError('New review chapter differs from the intended isolated workshop')
    invocation, timeline = str(uuid.uuid4()), str(uuid.uuid4())
    request = {'created_at': datetime.now(timezone.utc).isoformat(), 'invocation': invocation, 'timeline_id': timeline,
        'world_id': manifest['world_id'], 'definition_sha256': manifest['fingerprint'], 'player_sha256': digest(player),
        'studio_version': STUDIO_VERSION, 'sdk_version': SDK_VERSION, 'player': str(player),
        'asset_manifest_sha256': assets.manifest_sha256, 'existing_user_save_used': False, 'focus_forced': False,
        'automated_input': False, 'inference_requested': False}
    write(session / 'request.json', request)
    write(session / 'feedback.json', {'review_status': 'unreviewed', 'first_time': None, 'route': None,
        'active_minutes_excluding_breaks': None, 'stalls_or_mistakes': None, 'guidance_clear': None, 'repair_or_build_satisfying': None,
        'note': 'Rendered duration includes reading/inspection/saving. No human pacing or qualitative acceptance inferred.'})
    argv = command(player, project, session, invocation, timeline)
    write(session / 'invocation.json', argv)
    stage('running')
    interrupted = False
    started = time.monotonic()
    with (session / 'game.stdout.log').open('xb') as out, (session / 'game.stderr.log').open('xb') as err:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err, shell=False)
        try:
            process.wait(timeout=1050)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            interrupted = True
        finally:
            if process.poll() is None:
                try:
                    (session / ('stop.' + invocation + '.request')).write_text('stop\n', encoding='ascii')
                except OSError:
                    pass
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            write(session / 'process.json', {'pid': process.pid, 'exit_code': process.poll(), 'joined': process.poll() is not None,
                'interrupted_or_timed_out': interrupted, 'launch_to_exit_seconds': time.monotonic() - started,
                'timing_scope': 'Includes startup, setup, close and capture; not active gameplay time'})
    if interrupted:
        raise RuntimeError('Review cancelled/timed out; save and evidence retained, no acceptance')
    resources()  # Reject runtime or art changes during the run.
    if (session / 'game.stdout.log').stat().st_size > 65536:
        raise ValueError('Oversized native lifecycle log')
    lines = (session / 'game.stdout.log').read_text(encoding='utf-8').splitlines()
    summary = validate(read_json(session / 'performance.json'), process.returncode, request, [decode_json(x) for x in lines if x.strip()])
    write(session / 'result.json', summary)
    stage('measured_requires_human_review', result=str(session / 'result.json'))
    print(json.dumps({**summary, 'session': str(session)}, indent=2))
    print('Tell Codex your route, active minutes and any stalls or unclear guidance.')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    if not args.run:
        player, _, assets = resources()
        print(json.dumps({'status': 'ready_not_run', 'studio': STUDIO_VERSION, 'sdk': SDK_VERSION, 'player': str(player),
            'asset_roles': [x.role for x in assets.roles], 'asset_manifest_sha256': assets.manifest_sha256,
            'window_started': False}))
        return 0
    ATTEMPTS.mkdir(parents=True, exist_ok=True)
    attempt = ATTEMPTS / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + str(uuid.uuid4()))
    attempt.mkdir()
    state = {'at': datetime.now(timezone.utc).isoformat(), 'stage': 'starting', 'python': sys.executable}
    write(attempt / 'launch.json', state)
    print('Launch diagnostics: ' + str(attempt), flush=True)
    try:
        return run_interactive(attempt, state)
    except (KeyboardInterrupt, EOFError):
        state.update(status='cancelled', stopped_at_stage=state['stage'])
        write(attempt / 'launch.json', state)
        print('Cancelled before measurement acceptance. Diagnostics retained.', file=sys.stderr)
        return 130
    except Exception as error:
        state.update(status='failed', stopped_at_stage=state['stage'], error=str(error))
        write(attempt / 'launch.json', state)
        (attempt / 'failure.log').write_text(traceback.format_exc(), encoding='utf-8')
        print(str(error) + '\nSee ' + str(attempt), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
