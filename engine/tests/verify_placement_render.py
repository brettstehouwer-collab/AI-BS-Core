"""Cross-process native placement persistence/render proof; all evidence retained.

This runner launches real DX12 viewport/player processes. Run only in the
explicitly allocated GPU verification slot, never alongside another GPU suite.
"""
from datetime import datetime, timezone
from pathlib import Path
import ctypes
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import uuid


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def bounded_text(path, maximum=65536):
    with Path(path).open('rb') as stream:
        value = stream.read(maximum + 1)
    if len(value) > maximum:
        raise AssertionError('Native proof output exceeded its byte bound: ' + str(path))
    return value.decode('utf-8', 'replace')


def pixel_difference(first, second):
    first, second = Path(first).read_bytes(), Path(second).read_bytes()
    if (first[:2] != b'BM' or second[:2] != b'BM' or len(first) != len(second)
            or first[18:30] != second[18:30]):
        raise AssertionError('GPU captures must have matching BMP dimensions/format')
    offset = struct.unpack_from('<I', first, 10)[0]
    if offset != struct.unpack_from('<I', second, 10)[0] or offset < 54:
        raise AssertionError('Unexpected native GPU capture pixel offset')
    return sum(first[i:i + 4] != second[i:i + 4] for i in range(offset, len(first), 4))


def replace_snapshot(source, target):
    data = Path(source).read_bytes()
    temporary = target.with_suffix('.tmp')
    with temporary.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if os.name == 'nt' and target.exists():
        from ctypes import wintypes
        replace = ctypes.WinDLL('kernel32', use_last_error=True).ReplaceFileW
        replace.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                            wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p)
        replace.restype = wintypes.BOOL
        if not replace(str(target), str(temporary), None, 0, None, None):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        os.replace(temporary, target)


