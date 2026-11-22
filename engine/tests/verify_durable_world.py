"""Separate native DX12 processes prove the durable typed gameplay path."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def canonical_uuid(value):
    require(isinstance(value, str), 'Persistent UUID must be a string')
    parsed = uuid.UUID(value)
    require(parsed.version == 4 and str(parsed) == value, f'Noncanonical UUID: {value}')


def integer(value, name):
    require(type(value) is int and 0 <= value <= 2**64 - 1,
            f'{name} must be an unsigned integer')


def validate_report(data, pending=False):
    require(data.get('status') == 'passed', f'Native report did not pass: {data}')
    scope = data['scope']
    require(set(('project_id', 'world_id', 'branch_id', 'timeline_id', 'context')) <= set(scope),
            'Native report omitted complete gameplay scope')
    for key in ('project_id', 'branch_id'):
        require(isinstance(scope[key], str) and scope[key], f'Invalid scope {key}')
    for key in ('world_id', 'timeline_id'):
        canonical_uuid(scope[key])
    require(scope['context'] in (2, 'player_world'), 'Native gameplay used a different context')
    for key in ('visible_revision', 'durable_revision', 'durable_sequence', 'pending_batches'):
        integer(data[key], key)
    require(type(data['saved']) is bool, 'Saved must be an explicit boolean')
    if pending:
        require(not data['saved'] and data['pending_batches'] > 0 and
                data['visible_revision'] > data['durable_revision'],
                'Interruption must occur after visible publication and before its saved acknowledgement')
    else:
        require(data['saved'] and data['pending_batches'] == 0 and
                data['visible_revision'] == data['durable_revision'],
                'Successful ordinary native step ended with unsaved work')
    require(type(data['core_capacity']) in (int, float) and 0 <= data['core_capacity'] <= 100,
            'Invalid native core capacity')
    identities = data['entity_ids']
    require(isinstance(identities, dict) and identities, 'Native report omitted alias identities')
    require(all(isinstance(alias, str) and alias for alias in identities), 'Invalid entity alias')
    for value in identities.values():
        canonical_uuid(value)
    require(len(set(identities.values())) == len(identities), 'Aliases silently reused a persistent UUID')
    alive, tombstones = data['alive_ids'], data['tombstones']
    require(isinstance(alive, list) and isinstance(tombstones, list), 'Missing liveness/tombstone lists')
    for value in alive + tombstones:
        canonical_uuid(value)
    require(len(set(alive)) == len(alive) and len(set(tombstones)) == len(tombstones),
            'Liveness/tombstone list contains duplicate UUIDs')
    require(set(alive).isdisjoint(tombstones) and
            set(alive) | set(tombstones) == set(identities.values()),
            'Alias identities disagree with alive and retired identities')
    events = data['events']
    require(isinstance(events, list), 'Native report omitted semantic event history')
    seen = set()
    previous = None
    for event in events:
        canonical_uuid(event['event_id'])
        canonical_uuid(event['subject_id'])
        integer(event['sequence'], 'event sequence')
        require(event['event_id'] not in seen, 'Semantic event UUID was duplicated')
        require(event['sequence'] > 0 and (previous is None or event['sequence'] == previous + 1),
                'Semantic history is not strictly contiguous')
        require(isinstance(event['operation_id'], str) and event['operation_id'],
                'Semantic event omitted operation identity')
        require(event['type'] in ('repair.outcome', 'construction.outcome', 'route.outcome', 'hazard.outcome'),
                'Unknown semantic outcome type')
        require(event['subject_id'] in identities.values(), 'Semantic subject lost its persistent identity')
        seen.add(event['event_id'])
        previous = event['sequence']
    if events and not pending:
        require(events[-1]['sequence'] == data['durable_sequence'], 'Durable sequence differs from its last event')
    metrics = data['metrics']
    require(type(metrics['debug_layer']) is bool, 'Missing explicit DX12 debug-layer state')
    require(type(metrics['debug_errors']) is int and metrics['debug_errors'] == 0,
            'Native DX12 validation reported errors')
    require(type(metrics['nonbackground_pixels']) is int and metrics['nonbackground_pixels'] > 10000,
            'Native GPU capture was blank or incomplete')


def state_identity(data):
    return {key: data[key] for key in (
        'scope', 'visible_revision', 'durable_revision', 'durable_sequence', 'saved',
        'pending_batches', 'core_capacity', 'entity_ids', 'alive_ids', 'tombstones', 'events')}


def same_restart(before, before_pixels, after, after_pixels, label):
    require(state_identity(after) == state_identity(before),
            f'{label}: restart changed scope, heads, components, UUIDs or exact semantic events')
    require(after_pixels == before_pixels, f'{label}: restart changed actual GPU pixels')


def transition(before, after, event_type, subject):
    require(after['scope'] == before['scope'], 'Action changed its persistent world/timeline scope')
    require(after['durable_revision'] == before['durable_revision'] + 1 and
            after['durable_sequence'] == before['durable_sequence'] + 1,
            'One action did not advance exactly one committed revision and semantic sequence')
    require(len(after['events']) == len(before['events']) + 1 and
            after['events'][:-1] == before['events'],
            'Action changed prior semantic evidence or appended more than once')
    event = after['events'][-1]
    require(event['type'] == event_type and event['subject_id'] == subject,
            'Committed semantic outcome does not identify the actual action target')
    for alias, identity in before['entity_ids'].items():
        require(after['entity_ids'].get(alias) == identity, 'Action changed an existing persistent alias identity')


def verify(executable, output):
    executable, output = executable.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'durable-world-proof' / str(uuid.uuid4())
    work.mkdir(parents=True)
    checks = []
    coverage = {key: False for key in (
        'native_gpu', 'repair_build_dismantle', 'restart_pixels_identical', 'durable_reload', 'stable_uuids',
        'semantic_event_equality', 'tombstone_persistence', 'before_commit_recovery',
        'after_commit_recovery', 'exact_retry', 'live_retry', 'close_drained',
        'import_preserves_original')}
    result = {'schema_version': 1, 'status': 'failed', 'checks': checks,
              'metrics': coverage, 'work_directory': str(work)}
    processes = 0
    gpu_reports = []

    def publish():
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        temporary = output / 'durable_world_verification.tmp'
        temporary.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, output / 'durable_world_verification.json')

    def child(arguments, label, expected=0):
        nonlocal processes
        processes += 1
        try:
            completed = subprocess.run([str(executable), *arguments], capture_output=True,
                                       text=True, timeout=45)
        except subprocess.TimeoutExpired as error:
            # subprocess.run kills and waits for this owned child on timeout.
            raise RuntimeError(f'{label}: owned native process exceeded 45 seconds') from error
        (work / f'{label}.stdout.log').write_text(completed.stdout, encoding='utf-8')
        (work / f'{label}.stderr.log').write_text(completed.stderr, encoding='utf-8')
        require(completed.returncode == expected,
                f'{label}: exit {completed.returncode}, expected {expected}: '
                f'{completed.stdout} {completed.stderr}')

    def run(step, label, database, expected=0, request=None, original=None):
        report, capture = work / f'{label}.json', work / f'{label}.bmp'
        arguments = ['--durable-world', '--world-db', str(database), '--durable-step', step,
                     '--capture', str(capture), '--durable-report', str(report)]
        if request is not None:
            arguments += ['--request-file', str(request)]
        if original is not None:
            arguments += ['--import-checkpoint', str(original)]
        child(arguments, label, expected)
        data = json.loads(report.read_text(encoding='utf-8'))
        validate_report(data, pending=expected in (73, 74))
        pixels = capture.read_bytes()
        require(len(pixels) > 54 and pixels[:2] == b'BM', f'{label}: capture is not an actual BMP')
        gpu_reports.append(data['metrics'])
        return data, pixels

    try:
        publish()
        require(executable.is_file(), f'Native executable not found: {executable}')
        database = work / 'normal.sqlite'
        seeded, dark = run('seed', 'seed', database)
        require(seeded['core_capacity'] == 0, 'Fresh core was already repaired')
        core = seeded['entity_ids']['core-01']
        repaired, lit = run('repair', 'repair', database)
        transition(seeded, repaired, 'repair.outcome', core)
        require(repaired['core_capacity'] == 100 and lit != dark, 'Repair did not change typed state and GPU pixels')
        restarted, pixels = run('reload', 'repair-restart', database)
        same_restart(repaired, lit, restarted, pixels, 'repair')
        require(restarted['metrics'].get('reload') is True, 'Native restart did not exercise the real F9 durable reload path')
        coverage['durable_reload'] = True
        checks.append('Repair through native input changes real GPU pixels; restart and actual F9 reload preserve identical UUIDs and semantic evidence')

        built, constructed = run('build', 'build', database)
        added = set(built['alive_ids']) - set(repaired['alive_ids'])
        require(len(added) == 1, 'Build did not introduce exactly one persistent relay UUID')
        relay = added.pop()
        transition(repaired, built, 'construction.outcome', relay)
        require(len(built['entity_ids']) == len(repaired['entity_ids']) + 1 and constructed != lit,
                'Relay construction did not change aliases and actual GPU geometry')
        restarted, pixels = run('inspect', 'build-restart', database)
        same_restart(built, constructed, restarted, pixels, 'build')

        removed, dismantled = run('dismantle', 'dismantle', database)
        transition(built, removed, 'construction.outcome', relay)
        require(relay not in removed['alive_ids'] and relay in removed['tombstones'] and
                set(removed['alive_ids']) == set(repaired['alive_ids']) and dismantled != constructed,
                'Dismantle did not retire the constructed UUID and remove its GPU geometry')
        restarted, pixels = run('inspect', 'dismantle-restart', database)
        same_restart(removed, dismantled, restarted, pixels, 'dismantle')
        coverage.update(native_gpu=True, repair_build_dismantle=True, restart_pixels_identical=True,
                        stable_uuids=True, semantic_event_equality=True, tombstone_persistence=True)
        checks.append('Native build/dismantle persists exact construction events, aliases and tombstones across separate GPU processes')

        crash_db = work / 'interrupted.sqlite'
        old, old_pixels = run('seed', 'crash-seed', crash_db)
        before_request = work / 'before-request.batch'
        pending, pending_pixels = run('before-commit', 'before-commit', crash_db, 73, before_request)
        require(pending['scope'] == old['scope'] and pending['visible_revision'] == old['durable_revision'] + 1 and
                pending['durable_revision'] == old['durable_revision'] and pending['core_capacity'] == 100 and
                pending_pixels != old_pixels, 'Pre-COMMIT exit did not retain an actually visible unsaved repair')
        require(before_request.is_file() and before_request.stat().st_size > 0, 'Pre-COMMIT exit omitted its canonical retry request')
        before, pixels = run('inspect', 'before-restart', crash_db)
        same_restart(old, old_pixels, before, pixels, 'pre-COMMIT interruption')
        coverage['before_commit_recovery'] = True
        checks.append('Process exit before COMMIT leaves the previous complete world, events and GPU pixels while preserving evidence of unsaved visibility')

        after_request = work / 'after-request.batch'
        pending, pending_pixels = run('after-commit', 'after-commit', crash_db, 74, after_request)
        require(pending['scope'] == old['scope'] and pending['visible_revision'] == old['durable_revision'] + 1 and
                pending['durable_revision'] == old['durable_revision'] and pending['core_capacity'] == 100,
                'Post-COMMIT exit fabricated a saved acknowledgement before completion delivery')
        request_bytes = after_request.read_bytes()
        require(request_bytes, 'Post-COMMIT exit omitted its exact retry request')
        after, pixels = run('inspect', 'after-restart', crash_db)
        transition(old, after, 'repair.outcome', old['entity_ids']['core-01'])
        require(after['core_capacity'] == 100 and pixels == pending_pixels and pixels != old_pixels,
                'Post-COMMIT restart did not recover the visibly repaired GPU world')
        retried, retry_pixels = run('retry', 'lost-completion-retry', crash_db, request=after_request)
        same_restart(after, pixels, retried, retry_pixels, 'lost-completion exact retry')
        require(after_request.read_bytes() == request_bytes, 'Exact retry rewrote the preserved canonical request')
        coverage.update(after_commit_recovery=True, exact_retry=True)
        checks.append('Process exit after COMMIT recovers exactly one event; resubmitting its preserved request adds no state, history or pixel change')

        for step, metric in (('fail-retry', 'live_retry'), ('close-drain', 'close_drained')):
            special_db = work / f'{step}.sqlite'
            base, base_pixels = run('seed', f'{step}-seed', special_db)
            completed, pixels = run(step, step, special_db)
            transition(base, completed, 'repair.outcome', base['entity_ids']['core-01'])
            require(completed['metrics'].get(metric) is True and completed['core_capacity'] == 100 and pixels != base_pixels,
                    f'{step}: native process did not prove its controlled failure/close path')
            restarted, restarted_pixels = run('inspect', f'{step}-restart', special_db)
            same_restart(completed, pixels, restarted, restarted_pixels, step)
            coverage[metric] = True
        checks.append('An actual failed native save stays visible and retries live once; WM_CLOSE drains gated pending work before joining')

        original = work / 'original.aibs'
        legacy = None
        legacy_pixels = None
        for step in ('seed', 'edit'):
            label = f'original-{step}'
            report, capture = work / f'{label}.json', work / f'{label}.bmp'
            child(['--world-step', step, '--checkpoint', str(original), '--capture', str(capture),
                   '--world-report', str(report)], label)
            legacy = json.loads(report.read_text(encoding='utf-8'))
            require(legacy['status'] == 'passed', 'Original format-1 native setup failed')
            legacy_pixels = capture.read_bytes()
        original_bytes = original.read_bytes()
        imported_db = work / 'imported.sqlite'
        imported, imported_pixels = run('seed', 'imported-original', imported_db, original=original)
        require(original.read_bytes() == original_bytes and imported['scope']['world_id'] == legacy['world_id'] and
                imported['entity_ids'] == legacy['entity_ids'] and imported['durable_revision'] == legacy['revision'],
                'Import changed original bytes, world/head identity or entity UUIDs')
        require(imported['imported_original_events'] == legacy['memory_events'] and
                isinstance(imported['original_evidence'], str) and imported['original_evidence'],
                'Import omitted its separate original authoring evidence')
        require(imported_pixels == legacy_pixels, 'Typed imported world changed original GPU geometry')
        restarted, pixels = run('inspect', 'imported-restart', imported_db)
        same_restart(imported, imported_pixels, restarted, pixels, 'original format-1 import')
        require(original.read_bytes() == original_bytes, 'Imported restart modified the original checkpoint')
        coverage['import_preserves_original'] = True
        checks.append('Original format-1 checkpoint imports without rewriting its bytes, entity UUIDs, revision, source event count or native GPU pixels')

        result.update(status='passed', scope=removed['scope'], revision=removed['durable_revision'],
                      durable_events=len(removed['events']))
    except Exception as error:
        result['error'] = str(error)
        checks.append('FAILED: ' + str(error))
    finally:
        coverage.update(processes=processes, debug_layer=bool(gpu_reports) and
                        all(item['debug_layer'] for item in gpu_reports),
                        debug_errors=sum(item['debug_errors'] for item in gpu_reports))
        publish()
    print(json.dumps(result))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: verify_durable_world.py NATIVE_EXECUTABLE OUTPUT_DIRECTORY')
    raise SystemExit(verify(Path(sys.argv[1]), Path(sys.argv[2])))
