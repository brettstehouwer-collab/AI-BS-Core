"""User-started stationary First Boot benchmark; never launches on inspection."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUNDLE = ROOT / 'native_studio/releases/v5.329.103/AI_BS_Studio/_internal'
EXPECTED_PLAYER_SHA256 = 'ff9a56e0524d3e36138cb3af150cde41ff8cfdb71494c690c926ca26a0c5fe06'
SESSIONS = Path('D:/AI-BS-Game-Resources/PerformanceSessions')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def resources(bundle=DEFAULT_BUNDLE):
    # Reuse the closed, stdlib-only curated-pack validator without importing UI.
    spec = importlib.util.spec_from_file_location('aibs_measure_assets',
        ROOT / 'native_studio/game_engine/opening_assets.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    bundle = module.plain_path(bundle, directory=True)
    binary = module.plain_path(bundle / 'game_assets/player', boundary=bundle, directory=True)
    player = module.plain_path(binary / 'aibs_motherboard.exe', boundary=bundle, file=True)
    factory = module.plain_path(binary / 'aibs_warm_opening_project.exe', boundary=bundle, file=True)
    if digest(player) != EXPECTED_PLAYER_SHA256:
        raise ValueError('Player differs from the verified Studio103 baseline; preserve the file for review')
    capabilities = module.bounded_json(module._read(binary / 'aibs_capabilities.json', 16384))
    if capabilities.get('sdk_version') != '0.16.4':
        raise ValueError('This measured baseline requires the reviewed SDK0.16.4 player')
    assets = module.read_opening_assets(bundle / 'game_assets/opening', verify_pack_contents=True)
    return player, factory, assets


def measured_summary(report, exit_code):
    if exit_code != 0:
        raise ValueError('No valid measurement: native process failed')
    return validate_report(report)


def validate_report(report):
    import math
    if report.get('measurement_profile', 'stationary') != 'stationary':
        raise ValueError('Gameplay samples cannot be labelled as stationary baselines')
    if report.get('status') != 'measured':
        raise ValueError('No valid measurement: ' + str(report.get('error', 'native process failed')))
    values = [report.get('fps'), *(report.get('frame_ms', {}).get(k) for k in ('mean', 'p50', 'p95', 'p99'))]
    if any(type(v) not in (float, int) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Incomplete or invalid native frame statistics')
    if report.get('actual_client_width') != 1920 or report.get('actual_client_height') != 1080:
        raise ValueError('Measurement was not the requested physical1080p client')
    if report.get('gpu_debug_layer_observed') is not False:
        raise ValueError('Development validation was active; baseline policy differs')
    count = report.get('frame_count')
    wall = report.get('measured_wall_seconds')
    if (type(count) is not int or count <= 0 or report.get('actual_present_delta') != count
            or type(wall) not in (float, int) or not math.isfinite(wall) or wall < 15
            or abs(report['fps'] - count / wall) > .01):
        raise ValueError('Incomplete or inconsistent actual Present/time accounting')
    if any(report.get(key) is not False for key in ('synthetic_chapter_ticks_used_for_fps',
            'engine_requested_inference', 'recording_enabled')):
        raise ValueError('Measurement mode differs from the declared baseline')
    return {'fps': report['fps'], 'frame_ms': report['frame_ms'],
        'scope': 'Stationary nook only; not whole-opening performance or human pacing'}


def run_interactive(bundle=DEFAULT_BUNDLE):
    if not sys.stdin.isatty():
        raise ValueError('Start this check yourself in an interactive console; no unattended timed launch')
    player, factory, assets = resources(bundle)
    if shutil.disk_usage('D:/').free < 2 * 1024**3:
        raise ValueError('Keep at least2GiB free on D: for retained measurement evidence')
    print('This opens a separate First Boot test world; your saved game is untouched.')
    print('Click the game window, stand still, and keep it active until it closes.')
    print('It needs2seconds warmup and15seconds measurement. No focus is forced.')
    input('Press Enter when you are ready to start, or Ctrl+C to cancel: ')
    SESSIONS.mkdir(parents=True, exist_ok=True)
    session = SESSIONS / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + str(uuid.uuid4()))
    session.mkdir()
    project = session / 'chapter'
    command = [str(factory), '--output', str(project), '--workshop']
    for role in assets.roles:
        command += ['--' + role.role + '-pack', str(role.directory)]
    request = {'at': datetime.now(timezone.utc).isoformat(), 'player': str(player),
        'player_sha256': digest(player), 'factory_sha256': digest(factory),
        'asset_manifest_sha256': assets.manifest_sha256, 'scope': 'Stationary new nook baseline',
        'existing_user_save_used': False, 'focus_forced': False}
    (session / 'request.json').write_text(json.dumps(request, indent=2) + '\n', encoding='utf-8')
    with (session / 'factory.stdout.log').open('xb') as out, (session / 'factory.stderr.log').open('xb') as err:
        created = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
            shell=False, timeout=60)
    if created.returncode:
        raise RuntimeError('Opening creation failed; evidence retained at ' + str(session))
    invocation = str(uuid.uuid4())
    stop = session / ('stop.' + invocation + '.request')
    command = [str(player), '--durable-world', '--content-definition', str(project / 'opening.aibd'),
        '--asset-root', str(project / 'assets/packs'), '--database', str(session / 'world.sqlite'),
        '--project', 'user-started-performance', '--branch', 'stationary-nook',
        '--play-session', invocation, '--stop-file', str(stop), '--width', '1920', '--height', '1080',
        '--capture', str(session / 'after.bmp'), '--performance-report', str(session / 'performance.json'),
        '--performance-seconds', '15', '--performance-warmup', '2']
    with (session / 'game.stdout.log').open('xb') as out, (session / 'game.stderr.log').open('xb') as err:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, shell=False)
        try:
            code = process.wait(timeout=85)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            raise RuntimeError('Check interrupted; retained child joined, evidence at ' + str(session))
        finally:
            if process.poll() is None:
                try:
                    stop.write_text('stop\n', encoding='ascii')
                except OSError:
                    pass  # Still join/stop this retained child if storage failed.
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            (session / 'process.json').write_text(json.dumps({'pid': process.pid,
                'exit_code': process.poll(), 'joined': process.poll() is not None,
                'completed_at': datetime.now(timezone.utc).isoformat()}) + '\n', encoding='utf-8')
    report_path = session / 'performance.json'
    if not report_path.is_file() or report_path.stat().st_size > 65536:
        raise RuntimeError('Native measurement report missing/oversized; evidence at ' + str(session))
    summary = measured_summary(json.loads(report_path.read_text(encoding='utf-8')), code)
    if digest(player) != request['player_sha256']:
        raise RuntimeError('Player changed during measurement; result not accepted')
    print(json.dumps({**summary, 'evidence': str(session)}, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Require an interactive readiness confirmation')
    args = parser.parse_args(argv)
    if args.run:
        return run_interactive()
    player, _, assets = resources()
    print(json.dumps({'status': 'ready_not_run', 'player': str(player), 'sdk': '0.16.4',
        'verified_asset_roles': [a.role for a in assets.roles], 'timed_window_started': False}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyboardInterrupt, EOFError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
