"""Create-only current-player hidden seed/reload proof for the qualified LH asset.

No original save is admitted. This is controlled native integration, not ordinary
play, persistent SavedChapterPlayClient acceptance, installed parity or profiling.
Timed-out children are retained, never killed or automatically restarted.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import struct
import time
import uuid

import psutil

from qualify_rtx_creator import ROOT, VARIANTS, copy_tree, load, long, need, pin, plain, tree, write_json

MANIFEST = ROOT / 't/hudvis_build01/frozen-candidate-v02.json'
MANIFEST_SHA = '5b022239f95d97e31797e82be137881a52035a4e1a9426538ddb8d9e975b8f39'
PLAYER_SHA = '60ee067f229e040a359e302bb90def884d49223af5a616e6065d9fced1583cda'
CREATOR = VARIANTS / 'Creator_LH_20261111_v05'


def validate_pins():
    need(pin(MANIFEST)['sha256'] == MANIFEST_SHA, 'Frozen manifest identity changed')
    manifest = load(MANIFEST)
    for name, expected in manifest['artifact_pins'].items():
        need(pin(Path(name)) == expected, 'Frozen artifact changed: ' + name)
    worktree = Path(manifest['worktree'])
    checked = {}
    for name, expected in manifest['source_pins'].items():
        source = ROOT / Path(name).relative_to(worktree)
        need(pin(source)['sha256'] == expected, 'Canonical compiled source changed: ' + str(source))
        checked[str(source)] = expected
    player = Path(manifest['player'])
    need(pin(player)['sha256'] == PLAYER_SHA, 'Wrong current player')
    return player, {'manifest': pin(MANIFEST), 'artifacts': manifest['artifact_pins'], 'canonical_sources': checked}


def validate_bitmap(path):
    from qualify_rtx_creator import read
    data = read(path)
    need(len(data) >= 54 and data[:2] == b'BM', 'Invalid native BMP header')
    size, offset = struct.unpack_from('<IxxxxI', data, 2)
    width, height = struct.unpack_from('<ii', data, 18)
    planes, bits = struct.unpack_from('<HH', data, 26)
    compression = struct.unpack_from('<I', data, 30)[0]
    need(size == len(data) and offset >= 54 and 0 < width <= 3840 and 0 < abs(height) <= 2160
         and planes == 1 and bits in (24, 32) and compression == 0, 'Unexpected native BMP layout')
    stride = ((width * bits + 31) // 32) * 4
    need(offset + stride * abs(height) == len(data), 'Native BMP payload truncated')
    return {'width': width, 'height': abs(height), **pin(path)}


def run_stage(player, output, session, stage, dimensions=(1440, 900)):
    report = output / (stage + '.json')
    capture = output / (stage + '.bmp')
    args = [str(player), '--durable-world', '--content-definition', str(output/'project/opening.aibd'),
            '--asset-root', str(output/'project/assets/packs'), '--database', str(output/'world.sqlite'),
            '--project', 'prop01-native-acceptance', '--branch', 'independent-prop01-v1',
            '--play-session', session, '--stop-file', str(output/(stage+'.stop.request')),
            '--durable-step', stage, '--capture', str(capture), '--durable-report', str(report),
            '--width', str(dimensions[0]), '--height', str(dimensions[1])]
    need(not report.exists() and not capture.exists(), 'Proof outputs must be new')
    env = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP') if key in os.environ}
    env['PATH'] = str(player.parent) + ';C:\\Windows\\System32'
    with (output/(stage+'.stdout.log')).open('xb') as stdout, (output/(stage+'.stderr.log')).open('xb') as stderr:
        child = subprocess.Popen(args, cwd=player.parent, env=env, stdout=stdout, stderr=stderr,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        identity = {'pid': child.pid, 'created': psutil.Process(child.pid).create_time(),
                    'args': args, 'retained_exact_handle': True}
        write_json(output/(stage+'.started.json'), identity)
        print(stage + ': started owned player ' + str(child.pid), flush=True)
        deadline = time.monotonic() + 120
        while child.poll() is None and time.monotonic() < deadline:
            time.sleep(.25)
        identity.update(terminal=child.poll() is not None, exit_code=child.poll())
        write_json(output/(stage+'.process.json'), identity)
        need(identity['terminal'], 'Owned player still live: preserve its handle/PID; no restart')
        need(child.returncode == 0, 'Player failed; inspect retained stdout/stderr')
    value = load(report)
    need(value['schema_version'] == 1 and value['status'] == 'passed' and value['saved'] and value['pending_batches'] == 0,
         'Native report is not durably saved')
    need(value['scope']['context'] == 'temporary_play', 'Unexpected persistent scope')
    need(value['scope']['project_id'] == 'prop01-native-acceptance' and value['scope']['branch_id'] == 'independent-prop01-v1'
         and value['scope']['timeline_id'] == session, 'Unexpected session identity')
    need(value['visible_revision'] == value['durable_revision'], 'Visible state not durable')
    need(value['content']['revision'] == 6 and value['content']['fingerprint'] == pin(output/'project/opening.aibd')['sha256'],
         'Player did not load exact current export')
    metrics = value['metrics']
    need(metrics['debug_layer'] and metrics['debug_errors'] == 0 and metrics['debug_warnings'] == 0 and metrics['nonbackground_pixels'] > 10000,
         'GPU readback or debug diagnostics failed')
    need(metrics['hud_readback'] and metrics['hud_fits'] and metrics['hud_capture'], 'HUD proof incomplete')
    need(metrics['reload'] == (stage == 'reload'), 'Wrong actual F9 result')
    need(not value['os_focus_input_verified'] and not value['human_pacing_measured'], 'Controlled proof mislabeled')
    captures = {str(path): validate_bitmap(path) for path in
                (capture, Path(str(capture)+'.pov.bmp'), Path(str(capture)+'.hud.bmp'))}
    return {'process': identity, 'report': value, 'captures': captures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.absolute()
    plain(output)
    need(output.parent == VARIANTS and not long(output).exists(), 'Use a new direct child of reviewed RTX variants root')
    player, pins = validate_pins()
    source = CREATOR/'project'
    before = tree(source)
    author = load(CREATOR/'author.json')
    need(pin(source/'opening.aibd') == author['opening'], 'Creator export changed')
    metadata = load(source/'.aibs-chapter-project.json')
    need(metadata['project'] == 'prop01-native-acceptance' and metadata['branch'] == 'independent-prop01-v1', 'Unexpected chapter identity')
    long(output).mkdir()
    write_json(output/'preflight.json', {'pins': pins, 'source': str(source), 'source_tree': before})
    result = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'INCOMPLETE', 'scope': 'controlled hidden temporary native seed/reload',
              'player': str(player), 'player_sha256': PLAYER_SHA, 'session': str(uuid.uuid4()), 'stages': {}}
    try:
        copy_tree(source, output/'project')
        for stage in ('seed', 'reload'):
            result['stages'][stage] = run_stage(player, output, result['session'], stage)
        seed = result['stages']['seed']['report']
        reload = result['stages']['reload']['report']
        for key in ('scope', 'content', 'chapter_ids', 'components', 'events', 'visible_revision', 'durable_revision', 'durable_sequence'):
            need(seed[key] == reload[key], 'Fresh process reload changed durable state: ' + key)
        need(tree(output/'project') == before, 'Owned immutable chapter/asset input changed')
        validate_pins()
        result['status'] = 'PASS_CONTROLLED_CURRENT_PLAYER_SEED_RELOAD'
    except Exception as exc:
        result['status'] = 'FAILED'
        result['error'] = str(exc)
        raise
    finally:
        result['original_project_unchanged'] = tree(source) == before
        if not result['original_project_unchanged']:
            result['status'] = 'FAILED_SOURCE_PRESERVATION'
        write_json(output/'qualification.json', result)
        print(result['status'], flush=True)
    need(result['original_project_unchanged'], 'Original project changed')


if __name__ == '__main__':
    main()
