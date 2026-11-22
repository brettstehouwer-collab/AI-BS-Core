"""Create-only Nsight capture/replay of the pinned current LH native proof.

Instrumentation and replay timings are diagnostics, never ordinary gameplay
performance. No original saves, desktop input, model calls or force termination.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import subprocess
import time
import uuid

import psutil

from qualify_rtx_creator import (ROOT, VARIANTS, copy_tree, load, long, need, pin,
    plain, read, tree, write, write_json)
from qualify_rtx_current_player import CREATOR, validate_bitmap
from qualify_rtx_hud_fit import validate_candidate

PREFLIGHT = ROOT/'backups/nsight_preflight_20261111_v01'
TOOLS = Path('C:/Program Files/NVIDIA Corporation/Nsight Graphics 2026.4.0/host/windows-desktop-nomad-x64')
EXPECTED = {
    'ngfx-capture.exe': 'a41b2dce12be9078f4983f1c333116e224c5fd81704b0b3d51a40f317eb29f07',
    'ngfx-replay.exe': 'f72332c03745418600a923b6572e84b50290df8828cddf69f2b5c3efbc976d39',
}


def verify_tools():
    pins, signatures = load(PREFLIGHT/'pins.json'), load(PREFLIGHT/'signatures.json')
    need(set(pins) == set(EXPECTED) and len(signatures) == 2, 'Unexpected reviewed Nsight tool set')
    verified = {}
    for name, expected in EXPECTED.items():
        path = TOOLS/name
        need(Path(pins[name]['path']) == path and pins[name]['sha256'] == expected,
             'Reviewed Nsight identity differs')
        need(pin(path)['sha256'] == expected, 'Installed Nsight executable changed')
        signature = [row for row in signatures if row['name'] == name]
        need(len(signature) == 1 and signature[0]['status'] == 'Valid' and
             signature[0]['publisher'].startswith('CN=NVIDIA Corporation,'),
             'Reviewed NVIDIA signature admission failed')
        verified[name] = {'path': str(path), **pin(path),
                          'signature_from_retained_parent_preflight': signature[0]}
    preflight = {name: pin(PREFLIGHT/name) for name in ('pins.json', 'signatures.json',
        'ngfx-capture.exe.help.log', 'ngfx-capture.exe.version.log',
        'ngfx-replay.exe.help.log', 'ngfx-replay.exe.version.log')}
    return {'tools': verified, 'preflight': preflight}


def environment(output, player):
    profile, temporary = output/'profile', output/'temp'
    for path in (profile, temporary, profile/'AppData', profile/'AppData/Roaming', profile/'AppData/Local'):
        long(path).mkdir()
    system = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    return {'SystemRoot': str(system), 'WINDIR': str(system),
        'COMSPEC': str(system/'System32/cmd.exe'),
        'PATH': ';'.join(map(str, (TOOLS, player.parent, system/'System32'))),
        'TEMP': str(temporary), 'TMP': str(temporary), 'USERPROFILE': str(profile),
        'APPDATA': str(profile/'AppData/Roaming'), 'LOCALAPPDATA': str(profile/'AppData/Local')}


class NativeHandle:
    def __init__(self, process, expected):
        import _winapi
        need(Path(process.exe()).resolve() == expected.resolve(), 'Unexpected descendant executable')
        self.pid, self.birth = process.pid, process.create_time()
        self.path = str(expected)
        self.handle = _winapi.OpenProcess(0x100000 | 0x1000, False, self.pid)
        need(process.create_time() == self.birth, 'Descendant process identity changed')

    def observe(self):
        import _winapi
        terminal = _winapi.WaitForSingleObject(self.handle, 0) == 0
        return {'pid': self.pid, 'birth': self.birth, 'executable': self.path,
                'exact_handle_retained': True, 'terminal': terminal,
                'exit_code': _winapi.GetExitCodeProcess(self.handle) if terminal else None}

    def close(self):
        import _winapi
        need(self.observe()['terminal'], 'Never close the diagnostic handle of a live descendant')
        _winapi.CloseHandle(self.handle)


def run_owned(command, cwd, env, output, label, *, player=None, seconds=180):
    handles, observations = {}, []
    with long(output/(label+'.stdout.log')).open('xb') as stdout, long(output/(label+'.stderr.log')).open('xb') as stderr:
        child = subprocess.Popen(list(map(str, command)), cwd=cwd, env=env,
            stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        identity = {'pid': child.pid, 'birth': psutil.Process(child.pid).create_time(),
            'command': list(map(str, command)), 'working_directory': str(cwd),
            'exact_popen_handle_retained': True}
        write_json(output/(label+'.started.json'), identity)
        started, overdue = time.monotonic(), False
        while True:
            if player is not None and child.poll() is None:
                try:
                    for descendant in psutil.Process(child.pid).children(recursive=True):
                        try:
                            if descendant.pid not in handles and Path(descendant.exe()).resolve() == player.resolve():
                                handle = NativeHandle(descendant, player)
                                handles[descendant.pid] = handle
                                write_json(output/(label+'.player-'+str(descendant.pid)+'.started.json'), handle.observe())
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            current = [handle.observe() for handle in handles.values()]
            if child.poll() is not None and all(row['terminal'] for row in current):
                observations = current
                break
            if not overdue and time.monotonic()-started > seconds:
                overdue = True
                write_json(output/(label+'.retained.json'), {**identity,
                    'status': 'TIMEOUT_RETAINED_NO_KILL_NO_RESTART', 'descendants': current,
                    'instruction': 'Harness retains exact handles and waits only for these owners; no later GPU stage will run.'})
                print(label+': timeout; owners/handles retained, no restart', flush=True)
            time.sleep(.025 if not overdue else .25)
        result = {**identity, 'terminal': True, 'exit_code': child.returncode,
            'deadline_exceeded': overdue, 'wall_seconds': time.monotonic()-started,
            'player_processes': observations}
        write_json(output/(label+'.process.json'), result)
        for handle in handles.values():
            handle.close()
        need(not overdue, label+' exceeded bounded observation; retained failure must be reviewed')
        need(child.returncode == 0, label+' failed; retained stdout/stderr')
        if player is not None:
            need(len(observations) == 1 and observations[0]['exit_code'] == 0,
                 'Exactly one actual player with observed normal exit0 is required')
        return result


def artifact(path, maximum=2 * 1024**3):
    plain(path)
    size = long(path).stat().st_size
    need(0 < size <= maximum, 'Nsight artifact exceeds bounded size or is empty')
    digest = hashlib.sha256()
    with long(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    need(long(path).stat().st_size == size, 'Nsight artifact changed while hashing')
    return {'bytes': size, 'sha256': digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--diagnostic-candidate', action='store_true',
                        help='Use only the separately pinned diagnostic logging build')
    parser.add_argument('--disable-capture-pipeline-cache', action='store_true',
                        help='Disable only Nsight internal pipeline caches for this capture; retain debug layer/guard')
    args = parser.parse_args()
    output = args.output.absolute()
    need(output.parent == VARIANTS and output.name.startswith('Nsight_LH_') and
         not long(output).exists(), 'Use a new Nsight_LH direct reviewed RTX child')
    plain(output)
    candidate_validator = validate_candidate
    if args.diagnostic_candidate:
        from prepare_rtx_nsight_diagnostic import validate_candidate as validate_diagnostic
        candidate_validator = validate_diagnostic
    player, candidate = candidate_validator()
    reviewed = verify_tools()
    source = CREATOR/'project'
    before = tree(source)
    need(pin(source/'opening.aibd') == load(CREATOR/'author.json')['opening'], 'Final creator export differs')
    long(output).mkdir()
    record = {'status': 'INCOMPLETE', 'utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Nsight-instrumented controlled hidden seed and single-frame replay diagnostics',
        'ordinary_gameplay_performance_measured': False, 'human_input_verified': False,
        'diagnostic_logging_candidate': args.diagnostic_candidate,
        'capture_internal_pipeline_cache_disabled': args.disable_capture_pipeline_cache,
        'player': str(player), 'candidate': candidate, 'tools': reviewed,
        'original_source_before': before, 'processes': []}
    try:
        long(output/'reviewed-preflight').mkdir()
        for name in reviewed['preflight']:
            write(output/'reviewed-preflight'/name, read(PREFLIGHT/name))
        copy_tree(source, output/'project')
        for name in ('capture', 'replay-temp', 'replay-performance'):
            long(output/name).mkdir()
        env = environment(output, player)
        write_json(output/'preflight.json', record)
        session = str(uuid.uuid4())
        game_args = ['--durable-world', '--content-definition', str(output/'project/opening.aibd'),
            '--asset-root', str(output/'project/assets/packs'), '--database', str(output/'world.sqlite'),
            '--project', 'prop01-native-acceptance', '--branch', 'independent-prop01-v1',
            '--play-session', session, '--stop-file', str(output/'seed.stop.request'),
            '--durable-step', 'seed', '--capture', str(output/'seed.bmp'),
            '--durable-report', str(output/'seed.json'), '--width', '1440', '--height', '900']
        capture = output/'capture/lh-frame.ngfx-bincap'
        if args.diagnostic_candidate:
            # Qualify the logging-only build without injection first. Every
            # database/output is new; never reuse the subsequent capture DB.
            baseline = output/'baseline-direct'
            long(baseline).mkdir()
            baseline_args = list(game_args)
            for flag, value in (('--database', baseline/'world.sqlite'),
                                ('--stop-file', baseline/'stop.request'),
                                ('--capture', baseline/'frame.bmp'),
                                ('--durable-report', baseline/'report.json')):
                baseline_args[baseline_args.index(flag)+1] = str(value)
            record['processes'].append(run_owned([str(player), *baseline_args], player.parent,
                                                 env, output, 'baseline-direct'))
            direct = load(baseline/'report.json')
            need(direct['status'] == 'passed' and direct['saved'] and direct['pending_batches'] == 0
                 and direct['metrics']['debug_layer'] and direct['metrics']['debug_errors'] == 0
                 and direct['metrics']['debug_warnings'] == 0, 'Uninstrumented diagnostic baseline failed')
            record['direct_baseline_passed'] = True
        command = [str(TOOLS/'ngfx-capture.exe'), '--exe', str(player), '--working-dir', str(player.parent),
            '--args', subprocess.list2cmdline(game_args), '--output-dir', str(output/'capture'),
            '--output-file', capture.name, '--capture-frame', '10', '--frame-count', '1',
            '--no-hud', '--no-bundle-replayer']
        if args.disable_capture_pipeline_cache:
            command.append('--no-internal-pipeline-caches')
        record['processes'].append(run_owned(command, player.parent, env, output, 'capture', player=player))
        native = load(output/'seed.json')
        need(native['schema_version'] == 1 and native['status'] == 'passed' and native['saved'] is True
             and native['pending_batches'] == 0 and native['visible_revision'] == native['durable_revision'], 'Native durable proof failed')
        need(native['scope'] == {'project_id': 'prop01-native-acceptance',
            'branch_id': 'independent-prop01-v1', 'world_id': '7c66f912-2990-4ebf-aeba-25365efe8481',
            'timeline_id': session, 'context': 'temporary_play'}, 'Native scope differs')
        need(native['content']['revision'] == 6 and native['content']['fingerprint'] == pin(output/'project/opening.aibd')['sha256'], 'Native content differs')
        metrics = native['metrics']
        need(metrics['debug_layer'] and metrics['debug_errors'] == metrics['debug_warnings'] == 0
             and metrics['nonbackground_pixels'] > 10000 and metrics['hud_readback'] and metrics['hud_fits']
             and metrics['hud_capture'] and metrics['hud_needed_height'] <= metrics['hud_height'], 'Native GPU/HUD acceptance failed')
        need(not native['os_focus_input_verified'] and not native['human_pacing_measured'], 'Controlled proof mislabeled')
        record['native'] = native
        record['native_captures'] = {name: validate_bitmap(output/name) for name in
            ('seed.bmp', 'seed.bmp.pov.bmp', 'seed.bmp.hud.bmp')}
        need(record['native_captures']['seed.bmp']['width'] == 1440 and
             record['native_captures']['seed.bmp']['height'] == 900, 'Wrong physical native viewport')
        record['capture'] = artifact(capture)
        replay = [str(TOOLS/'ngfx-replay.exe'), '--loop-count', '1', '--max-worker-threads', '4',
            '--temp-resource-dir', str(output/'replay-temp'), '--perf-report-dir', str(output/'replay-performance'),
            '--no-crash-reporting', str(capture)]
        record['processes'].append(run_owned(replay, TOOLS, env, output, 'replay'))
        need(artifact(capture) == record['capture'], 'Capture changed during replay')
        rows = {}
        for here, directories, files in os.walk(long(output/'replay-performance'), followlinks=False):
            for name in directories:
                plain(Path(here)/name)
            for name in files:
                path = Path(here)/name
                need(len(rows) < 128, 'Replay result member bound exceeded')
                rows[path.relative_to(long(output/'replay-performance')).as_posix()] = artifact(path, 64*1024**2)
        need(rows, 'Replay did not produce raw performance-report artifacts')
        record['replay_raw_reports'] = rows
        need(tree(output/'project') == before and tree(source) == before, 'Immutable copied/original input changed')
        need(candidate_validator()[1] == candidate and verify_tools() == reviewed, 'Candidate/tools changed')
        record['status'] = 'PASS_NSIGHT_CAPTURE_AND_SINGLE_REPLAY_DIAGNOSTIC'
    except BaseException as error:
        record.update(status='FAILED_OR_RETAINED', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        record['original_source_unchanged'] = tree(source) == before
        write_json(output/'qualification.json', record)
        print(record['status'], flush=True)


if __name__ == '__main__':
    main()
