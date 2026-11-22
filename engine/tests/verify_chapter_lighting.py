"""Actual native chapter power/lighting/render/restart proof on owned files.

Run only in the coordinated GPU verification slot. Uses no family references,
real player saves, model inference or public services.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import uuid


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pixel_difference(first, second):
    first, second = Path(first).read_bytes(), Path(second).read_bytes()
    if (first[:2] != b'BM' or second[:2] != b'BM' or len(first) != len(second)
            or first[18:30] != second[18:30]):
        raise AssertionError('Native lighting BMP readbacks must have matching formats')
    offset = struct.unpack_from('<I', first, 10)[0]
    if offset != struct.unpack_from('<I', second, 10)[0] or offset < 54:
        raise AssertionError('Invalid native BMP pixel offset')
    return sum(first[i:i+4] != second[i:i+4] for i in range(offset, len(first), 4))


def verify(fixture, player, output):
    fixture, player, output = (Path(p).resolve() for p in (fixture, player, output))
    output.mkdir(parents=True, exist_ok=True)
    work = output / ('chapter-lighting-' + str(uuid.uuid4()))
    work.mkdir()
    report = output / (work.name + '-verification.json')
    result = {'schema_version': 1, 'status': 'failed', 'checks': [], 'metrics': {},
              'work_directory': str(work), 'gpu_requested': True,
              'family_references_used': False, 'model_inference': False,
              'processes_joined': False}
    processes = []

    def check(value, message):
        if not value:
            raise AssertionError(message)
        result['checks'].append(message)

    def child(executable, arguments, label, seconds=180):
        with (work/(label+'.stdout.log')).open('xb') as stdout, (work/(label+'.stderr.log')).open('xb') as stderr:
            process = subprocess.Popen([str(executable), *map(str, arguments)], stdout=stdout, stderr=stderr,
                stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            processes.append(process)
            try:
                code = process.wait(timeout=seconds)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=15)
        check(code == 0, label + ': native process completed: ' + (work/(label+'.stderr.log')).read_text(encoding='utf-8', errors='replace')[-2000:])

    def component(data, kind):
        return next(r for r in data['components'] if r['type'] == kind)

    def coherent(data, expected, phase, enabled, session, require_route_witness=True):
        check(data['status'] == 'passed' and data['saved'] and data['pending_batches'] == 0
              and data['visible_revision'] == data['durable_revision'],
              phase + ': native durable acknowledgement completed')
        check(data['scope']['context'] == 'temporary_play' and data['scope']['timeline_id'] == session
              and data['scope']['world_id'] == expected['world_id']
              and data['scope']['project_id'] == 'chapter-lighting-proof' and data['scope']['branch_id'] == 'main',
              phase + ': native process used the exact private scope')
        check(data['content']['fingerprint'] == expected['withlights_fingerprint' if enabled else 'withoutlights_fingerprint'],
              phase + ': native runtime pins the exact authored light/control document')
        lighting = data['lighting']
        powered = phase != 'inspect'
        check(lighting['enabled'] is enabled and lighting['points'] == (2 if powered else 1) * int(enabled)
              and lighting['directional'] is (enabled and powered)
              and lighting['main_power'] is (phase == 'repair-route')
              and lighting['bypass_power'] is (phase == 'bypass-route'),
              phase + ': reported rendered lights match the actual authoritative supply')
        metrics = data['metrics']
        check(metrics['debug_layer'] and metrics['debug_errors'] == 0 and metrics['nonbackground_pixels'] > 10000,
              phase + ': actual GPU readback is nonblank with no debug errors')
        if 'debug_warnings' in metrics:
            check(metrics['debug_warnings'] == 0, phase + ': actual GPU debug warnings are zero')
        progress = component(data, 'firstboot.ChapterProgress')['fields']
        fault = component(data, 'firstboot.PowerFault')['fields']
        if not powered:
            check(not progress['shelter_secured'] and progress['first_route'] == 'none',
                  'Reserve lighting does not silently complete shelter or a route')
        elif phase == 'repair-route':
            check((not require_route_witness or metrics['repair_route']) and progress['first_route'] == 'repair'
                  and fault['capacity'] == 100 and not fault['isolated'],
                  'Main illumination follows actual repair/reconnection and physical route crossing')
        else:
            relay = next(r for r in data['components'] if r['entity_id'] == fault['bypass_relay'])
            check((not require_route_witness or metrics['bypass_route']) and progress['first_route'] == 'bypass' and fault['isolated']
                  and fault['bypass_connected'] and relay['fields']['alive'] and relay['fields']['capacity'] == 100,
                  'Bypass illumination follows an actual connected live relay and physical route crossing')

    def run_phase(content, folder, phase, session, label):
        folder.mkdir(exist_ok=True)
        capture, native_report = work/(label+'.bmp'), work/(label+'.json')
        child(player, ['--durable-world', '--content-definition', content, '--asset-root', work/'content/empty-packs',
              '--database', folder/'world.sqlite', '--project', 'chapter-lighting-proof', '--branch', 'main',
              '--play-session', session, '--stop-file', folder/'stop.request', '--durable-step', phase,
              '--capture', capture, '--durable-report', native_report], label)
        return json.loads(native_report.read_text(encoding='utf-8')), capture

    try:
        check(fixture.is_file() and player.is_file(), 'Selected fixture and native player exist')
        result['source_sha256'] = {path.name: sha(path) for path in
                                 (Path(__file__), Path(__file__).with_name('chapter_lighting_fixture.cpp'))}
        result['executable_sha256'] = {'fixture': sha(fixture), 'native_player': sha(player)}
        child(fixture, [work/'content'], 'prepare-fixture', seconds=60)
        expected = json.loads((work/'content/expected.json').read_text(encoding='utf-8'))
        check(expected['geometry_identical'] and not expected['family_references_used'],
              'Authored light and control fixtures retain identical physical geometry without private references')
        retained = {name: sha(work/'content'/name) for name in ('withlights.aibd', 'withoutlights.aibd', 'expected.json')}
        result['fixture_sha256'] = retained
        sentinel = work/'retained-original-save.sqlite'
        sentinel.write_bytes(b'Unselected original-save sentinel; never opened by a runtime\n')
        sentinel_sha = sha(sentinel)
        comparisons = {}
        for phase in ('inspect', 'repair-route', 'bypass-route'):
            captures = {}
            for enabled in (False, True):
                kind = 'withlights' if enabled else 'withoutlights'
                session = str(uuid.uuid4())
                folder = work/(kind+'-'+phase)
                data, capture = run_phase(work/'content'/(kind+'.aibd'), folder, phase, session, kind+'-'+phase)
                coherent(data, expected, phase, enabled, session)
                captures[kind] = capture
                if enabled:
                    reopened, reopen_capture = run_phase(work/'content'/(kind+'.aibd'), folder, 'inspect', session,
                                                         kind+'-'+phase+'-reopened')
                    # The second process inspects the persisted phase, not a newly
                    # completed route; keep the original expected supply but do
                    # not require its per-run scripted movement flag again.
                    coherent(reopened, expected, phase, enabled, session, require_route_witness=False)
                    check(reopened['lighting'] == data['lighting']
                          and {r['entity_id']: r for r in reopened['components']} == {r['entity_id']: r for r in data['components']}
                          and reopened['visible_revision'] == data['visible_revision']
                          and reopened['durable_sequence'] == data['durable_sequence']
                          and reopened['events'] == data['events'],
                          phase + ': fresh process restores exact light-driving state and semantic head')
                    check(pixel_difference(capture, reopen_capture) == 0,
                          phase + ': persisted lighting produces identical overview GPU pixels after restart')
            difference = pixel_difference(captures['withlights'], captures['withoutlights'])
            comparisons[phase] = difference
            check(difference > 100, phase + ': authored light selection changes actual native GPU pixels')
        check(all(sha(work/'content'/name) == digest for name, digest in retained.items()) and sha(sentinel) == sentinel_sha,
              'Native route/restart proofs preserve original fixture documents and unselected save sentinel')
        result['metrics']['authored_vs_legacy_pixels_changed'] = comparisons
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = str(error)
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=15)
        result['processes_joined'] = all(process.poll() is not None for process in processes)
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'report': str(report), 'checks': len(result['checks']),
                      **({'error': result['error']} if 'error' in result else {})}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(verify(*sys.argv[1:]))
