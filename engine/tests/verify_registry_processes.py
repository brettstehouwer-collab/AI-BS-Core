"""Terminate real migration processes around COMMIT and verify preserved M2 data."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


def require(value, message):
    if not value:
        raise AssertionError(message)


def preserved(data):
    return {key: data[key] for key in (
        'scope', 'revision', 'sequence', 'original_checkpoint_id', 'original_revision',
        'original_events', 'original_receipt_preserved', 'original_undo_redo_preserved',
        'baseline_revision', 'baseline_sequence', 'legacy_hex', 'old_receipt_hex',
        'old_retry_status', 'baseline_components', 'components', 'batches')}


def verify(executable, output, old_native=None):
    executable, output = executable.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'registry-process-proof' / str(uuid.uuid4())
    work.mkdir(parents=True)
    (work / 'SYNTHETIC_FIXTURE.txt').write_text(
        'Synthetic authoring history, UUIDs and checkpoints generated solely for this process proof.\n',
        encoding='utf-8')
    checks = []
    metrics = {name: False for name in (
        'before_commit_recovery', 'after_commit_recovery', 'atomic_registry_receipts',
        'preserved_m2_evidence', 'exact_migration_retry', 'conflicting_migration_rejected',
        'stale_registry_connection', 'old_studio92_rejected')}
    report = {'schema_version': 1, 'status': 'failed', 'checks': checks,
              'metrics': metrics, 'work_directory': str(work)}
    ids = {name: str(uuid.uuid4()) for name in ('timeline', 'entity', 'event')}
    source, database = work / 'original.aibs', work / 'world.sqlite'
    stale = None
    processes = 0

    def publish():
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        temporary = output / 'registry_migration_verification.tmp'
        temporary.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, output / 'registry_migration_verification.json')

    def command(step):
        arguments = [str(executable), '--step', step, '--database', str(database),
                     '--source', str(source), '--report', str(work / f'{step}.json')]
        for key, value in ids.items():
            arguments += ['--' + key, value]
        return arguments

    def run(step, expected=0):
        nonlocal processes
        processes += 1
        child = subprocess.run(command(step), capture_output=True, text=True, timeout=25)
        (work / f'{step}.stdout.log').write_text(child.stdout, encoding='utf-8')
        (work / f'{step}.stderr.log').write_text(child.stderr, encoding='utf-8')
        require(child.returncode == expected,
                f'{step}: exit {child.returncode}, expected {expected}: {child.stdout} {child.stderr}')
        if expected:
            return None
        data = json.loads((work / f'{step}.json').read_text(encoding='utf-8'))
        require(data['status'] == 'passed' and data['old_retry_status'] == 'retry',
                f'{step}: probe did not verify complete current state and original exact receipt')
        return data

    try:
        publish()
        require(executable.is_file(), f'Registry probe executable not found: {executable}')
        seed = run('seed')
        ids['world'] = seed['scope']['world_id']
        raw = source.read_bytes()
        require(raw[:8] == b'AIBSSAVE' and int.from_bytes(raw[8:12], 'little') == 1 and
                bytes.fromhex(seed['old_receipt_hex'])[:8] == b'AIBGBAT1' and
                seed['registry_hex'] == seed['expected_old_registry_hex'] and
                seed['format'] == 1 and seed['revision'] == 3 and seed['sequence'] == 1 and
                seed['baseline_revision'] == 2 and seed['baseline_sequence'] == 0 and
                seed['original_events'] == 2 and len(seed['batches']) == 1 and
                seed['legacy_hex'] == raw.hex() and seed['old_receipt_hex'] == seed['batches'][0],
                'Seed is not a genuine imported v1 authoring baseline plus one exact v1 gameplay receipt')
        require(seed['original_receipt_preserved'] and seed['original_undo_redo_preserved'],
                'Original format1 receipt/undo/redo evidence is missing')
        checks.append('Genuine format1 create/set history imports as exact original evidence with a separate v1 gameplay batch')

        run('before', 73)
        before = run('inspect')
        require(before['format'] == 1 and before['registry_hex'] == seed['registry_hex'] and
                preserved(before) == preserved(seed) and source.read_bytes() == raw,
                'Pre-COMMIT process termination published partial format, registry or gameplay changes')
        metrics['before_commit_recovery'] = True
        checks.append('Process exit before migration COMMIT preserves format1, old registry and complete original/gameplay evidence')

        processes += 1
        stale = subprocess.Popen(command('stale'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ready = work / 'stale.json.ready'
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            require(stale.poll() is None, 'Stale connection exited before opening its original registry')
            time.sleep(0.01)
        require(ready.exists(), 'Stale connection did not signal readiness')
        run('after', 74)
        (work / 'stale.json.go').write_text('resume after registry COMMIT', encoding='utf-8')
        stdout, stderr = stale.communicate(timeout=15)
        (work / 'stale.stdout.log').write_text(stdout, encoding='utf-8')
        (work / 'stale.stderr.log').write_text(stderr, encoding='utf-8')
        require(stale.returncode == 0, f'Stale old-registry connection did not reject safely: {stdout} {stderr}')
        stale_result = json.loads((work / 'stale.json').read_text(encoding='utf-8'))
        require(stale_result['migration_status'] == 'stale_rejected' and
                preserved(stale_result) == preserved(seed), 'Stale connection changed committed gameplay after registry extension')
        metrics['stale_registry_connection'] = True
        checks.append('A real connection opened before migration rejects new gameplay after the registry changes')

        after = run('inspect')
        require(after['format'] == 2 and after['registry_hex'] == after['expected_target_registry_hex'] and
                after['registry_hex'] != seed['registry_hex'] and
                preserved(after) == preserved(seed) and source.read_bytes() == raw,
                'Post-COMMIT process termination lost registry atomicity or changed M2 evidence/heads')
        metrics.update(after_commit_recovery=True, preserved_m2_evidence=True)
        checks.append('Process exit after migration COMMIT exposes format2/new registry with identical scope, heads, components, original raw, events and old receipts')
        retry = run('retry')
        require(retry['migration_status'] == 'retry' and retry['format'] == 2 and
                retry['registry_hex'] == after['registry_hex'] and preserved(retry) == preserved(seed),
                'Exact migration retry lost its committed receipt or changed any gameplay state')
        conflict = run('conflict')
        require(conflict['migration_status'] == 'rejected' and conflict['registry_hex'] == after['registry_hex'] and
                preserved(conflict) == preserved(seed) and source.read_bytes() == raw,
                'Conflicting migration ID changed the registry or original evidence')
        metrics.update(exact_migration_retry=True, conflicting_migration_rejected=True,
                       atomic_registry_receipts=True)
        checks.append('Exact migration retry remains idempotent and conflicting ID/target rejects without a gameplay event or revision')

        if old_native is not None and old_native.is_file():
            processes += 1
            old_report = work / 'studio92-rejected.json'
            child = subprocess.run([str(old_native.resolve()), '--durable-world', '--world-db', str(database),
                                    '--durable-step', 'inspect', '--capture', str(work / 'studio92.bmp'),
                                    '--durable-report', str(old_report)],
                                   capture_output=True, text=True, timeout=25)
            diagnostic = child.stdout + child.stderr
            if old_report.is_file():
                diagnostic += old_report.read_text(encoding='utf-8')
            (work / 'studio92.stdout.log').write_text(child.stdout, encoding='utf-8')
            (work / 'studio92.stderr.log').write_text(child.stderr, encoding='utf-8')
            require(child.returncode != 0 and 'unsupported gameplay database format' in diagnostic.lower(),
                    'Retained Studio92 did not reject format2 specifically at its format guard')
            final = run('inspect')
            require(final['format'] == 2 and final['registry_hex'] == after['registry_hex'] and
                    preserved(final) == preserved(seed) and source.read_bytes() == raw,
                    'Rejected retained Studio92 changed the evolved database or original evidence')
            metrics['old_studio92_rejected'] = True
            checks.append('Actual retained Studio92 native executable rejects format2 as unsupported before scope/game loading')
        else:
            checks.append('Retained Studio92 compatibility check not run: optional executable is unavailable')
        report.update(status='passed', scope=seed['scope'], revision=seed['revision'],
                      original_checkpoint_id=seed['original_checkpoint_id'])
    except Exception as error:
        report['error'] = str(error)
        checks.append('FAILED: ' + str(error))
    finally:
        if stale is not None and stale.poll() is None:
            stale.kill()
            stale.communicate(timeout=10)
        metrics['processes'] = processes
        publish()
    print(json.dumps(report))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        raise SystemExit('Usage: verify_registry_processes.py PROBE_EXECUTABLE OUTPUT_DIRECTORY [STUDIO92_NATIVE_EXECUTABLE]')
    previous = Path(sys.argv[3]) if len(sys.argv) == 4 else Path(
        'C:/AI-BS/native_studio/releases/v5.329.92/AI_BS_Studio/_internal/game_assets/player/aibs_motherboard.exe')
    raise SystemExit(verify(Path(sys.argv[1]), Path(sys.argv[2]), previous))
