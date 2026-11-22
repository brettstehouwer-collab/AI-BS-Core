"""Actual native processes, controller edges, DX12 readback and chapter recovery."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def identity(value):
    require(isinstance(value, str) and str(uuid.UUID(value)) == value and
            uuid.UUID(value).version == 4, f'Invalid persistent UUID: {value}')


def records(report):
    return {item['entity_id']: item for item in report['components']}


def chapter_record(report, alias):
    return records(report)[report['chapter_ids'][alias]]['fields']


def state(report):
    return {key: report[key] for key in ('scope', 'visible_revision', 'durable_revision',
            'durable_sequence', 'saved', 'pending_batches', 'chapter_ids', 'components', 'events')}


def database_rows(path):
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as database:
        tables = [row[0] for row in database.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {'format': database.execute('PRAGMA user_version').fetchone()[0],
                **{table: sorted(database.execute(f'SELECT * FROM {table}').fetchall())
                   for table in tables}}


def validate(report, capture):
    require(report.get('status') == 'passed' and report.get('schema_version') == 1,
            'Native chapter report did not pass')
    require(report['saved'] is True and report['pending_batches'] == 0 and
            report['visible_revision'] == report['durable_revision'],
            'Native chapter ended before actual durable acknowledgement')
    scope = report['scope']
    require(scope['project_id'] == 'first-boot-world' and scope['branch_id'] == 'main' and
            scope['context'] == 'player_world', 'Wrong complete chapter scope')
    identity(scope['world_id'])
    identity(scope['timeline_id'])
    for value in report['chapter_ids'].values():
        identity(value)
    items = records(report)
    require(len(items) == len(report['components']) and len(items) >= 62,
            'Chapter component projection lost or duplicated identities')
    for value in items:
        identity(value)
    require(set(report['chapter_ids'].values()) <= set(items), 'Missing chapter entities')
    seen = set()
    previous = None
    for event in report['events']:
        identity(event['event_id'])
        identity(event['subject_id'])
        require(event['event_id'] not in seen and event['subject_id'] in items,
                'Repeated event or lost semantic subject')
        require(event['operation_id'] and event['source'] and
                event['type'] in ('repair.outcome', 'construction.outcome', 'route.outcome',
                                  'hazard.outcome', 'mechanism.outcome', 'quest.outcome'),
                'Chapter semantic evidence omitted typed identity/provenance')
        require(event['revision'] <= report['durable_revision'] and
                (previous is None or event['sequence'] == previous + 1),
                'Recall exposed unacknowledged or noncontiguous events')
        previous = event['sequence']
        seen.add(event['event_id'])
    require(previous == report['durable_sequence'], 'Acknowledged sequence differs from history')
    metrics = report['metrics']
    require(metrics['debug_errors'] == 0 and metrics['nonbackground_pixels'] > 10000,
            'Actual DX12 scene validation/readback failed')
    require(metrics['hud_readback'] is True and metrics['hud_fits'] is True and
            metrics['hud_capture'] is True and metrics['hud_needed_height'] <= metrics['hud_height'],
            'Actual native HUD is missing, clipped or uncaptured')
    for path in (capture, Path(str(capture) + '.pov.bmp'), Path(str(capture) + '.hud.bmp')):
        raw = path.read_bytes()
        require(len(raw) > 54 and raw[:2] == b'BM', f'Missing actual GPU/control BMP: {path}')


def verify(executable, output):
    executable, output = executable.resolve(), output.resolve()
    work = output / 'first-boot-chapter-proof' / str(uuid.uuid4())
    work.mkdir(parents=True)
    coverage = {key: False for key in (
        'native_gpu', 'actual_player_pov', 'actual_hud_fits', 'repair_route', 'bypass_route',
        'occupied_door_close', 'optional_help', 'optional_decline', 'depart_return',
        'feed_build_dismantle', 'latched_unpowered_return', 'restart_pixels_identity',
        'actual_f9_reload', 'hazard_pause', 'hazard_recovery', 'critical_backpressure',
        'recovery_consumes_old_input', 'stale_activation_rejected', 'empty_socket_survives',
        'remote_node_reach', 'translated_board_supported', 'reload_failure_retains_live',
        'live_f5_held_contact', 'close_drains_held_contact',
        'explicit_m2_upgrade', 'm2_history_preserved', 'original_import_preserved')}
    checks, gpu = [], []
    result = {'schema_version': 1, 'status': 'failed', 'executablePath': str(executable),
              'work_directory': str(work), 'checks': checks, 'metrics': coverage}
    processes = 0

    def publish():
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        temporary = output / 'first_boot_chapter_verification.tmp'
        temporary.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, output / 'first_boot_chapter_verification.json')

    def completed_child(completed, label, expected):
        (work / f'{label}.stdout.log').write_text(completed.stdout, encoding='utf-8')
        (work / f'{label}.stderr.log').write_text(completed.stderr, encoding='utf-8')
        require(completed.returncode == expected,
                f'{label}: exit {completed.returncode}, expected {expected}: {completed.stderr}')

    def child(arguments, label, expected=0):
        nonlocal processes
        processes += 1
        completed = subprocess.run([str(executable), *arguments], capture_output=True,
                                   text=True, timeout=90)
        completed_child(completed, label, expected)
        return completed

    def arguments(step, label, database, chapter=True, extras=()):
        report, capture = work / f'{label}.json', work / f'{label}.bmp'
        args = ['--durable-world', '--world-db', str(database), '--durable-step', step,
                '--capture', str(capture), '--durable-report', str(report)]
        if chapter:
            args.append('--chapter')
        return [*args, *extras], report, capture

    def read_report(report, capture):
        data = json.loads(report.read_text(encoding='utf-8'))
        validate(data, capture)
        gpu.append(data['metrics'])
        return data, capture.read_bytes()

    def run(step, label, database, extras=()):
        args, report, capture = arguments(step, label, database, extras=extras)
        child(args, label)
        return read_report(report, capture)

    def preserved(before, after):
        require(before['scope'] == after['scope'], 'Action replaced its complete gameplay scope')
        for key in before['chapter_ids']:
            require(before['chapter_ids'][key] == after['chapter_ids'][key], 'Chapter UUID changed')
        require(set(records(before)) <= set(records(after)), 'Existing entity UUID vanished')
        require(after['events'][:len(before['events'])] == before['events'],
                'Action rewrote previous typed events/receipts')

    def restart(before, pixels, database, label, step='inspect'):
        after, actual = run(step, label, database)
        require(state(before) == state(after) and actual == pixels,
                f'{label}: restart changed exact components, UUIDs, heads, events or GPU pixels')
        if step == 'reload':
            require(after['metrics']['reload'] is True, 'F9 path was not actually exercised')
        return after, actual

    try:
        publish()
        require(executable.is_file(), f'Native executable not found: {executable}')
        result['executableSha256'] = hashlib.sha256(executable.read_bytes()).hexdigest()
        repair_db = work / 'repair.sqlite'
        seeded, dark = run('seed', 'repair-seed', repair_db)
        initial = chapter_record(seeded, 'progress')
        require(initial['first_route'] == 'none' and not initial['shelter_secured'] and
                not initial['pencil_visited'], 'Initial availability fabricated physical visits')
        repaired, lit = run('repair-route', 'repair-route', repair_db)
        preserved(seeded, repaired)
        progress = chapter_record(repaired, 'progress')
        require(repaired['metrics']['repair_route'] is True and
                repaired['metrics']['walking_ticks'] > 500 and progress['first_route'] == 'repair' and
                progress['shelter_secured'] and progress['pencil_visited'] and lit != dark,
                'Continuous repair route did not change real geometry/progress')
        restart(repaired, lit, repair_db, 'repair-f9-restart', 'reload')
        cycled, _ = run('door-cycle', 'door-cycle', repair_db)
        require(cycled['metrics']['door_cycle'] is True, 'Occupied closure/reopen was not proven')
        helped, _ = run('help', 'optional-help', repair_db)
        require(helped['metrics']['help'] is True and
                chapter_record(helped, 'npc_quest')['lamp_connected'], 'Caretaker help did not connect lamp')
        returned, pixels = run('depart-return', 'depart-return', repair_db)
        require(returned['metrics']['depart_return'] is True, 'Actual grounded departure/return missing')
        restart(returned, pixels, repair_db, 'repair-final-restart')
        coverage.update(repair_route=True, occupied_door_close=True, optional_help=True,
                        depart_return=True, restart_pixels_identity=True, actual_f9_reload=True)
        checks.append('Continuous actual W/E repair and Pencil Room traversal, occupied door rejection, Ctrl+Y lamp help and grounded return survive fresh processes and F9 with exact pixels/history')

        bypass_db = work / 'bypass.sqlite'
        base, _ = run('seed', 'bypass-seed', bypass_db)
        bypass, _ = run('bypass-route', 'bypass-route', bypass_db)
        preserved(base, bypass)
        require(bypass['metrics']['bypass_route'] is True and bypass['metrics']['empty_socket'] is True and
                chapter_record(bypass, 'progress')['first_route'] == 'bypass' and
                chapter_record(bypass, 'progress')['pencil_visited'],
                'Actual empty-socket recovery/B/relay E/service door guidance or grounded Pencil route missing')
        relay = chapter_record(bypass, 'fault')['bypass_relay']
        declined, _ = run('decline', 'optional-decline', bypass_db)
        require(declined['metrics']['decline'] is True and
                not chapter_record(declined, 'npc_quest')['lamp_connected'], 'Optional decline forced lamp help')
        removed, pixels = run('feed-loss', 'feed-loss', bypass_db)
        require(removed['metrics']['feed_loss'] is True and not records(removed)[relay]['fields']['alive'] and
                chapter_record(removed, 'service_door')['unlocked'] and
                chapter_record(removed, 'service_door')['open'] and
                'relay feed is offline' in removed['hint'],
                'Delete did not preserve relay tombstone, truthful offline guidance and latched unpowered return')
        for checkpoint in ('bypass-route.bmp.connected-feed.hud.bmp',
                           'feed-loss.bmp.offline-feed.hud.bmp', 'feed-loss.bmp.nearby-arc.hud.bmp'):
            actual_hud = (work / checkpoint).read_bytes()
            require(len(actual_hud) > 54 and actual_hud[:2] == b'BM',
                    f'Actual native checkpoint hint HUD was not captured: {checkpoint}')
        restart(removed, pixels, bypass_db, 'feed-loss-restart')
        coverage.update(bypass_route=True, optional_decline=True, feed_build_dismantle=True,
                        latched_unpowered_return=True, empty_socket_survives=True)
        checks.append('Actual connected-bypass HUD directs its healthy service door before entry; continuous traversal reaches Pencil Room, and relay Delete makes offline guidance visible while nearby arc danger takes priority over completed progress before the latched unpowered return')

        hazard_db = work / 'hazard.sqlite'
        run('seed', 'hazard-seed', hazard_db)
        recovered, pixels = run('hazard', 'hazard', hazard_db)
        for key in ('hazard_pause', 'hazard_recovery', 'critical_backpressure',
                    'recovery_input_consumed', 'stale_intent_rejected'):
            require(recovered['metrics'][key] is True, f'Actual chapter hazard proof omitted {key}')
        require(chapter_record(recovered, 'progress')['recoveries'] == 2 and
                len([event for event in recovered['events'] if event['type'] == 'hazard.outcome']) == 2,
                'Recovery duplicated a cycle or omitted actual durable outcomes')
        restart(recovered, pixels, hazard_db, 'hazard-restart')
        coverage.update(hazard_pause=True, hazard_recovery=True, critical_backpressure=True,
                        recovery_consumes_old_input=True, stale_activation_rejected=True)
        checks.append('Actual clock pauses for inspection/focus; one-credit storage backpressure retains contact before teleport, recovery consumes old B input, repeated cycles deduplicate and stale activation intent drops')

        for step, metric, coverage_key in (('fail-retry', 'live_retry', 'live_f5_held_contact'),
                                           ('close-drain', 'close_drained', 'close_drains_held_contact')):
            database = work / (step + '.sqlite')
            base, _ = run('seed', step + '-seed', database)
            completed, pixels = run(step, step, database)
            preserved(base, completed)
            require(completed['metrics'][metric] is True and
                    completed['durable_revision'] == base['durable_revision'] + 2 and
                    chapter_record(completed, 'progress')['recoveries'] == 1 and
                    len([event for event in completed['events'] if event['type'] == 'hazard.outcome']) == 1,
                    f'{step}: held physical contact was lost, duplicated or acknowledged before saving')
            restart(completed, pixels, database, step + '-restart')
            coverage[coverage_key] = True
        checks.append('Actual F5 retries a failed pending save while holding body/clock/contact; actual WM_CLOSE keeps its HWND alive until that contact publishes once and both batches truly save, then restart preserves exact evidence')

        remote_db = work / 'remote.sqlite'
        run('seed', 'remote-seed', remote_db)
        remote, _ = run('remote-nodes', 'remote-nodes', remote_db)
        require(remote['metrics']['remote_nodes'] is True, 'Remote E/Delete body reach missing')
        translated, _ = run('translated-walk', 'translated-walk', work / 'translated.sqlite')
        require(translated['metrics']['translated_walk'] is True and
                translated['metrics']['walking_ticks'] > 100, 'Negative-height board repeatedly reset its supported body')
        coverage.update(remote_node_reach=True, translated_board_supported=True)
        checks.append('Distant Node E/Delete remain recoverable no-effect input; actual walking on an imported board shifted down 30m stays supported without fall reset')

        reload_db = work / 'reload-failure.sqlite'
        before, old_pixels = run('seed', 'reload-failure-seed', reload_db)
        gate = work / 'reload-gate'
        args, report, capture = arguments('reload-failure', 'reload-failure', reload_db,
                                           extras=('--proof-gate', str(gate)))
        processes += 1
        process = subprocess.Popen([str(executable), *args], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        writer = None
        try:
            deadline = time.monotonic() + 30
            ready = Path(str(gate) + '.ready')
            while not ready.exists():
                require(process.poll() is None and time.monotonic() < deadline,
                        'Reload-failure native process did not reach ready gate')
                time.sleep(.01)
            writer = sqlite3.connect(reload_db)
            writer.execute('BEGIN IMMEDIATE')
            Path(str(gate) + '.go').write_text('external writer owns actual transaction', encoding='utf-8')
            stdout, stderr = process.communicate(timeout=45)
            completed_child(subprocess.CompletedProcess(args, process.returncode, stdout, stderr),
                            'reload-failure', 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
            if writer is not None:
                writer.rollback()
                writer.close()
        retained, pixels = read_report(report, capture)
        require(retained['metrics']['reload_failure'] is True and
                state(before) == state(retained) and pixels == old_pixels,
                'F9 read/open failure discarded live world state')
        coverage['reload_failure_retains_live'] = True
        checks.append('An actual external SQLite writer makes staged F9 reopen fail while the native process retains its live owner, body, geometry and heads')

        m2_db = work / 'm2-upgrade.sqlite'
        for step in ('seed', 'repair', 'build'):
            args, report, _ = arguments(step, 'm2-' + step, m2_db, chapter=False)
            child(args, 'm2-' + step)
        m2_report = json.loads(report.read_text(encoding='utf-8'))
        old = database_rows(m2_db)
        args, _, _ = arguments('inspect', 'upgrade-without-consent', m2_db)
        rejected = child(args, 'upgrade-without-consent', 1)
        require('--upgrade-chapter' in rejected.stderr and database_rows(m2_db) == old,
                'Chapter silently upgraded or altered an existing M2 world')
        upgraded, pixels = run('inspect', 'explicit-upgrade', m2_db, ('--upgrade-chapter',))
        after = database_rows(m2_db)
        require(after['format'] == 2 and upgraded['scope'] == m2_report['scope'],
                'Explicit chapter extension replaced world/timeline or omitted format2')
        for table in ('aibs_gameplay_baselines', 'aibs_gameplay_baseline_components'):
            require(after[table] == old[table], 'Upgrade changed original raw baseline or exact records')
        for table in ('aibs_gameplay_batches', 'aibs_gameplay_events', 'aibs_gameplay_components'):
            require(set(old[table]) <= set(after[table]), 'Upgrade rewrote old exact receipts/events/Nodes')
        restart(upgraded, pixels, m2_db, 'upgraded-restart')
        coverage.update(explicit_m2_upgrade=True, m2_history_preserved=True)
        checks.append('M2 chapter selection rejects without explicit upgrade, then atomically adds registry/availability while retaining complete old scope, Node UUID bytes, baseline/raw, receipts and events')

        original = work / 'original.aibs'
        for step in ('seed', 'edit'):
            label = 'original-' + step
            child(['--world-step', step, '--checkpoint', str(original), '--capture',
                   str(work / (label + '.bmp')), '--world-report', str(work / (label + '.json'))], label)
        raw = original.read_bytes()
        source = json.loads((work / 'original-edit.json').read_text(encoding='utf-8'))
        imported_db = work / 'imported.sqlite'
        imported, pixels = run('seed', 'original-import', imported_db,
                               ('--import-checkpoint', str(original)))
        imported_rows = database_rows(imported_db)
        require(original.read_bytes() == raw and imported['scope']['world_id'] == source['world_id'] and
                imported_rows['aibs_gameplay_baselines'][0][-1] == raw and
                set(source['entity_ids'].values()) <= set(records(imported)),
                'Chapter import changed source bytes/world/UUIDs or failed to preserve raw evidence')
        restart(imported, pixels, imported_db, 'imported-restart')
        require(original.read_bytes() == raw, 'Chapter restart rewrote original checkpoint')
        coverage['original_import_preserved'] = True
        checks.append('Genuine original format1 edit imports into chapter without changing original bytes, UUIDs or world identity; exact raw checkpoint remains in the atomic baseline')
        coverage.update(native_gpu=True, actual_player_pov=True, actual_hud_fits=True)
        require(hashlib.sha256(executable.read_bytes()).hexdigest() == result['executableSha256'],
                'Native executable changed during the process proof')
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = str(error)
        checks.append('FAILED: ' + str(error))
    finally:
        coverage.update(processes=processes, debug_layer=bool(gpu) and
                        all(item['debug_layer'] for item in gpu),
                        debug_errors=sum(item['debug_errors'] for item in gpu))
        publish()
    print(json.dumps(result))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: verify_first_boot_chapter.py NATIVE_EXECUTABLE OUTPUT_DIRECTORY')
    raise SystemExit(verify(Path(sys.argv[1]), Path(sys.argv[2])))
