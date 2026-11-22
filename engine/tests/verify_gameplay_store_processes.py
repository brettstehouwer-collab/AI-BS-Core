"""Actual process termination around SQLite COMMIT, plus stale concurrent writer."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid


def main():
    executable = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'sqlite-process-proof' / str(uuid.uuid4())
    work.mkdir(parents=True)
    ids = {key: str(uuid.uuid4()) for key in ('world', 'timeline', 'entity', 'seed-event', 'repair-event')}
    report = {'schema_version': 1, 'status': 'failed', 'checks': [], 'metrics': {}}
    stale = None
    try:
        def command(step):
            args = [str(executable), '--step', step, '--database', str(work / 'world.db'),
                    '--report', str(work / f'{step}.json')]
            for key, value in ids.items():
                args.extend(['--' + key, value])
            return args

        def run(step, expected=0):
            child = subprocess.run(command(step), capture_output=True, text=True, timeout=20)
            if child.returncode != expected:
                raise RuntimeError(f'{step}: exit {child.returncode}, expected {expected}: {child.stdout} {child.stderr}')
            return json.loads((work / f'{step}.json').read_text()) if expected == 0 else None

        seed = run('seed')
        if seed['revision'] != 1 or seed['capacity'] != 0 or len(seed['events']) != 1:
            raise RuntimeError('Initial durable seed differs from actual recovery')
        run('before', 73)
        before = run('inspect')
        if before['revision'] != 1 or before['capacity'] != 0 or before['events'] != seed['events']:
            raise RuntimeError('Uncommitted component/event changes survived interruption')
        report['checks'].append('Process exit before COMMIT retains the previous complete components and events')
        stale = subprocess.Popen(command('stale'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ready = work / 'stale.json.ready'
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            if stale.poll() is not None:
                raise RuntimeError('Stale writer exited before capturing its old head')
            time.sleep(0.01)
        if not ready.exists():
            raise RuntimeError('Stale writer did not report ready')
        run('after', 74)
        (work / 'stale.json.go').write_text('continue')
        stdout, stderr = stale.communicate(timeout=15)
        if stale.returncode:
            raise RuntimeError(f'Stale writer failed: {stdout} {stderr}')
        stale_result = json.loads((work / 'stale.json').read_text())
        if stale_result['commit_status'] != 'rejected' or stale_result['revision'] != 2:
            raise RuntimeError('An already-open stale connection overwrote the new committed head')
        report['checks'].append('Concurrent stale writer rejects after another process commits')
        after = run('inspect')
        if after['revision'] != 2 or after['capacity'] != 100 or after['events'] != [ids['seed-event'], ids['repair-event']]:
            raise RuntimeError('Post-COMMIT process exit lost or duplicated its atomic repair')
        report['checks'].append('Process exit after COMMIT preserves components, semantic events and operation receipt')
        retry = run('retry')
        if retry['commit_status'] != 'retry' or retry['events'] != after['events'] or retry['revision'] != 2:
            raise RuntimeError('Lost completion retry duplicated a committed operation')
        report['checks'].append('Exact retry after lost completion is idempotent')
        rejected = run('conflict')
        if rejected['commit_status'] != 'rejected' or rejected['revision'] != 2 or rejected['capacity'] != 100:
            raise RuntimeError('Conflicting operation retry mutated durable state')
        report['checks'].append('Conflicting retry rejects without partial component/event publication')
        foreign = run('foreign')
        if foreign['revision'] != 0 or foreign['events'] or foreign['components'] != 0:
            raise RuntimeError('A separate branch read the original world history')
        final = run('inspect')
        if final != after:
            raise RuntimeError('Rejected or foreign operations changed the original world')
        report['checks'].append('Project/world/branch/timeline scope isolates recovered history')
        report.update(status='passed', world_id=ids['world'], revision=2,
                      metrics={'process_recovery': True, 'atomic_components_events': True,
                               'exact_retry': True, 'stale_writer': True, 'scope_isolation': True,
                               'schema_version': 1, 'durable_events': 2})
    except Exception as exc:
        report.update(error=str(exc), checks=[str(exc)])
    finally:
        if stale is not None and stale.poll() is None:
            stale.kill()
            stale.communicate(timeout=10)
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    (output / 'gameplay_store_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
