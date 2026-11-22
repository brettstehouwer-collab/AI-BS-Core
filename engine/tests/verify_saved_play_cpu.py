"""Actual CPU native admission and independent kernel-lock process contracts.

The native fixture calls the player's real parser/admission/lock functions but
never constructs a window/renderer. Lifecycle samples test serialization only;
actual first-frame/close receipts remain a separate GPU integration obligation.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid


def verify_readonly(fixture, output):
    fixture, output = Path(fixture).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output/('readonly-recovery-'+str(uuid.uuid4()))
    work.mkdir()
    p = subprocess.Popen([str(fixture), str(work/'native')], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        stdout, stderr = p.communicate(timeout=45)
    finally:
        if p.poll() is None:
            p.kill()
            p.communicate(timeout=10)
    (work/'stdout.log').write_bytes(stdout)
    (work/'stderr.log').write_bytes(stderr)
    passed = p.returncode == 0 and b'All read-only recovery checks passed' in stdout
    result = {'status': 'passed' if passed else 'failed', 'exit_code': p.returncode,
              'fixture': str(fixture), 'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'native_pass_labels': sum(line.startswith(b'PASS ') for line in stdout.splitlines()),
              'processes_joined': p.poll() is not None, 'work_directory': str(work),
              'completed_at': datetime.now(timezone.utc).isoformat()}
    (work/'verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))
    return 0 if passed else 1


def verify(fixture, output):
    fixture, output = Path(fixture).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output/('saved-play-cpu-'+str(uuid.uuid4()))
    work.mkdir()
    result = {'schema_version': 1, 'status': 'failed', 'checks': [],
              'work_directory': str(work), 'fixture': str(fixture),
              'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'windows_or_gpu_created': False, 'family_sources_used': False,
              'actual_player_first_frame_verified': False, 'processes_joined': False}
    processes = []

    def check(value, why):
        if not value:
            raise AssertionError(why)
        result['checks'].append(why)

    def child(arguments, label, expected=0):
        p = subprocess.Popen([str(fixture), *map(str, arguments)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        processes.append(p)
        try:
            stdout, stderr = p.communicate(timeout=30)
        finally:
            if p.poll() is None:
                p.kill()
                p.communicate(timeout=10)
        (work/(label+'.stdout.log')).write_bytes(stdout)
        (work/(label+'.stderr.log')).write_bytes(stderr)
        check(p.returncode == expected,
              label+': exit '+str(p.returncode)+', expected '+str(expected)+': '+stderr.decode(errors='replace'))
        return stdout, stderr

    def hold(database, label):
        ready, release = work/(label+'.ready'), work/(label+'.release')
        stdout = (work/(label+'.stdout.log')).open('xb')
        stderr = (work/(label+'.stderr.log')).open('xb')
        try:
            p = subprocess.Popen([str(fixture), '--hold-lock', str(database), str(ready), str(release)],
                                 stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        finally:
            stdout.close()
            stderr.close()
        processes.append(p)
        deadline = time.monotonic()+10
        while not ready.exists():
            if p.poll() is not None or time.monotonic() >= deadline:
                raise AssertionError('Actual lock owner did not become ready')
            time.sleep(.01)
        return p, release

    try:
        stdout, _ = child([work/'native'], 'native-admission')
        check(b'no window or GPU created' in stdout, 'Actual native CPU admission fixture completed')
        events = [json.loads(line) for line in (work/'native/lifecycle.jsonl').read_text().splitlines()]
        exact_keys = {'schema_version', 'event', 'play_session', 'project_id', 'branch_id',
                      'world_id', 'timeline_id', 'context', 'content_fingerprint', 'saved',
                      'durable_revision', 'durable_sequence'}
        check(len(events) == 2 and [e['event'] for e in events] ==
              ['aibs.saved_play.ready', 'aibs.saved_play.stopped'], 'Distinct ordered saved lifecycle serialization')
        for event in events:
            check(set(event) == exact_keys, 'Saved lifecycle has exactly the accepted closed key set')
            check(type(event['schema_version']) is int and event['schema_version'] == 1 and
                  event['context'] == 'player_world' and type(event['saved']) is bool and event['saved'],
                  'Saved lifecycle types and actual context are explicit')
            for field in ('durable_revision', 'durable_sequence'):
                check(type(event[field]) is int and 0 <= event[field] < 2**64,
                      'Saved lifecycle '+field+' is bounded unsigned64')
            for field in ('play_session', 'world_id', 'timeline_id'):
                check(str(uuid.UUID(event[field])) == event[field] and uuid.UUID(event[field]).version == 4,
                      'Saved lifecycle '+field+' is canonical UUID4')
        check(all(events[0][key] == events[1][key] for key in exact_keys-{'event'}),
              'Lifecycle samples retain exact scope, content and durable heads')
        check(events[0]['timeline_id'] != events[0]['play_session'],
              'Ephemeral invocation and stable player timeline are distinct')
        slot = work/'lock-slot'
        slot.mkdir()
        database = slot/'world.sqlite'
        first, release = hold(database, 'hold-graceful')
        _, error = child(['--try-lock', database], 'duplicate-owner', expected=1)
        check(b'already owned' in error and first.poll() is None,
              'Independent native process cannot steal a live slot lock')
        check(not database.exists(), 'Lock-only processes never initialize a gameplay database')
        release.write_bytes(b'release owned test lock\n')
        first.wait(timeout=10)
        check(first.returncode == 0, 'Graceful native lock owner exits and joins')
        child(['--try-lock', database], 'acquire-after-graceful')
        second, _ = hold(database, 'hold-crash')
        second.kill()
        second.wait(timeout=10)
        check(second.returncode != 0, 'Deliberately terminated lock owner is joined')
        child(['--try-lock', database], 'acquire-after-crash')
        check((slot/'player.lock').is_file() and not database.exists(),
              'Kernel crash release works without deleting the retained lock file or reseeding')
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = str(error)
    finally:
        for p in processes:
            if p.poll() is None:
                p.kill()
                p.wait(timeout=10)
        result['processes_joined'] = all(p.poll() is not None for p in processes)
        result['child_process_count'] = len(processes)
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        report = work/'verification.json'
        report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'report': str(report),
                      'checks': len(result['checks']),
                      **({'error': result['error']} if 'error' in result else {})}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--readonly':
        raise SystemExit(verify_readonly(*sys.argv[2:]))
    if len(sys.argv) != 3:
        raise SystemExit('Usage: verify_saved_play_cpu.py [--readonly] NATIVE_FIXTURE OUTPUT_ROOT')
    raise SystemExit(verify(*sys.argv[1:]))