def verify(fixture, viewport, player, source_pack, output):
    fixture, viewport, player, source_pack, output = (
        Path(path).resolve() for path in (fixture, viewport, player, source_pack, output))
    output.mkdir(parents=True, exist_ok=True)
    work = output / ('placement-render-' + str(uuid.uuid4()))
    work.mkdir()
    report = output / (work.name + '-verification.json')
    result = {'schema_version': 1, 'status': 'failed', 'checks': [], 'metrics': {},
              'work_directory': str(work), 'fixture_executable': str(fixture),
              'viewport_executable': str(viewport), 'player_executable': str(player),
              'source_fallback': False, 'actual_model_inference': False,
              'captures': {}, 'owned_processes_joined': False}
    processes = []

    def check(ok, why):
        if not ok:
            raise AssertionError(why)
        result['checks'].append(why)

    def child(executable, arguments, label, expected=0, seconds=60):
        stdout, stderr = work / (label + '.stdout.log'), work / (label + '.stderr.log')
        with stdout.open('xb') as out, stderr.open('xb') as err:
            process = subprocess.Popen([str(executable), *map(str, arguments)], stdout=out,
                stderr=err, stdin=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            processes.append(process)
            try:
                process.wait(timeout=seconds)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
        text, errors = bounded_text(stdout), bounded_text(stderr)
        check(process.returncode == expected,
              f'{label}: native exit {process.returncode}, expected {expected}: {errors}')
        return text, errors

    def viewport_probe(label, snapshot, store, selected=None, expected=0):
        capture, proof = work / (label + '.bmp'), work / (label + '.json')
        arguments = ['--snapshot', snapshot, '--stop-file', work / (label + '.stop'),
                     '--asset-root', store, '--self-test', '--capture', capture, '--report', proof]
        text, errors = child(viewport, arguments, label, expected)
        if expected:
            check(not capture.exists() and not proof.exists() and 'AIBV1 READY ' not in text,
                  label + ': missing/tampered dependency rejected before capture or source fallback')
            return None
        data = json.loads(proof.read_text(encoding='utf-8'))
        check(data['debug_errors'] == 0 and data['nonbackground_pixels'] > 100,
              label + ': actual DX12 readback contains geometry without debug errors')
        if selected is not None:
            check(data['selected_uuid'] == selected and (' ' + selected) in text,
                  label + ': actual native Win32 pick preserves the placement UUID')
        result['captures'][label] = str(capture)
        overview = Path(str(capture) + '.unselected.bmp')
        check(overview.is_file(), label + ': pre-focus overview readback exists')
        result['captures'][label + '_overview'] = str(overview)
        result['metrics'][label] = data
        return overview

    try:
        # File admission occurs before any process launch. A missing fixture is
        # a deterministic RED result and cannot accidentally start a GPU child.
        for path in (fixture, viewport, player):
            check(path.is_file(), 'Required native proof executable exists: ' + str(path))
        original_pack = {path.relative_to(source_pack).as_posix(): digest(path)
                         for path in source_pack.rglob('*') if path.is_file()}
        check(len(original_pack) == 4, 'Source reference pack has exactly four retained public files')
        catalog = bounded_text(source_pack / 'catalog.aibcat', maximum=1024 * 1024)
        if catalog.startswith('AIBCAT 2\nsurface '):
            source_kind, payload_extension, content_version = 'surface', '.aibsurf', 3
        else:
            check(catalog.startswith('AIBCAT 1\n'), 'Source pack declares a supported explicit native catalog version')
            source_kind, payload_extension, content_version = 'mesh', '.aibmesh', 2
        result['source_input'] = {'kind': source_kind, 'payload_extension': payload_extension,
                                  'placement_content_version': content_version,
                                  'catalog_sha256': digest(source_pack / 'catalog.aibcat'),
                                  'retained_file_sha256': original_pack}
        project = work / 'fixture'
        child(fixture, [source_pack, project], 'prepare-fixture')
        expected = json.loads((project / 'expected.json').read_text(encoding='utf-8'))
        check(expected.get('asset_kind', 'mesh') == source_kind
              and expected.get('payload_extension', '.aibmesh') == payload_extension
              and expected.get('placement_content_version', 2) == content_version,
              'Fixture kind, cooked suffix and retained content version match the actual source catalog')
        check((source_kind == 'surface' and expected.get('textured_vertices', 0) > 0 and expected.get('texture_count', 0) > 0)
              or (source_kind == 'mesh' and expected.get('textured_vertices', 0) == 0 and expected.get('texture_count', 0) == 0),
              'Fixture resolves the selected typed or legacy native rendering path')
        store = project / 'project/assets/packs'
        journal = project / 'project/chapter.aiba'
        protected = {path: digest(path) for path in project.rglob('*') if path.is_file()}
        child(fixture, ['--reopen', project], 'reopen-fixture')
        reopened = json.loads((project / 'reopened.json').read_text(encoding='utf-8'))
        check(reopened['fingerprint'] == expected['restored']['fingerprint'] and
              reopened['placement_id'] == expected['placement_id'] and
              reopened['world_id'] == expected['world_id'],
              'A separate native owner process reopened the saved placement/fingerprint/world identity')
        check(all(digest(path) == sha for path, sha in protected.items()),
              'Native reopen preserves every existing authored/asset/protected fixture byte')
        protected.update({path: digest(path) for path in project.rglob('*') if path.is_file()})

        # Empty initial selection prevents transient highlight differences from
        # being misreported as rendered asset geometry. Fixture bounds assert
        # that every overview uses the same framing as its baseline.
        overviews = {}
        for label in ('baseline', 'placed', 'moved', 'erased', 'restored', 'reopened'):
            overviews[label] = viewport_probe(label, project / (label + '.aibv'), store)
        differences = {label: pixel_difference(overviews['baseline'], overviews[label])
                       for label in ('placed', 'moved', 'erased', 'restored', 'reopened')}
        result['metrics']['baseline_pixel_differences'] = differences
        check(differences['placed'] > 100 and differences['moved'] > 100,
              'Actual overview GPU pixels contain the persisted placement before and after movement')
        check(pixel_difference(overviews['placed'], overviews['moved']) > 100,
              'Moving the saved placement changes actual rendered geometry')
        check(differences['erased'] == 0,
              'Erasing the visual placement restores the exact original overview GPU pixels')
        check(pixel_difference(overviews['moved'], overviews['restored']) == 0 and
              pixel_difference(overviews['restored'], overviews['reopened']) == 0,
              'Undo restore and separate-process reopen produce identical saved placement pixels')
        for label in ('placed', 'moved', 'restored', 'reopened'):
            viewport_probe(label + '-pick', project / (label + '-pick.aibv'), store,
                           expected['placement_id'])

        # Exercise the actual live renderer replacement path as well as startup.
        live = work / 'live.aibv'
        replace_snapshot(project / 'baseline.aibv', live)
        stop = work / 'live.stop'
        stdout, stderr = work / 'live.stdout.log', work / 'live.stderr.log'
        with stdout.open('xb') as out, stderr.open('xb') as err:
            process = subprocess.Popen([str(viewport), '--snapshot', str(live), '--stop-file', str(stop),
                '--asset-root', str(store)], stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            processes.append(process)
            try:
                for label in ('baseline', 'placed', 'moved', 'erased', 'restored'):
                    if label != 'baseline':
                        replace_snapshot(project / (label + '.aibv'), live)
                    state = expected[label]
                    marker = f'AIBV1 READY {state["snapshot_id"]} {expected["world_id"]} {state["head"]}'
                    deadline = time.monotonic() + 20
                    while marker not in bounded_text(stdout) and time.monotonic() < deadline and process.poll() is None:
                        time.sleep(.01)
                    check(marker in bounded_text(stdout), label + ': live native scene replacement reached correlated READY')
                check('Snapshot rejected:' not in bounded_text(stderr), 'Live renderer updates rejected no valid snapshots')
                # A persistent missing source must be visible without discarding
                # the last valid scene. Restore the SAME timestamp/revision to
                # prove recovery does not depend on a newer timestamp.
                held = work / 'live-held.aibv'
                live.replace(held)
                deadline = time.monotonic() + 8
                while 'Snapshot unavailable:' not in bounded_text(stderr) and time.monotonic() < deadline and process.poll() is None:
                    time.sleep(.01)
                check(process.poll() is None and 'Snapshot unavailable:' in bounded_text(stderr),
                      'Persistent source unavailability is reported while the viewport stays alive')
                held.replace(live)
                deadline = time.monotonic() + 8
                while 'Snapshot recovered:' not in bounded_text(stderr) and time.monotonic() < deadline and process.poll() is None:
                    time.sleep(.01)
                check('Snapshot recovered:' in bounded_text(stderr),
                      'Restoring the same snapshot revision/timestamp explicitly reports recovery')
            finally:
                if process.poll() is None:
                    stop.write_text('Owned proof requested close\n', encoding='utf-8')
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)
            check(process.returncode == 0, 'Live viewport stop marker closed and joined its owned process')

        # Tampering affects only fresh private fixture copies; source packs,
        # authoring journals and retained save sentinels remain untouched.
        for label, filename in (('bad-mesh', expected['asset_sha256'] + payload_extension),
                                ('bad-license', 'LICENSE.txt')):
            private_store = work / label
            shutil.copytree(store, private_store)
            candidates = list(private_store.rglob(filename))
            check(len(candidates) == 1, label + ': one owned tamper target')
            target = candidates[0]
            check(target.resolve().is_relative_to(private_store.resolve()), label + ': tamper target stays inside owned fixture')
            target.write_bytes(target.read_bytes() + b'fault injection')
            viewport_probe(label, project / 'restored.aibv', private_store, expected=1)
        viewport_probe('missing-store', project / 'restored.aibv', work / 'absent-store', expected=1)

        # Actual managed Play consumes a private copied closure and a fresh
        # temporary-play SQLite scope. Its files remain as proof artifacts.
        for label in ('baseline', 'restored'):
            scratch = work / ('play-inspect-' + label)
            scratch.mkdir()
            private_store = scratch / 'packs'
            shutil.copytree(store, private_store)
            session = str(uuid.uuid4())
            arguments = ['--durable-world', '--content-definition', project / (label + '.aibd'),
                '--asset-root', private_store, '--database', scratch / 'world.sqlite',
                '--project', 'placement-render-proof', '--branch', 'main', '--play-session', session,
                '--stop-file', scratch / 'stop.request', '--durable-step', 'inspect',
                '--capture', work / ('play-' + label + '.bmp'),
                '--durable-report', work / ('play-' + label + '.json')]
            child(player, arguments, 'play-inspect-' + label, seconds=90)
            data = json.loads((work / ('play-' + label + '.json')).read_text(encoding='utf-8'))
            check(data['scope']['context'] == 'temporary_play' and data['scope']['timeline_id'] == session
                  and data['content']['fingerprint'] == expected[label]['fingerprint'],
                  label + ': actual native Play pins the exact temporary scope and authored definition')
            check(data['metrics']['debug_errors'] == 0 and data['metrics']['nonbackground_pixels'] > 10000
                  and data['saved'] and data['pending_batches'] == 0,
                  label + ': actual Play render and durable close complete without pending work')
            result['captures']['play_' + label] = str(work / ('play-' + label + '.bmp'))
        play_difference = pixel_difference(work / 'play-baseline.bmp', work / 'play-restored.bmp')
        result['metrics']['play_placement_pixels_changed'] = play_difference
        check(play_difference > 100, 'Managed Play renders the persisted asset geometry in actual overview pixels')

        scratch = work / 'managed-play'
        scratch.mkdir()
        private_store = scratch / 'packs'
        shutil.copytree(store, private_store)
        session, fingerprint = str(uuid.uuid4()), expected['restored']['fingerprint']
        stop, stdout, stderr = scratch / 'stop.request', work / 'managed.stdout.log', work / 'managed.stderr.log'
        with stdout.open('xb') as out, stderr.open('xb') as err:
            process = subprocess.Popen([str(player), '--durable-world', '--content-definition', str(project / 'restored.aibd'),
                '--asset-root', str(private_store), '--database', str(scratch / 'world.sqlite'),
                '--project', 'placement-render-proof', '--branch', 'main', '--play-session', session,
                '--stop-file', str(stop)], stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            processes.append(process)
            try:
                deadline = time.monotonic() + 30
                while 'aibs.play.ready' not in bounded_text(stdout) and time.monotonic() < deadline and process.poll() is None:
                    time.sleep(.02)
                check('aibs.play.ready' in bounded_text(stdout), 'Managed native Play rendered its first placed-content frame')
            finally:
                if process.poll() is None:
                    stop.write_text('Owned proof requested close\n', encoding='utf-8')
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=10)
            check(process.returncode == 0, 'Managed Play stop marker drained and joined the owned native process')
        events = [json.loads(line) for line in bounded_text(stdout).splitlines() if line.startswith('{')]
        check([event['event'] for event in events] == ['aibs.play.ready', 'aibs.play.stopped'] and
              all(event['play_session'] == session and event['world_id'] == expected['world_id']
                  and event['content_fingerprint'] == fingerprint and event['saved'] for event in events),
              'Managed Play READY/STOPPED receipts match the immutable placement content/session and saved state')
        result['metrics']['managed_play_events'] = events
        check(all(digest(path) == sha for path, sha in protected.items()),
              'Viewport, negative fixtures and actual Play leave all authored documents/assets/save sentinels unchanged')
        check({path.relative_to(source_pack).as_posix(): digest(path)
               for path in source_pack.rglob('*') if path.is_file()} == original_pack,
              'Original source reference pack remains byte-identical')
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = str(error)
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
        result['owned_processes_joined'] = all(process.poll() is not None for process in processes)
        if not result['owned_processes_joined']:
            result['status'] = 'failed'
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'report': str(report),
                      'checks': len(result['checks']), **({'error': result['error']} if 'error' in result else {})}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    if len(sys.argv) != 6:
        raise SystemExit('Usage: verify_placement_render.py FIXTURE VIEWPORT PLAYER SOURCE_PACK OUTPUT_DIRECTORY')
    raise SystemExit(verify(*sys.argv[1:]))
