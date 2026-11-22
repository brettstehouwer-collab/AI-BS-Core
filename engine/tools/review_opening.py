"""Manual opening review in a new, retained test world; inspection never launches."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

SPEC = importlib.util.spec_from_file_location('opening_review_resources',
    Path(__file__).with_name('measure_opening.py'))
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)
SESSIONS = Path('D:/AI-BS-Game-Resources/OpeningReviews')


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def play_command(player, project, session, invocation, timeline):
    return [str(player), '--durable-world', '--content-definition', str(project / 'opening.aibd'),
        '--asset-root', str(project / 'assets/packs'), '--database', str(session / 'world.sqlite'),
        '--project', 'manual-opening-review', '--branch', 'first-time-review',
        '--persistent-play', '--timeline-id', timeline, '--play-session', invocation,
        '--stop-file', str(session / ('stop.' + invocation + '.request')),
        '--width', '1920', '--height', '1080']


def run_interactive():
    if not sys.stdin.isatty():
        raise ValueError('Start the manual review in an interactive console')
    player, factory, assets = baseline.resources()
    if shutil.disk_usage('D:/').free < 2 * 1024**3:
        raise ValueError('Keep at least2GiB free on D:')
    print('A fresh review world will be retained on D:. Your existing saves stay untouched.')
    print('Play normally: explore the nook, repair OR build the bypass, then reach shelter and the Pencil Room.')
    print('Use the on-screen controls and Adam guidance. Close the game normally when finished.')
    print('This records console-session elapsed time, NOT FPS or verified active gameplay time.')
    input('Press Enter to start, or Ctrl+C to cancel: ')
    SESSIONS.mkdir(parents=True, exist_ok=True)
    session = SESSIONS / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + str(uuid.uuid4()))
    session.mkdir()
    project = session / 'chapter'
    request = {'at': datetime.now(timezone.utc).isoformat(), 'player': str(player),
        'player_sha256': baseline.digest(player), 'factory_sha256': baseline.digest(factory),
        'asset_manifest_sha256': assets.manifest_sha256, 'existing_user_save_used': False,
        'focus_forced': False, 'automated_input': False, 'performance_measured': False}
    write(session / 'request.json', request)
    write(session / 'feedback.json', {'review_status': 'unreviewed', 'first_time': None,
        'route': None, 'reached_shelter': None, 'reached_pencil_room': None,
        'self_reported_active_minutes': None, 'time_lost_or_stalled': None,
        'interaction_mistakes': None, 'adam_guidance_clear': None,
        'repair_or_build_satisfying': None, 'changes_requested': None,
        'note': 'No acceptance inferred from elapsed time. Complete after normal play.'})
    command = [str(factory), '--output', str(project), '--workshop']
    for role in assets.roles:
        command += ['--' + role.role + '-pack', str(role.directory)]
    with (session / 'factory.stdout.log').open('xb') as out, (session / 'factory.stderr.log').open('xb') as err:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
            shell=False, timeout=60)
    if result.returncode:
        raise RuntimeError('Factory failed; retained evidence: ' + str(session))
    invocation, timeline = str(uuid.uuid4()), str(uuid.uuid4())
    command = play_command(player, project, session, invocation, timeline)
    write(session / 'invocation.json', {'command': command, 'timeline_id': timeline})
    started = time.monotonic()
    interrupted = False
    player_unchanged = False
    with (session / 'game.stdout.log').open('xb') as out, (session / 'game.stderr.log').open('xb') as err:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, shell=False)
        try:
            process.wait(timeout=45 * 60)
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
            player_unchanged = baseline.digest(player) == request['player_sha256']
            write(session / 'process.json', {'pid': process.pid, 'exit_code': process.poll(),
                'joined': process.poll() is not None, 'interrupted_or_timed_out': interrupted,
                'process_elapsed_seconds': time.monotonic() - started,
                'timing_scope': 'Launch to child exit, including startup, menus and any waiting; not active gameplay or FPS',
                'player_unchanged': player_unchanged,
                'completed_at': datetime.now(timezone.utc).isoformat()})
    print('Review files and fresh test save retained at: ' + str(session))
    print('Please report your route, approximate active minutes, stalls and how Adam guidance felt.')
    if interrupted or process.returncode != 0 or not player_unchanged:
        raise RuntimeError('Review interrupted or native process failed; no acceptance recorded')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    if args.run:
        return run_interactive()
    player, _, assets = baseline.resources()
    print(json.dumps({'status': 'ready_not_run', 'player': str(player),
        'verified_asset_roles': [a.role for a in assets.roles], 'window_started': False,
        'performance_measured': False}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyboardInterrupt, EOFError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
