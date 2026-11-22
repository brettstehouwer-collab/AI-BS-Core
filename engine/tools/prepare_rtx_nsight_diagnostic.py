"""Offline isolated diagnostic build; never launches a player or GPU test."""
import argparse
import difflib
import os
from pathlib import Path
import subprocess
import time

from qualify_rtx_creator import ROOT, read, pin, plain, long, write, write_json, load
from qualify_rtx_hud_fit import validate_candidate as validate_origin

SOURCE = ROOT/'t/nsight_diag_source01'
BUILD = ROOT/'t/nsight_diag_build01'
SEED = ROOT/'t/worktrees/hud_visibility_v01/engine'
MANIFEST = BUILD/'frozen-candidate-v01.json'
ORIGIN = ROOT/'t/hudfit_build01/frozen-candidate-v01.json'
INSERTION = ('std::cerr<<"AIBS_NSIGHT_DIAGNOSTIC nonbackground_pixels="<<pixels'
    '<<" debug_errors="<<stats.debug_errors<<" debug_warnings="<<stats.debug_warnings'
    '<<" debug_layer="<<stats.debug_layer<<"\\n";'
    'for(const auto& message:stats.debug_messages)std::cerr<<"AIBS_NSIGHT_DIAGNOSTIC "<<message<<"\\n";')


def need(value, message):
    if not value:
        raise RuntimeError(message)


def inventory():
    rows, total = {}, 0
    for here, directories, files in os.walk(SEED, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in ('out', '.git', '__pycache__'))
        for name in directories:
            plain(Path(here)/name)
        for name in sorted(files):
            path = Path(here)/name
            plain(path)
            info = pin(path)
            total += info['bytes']
            need(len(rows) < 5000 and total <= 256*1024*1024, 'Isolated seed exceeds bounded snapshot budget')
            rows[path.relative_to(SEED).as_posix()] = info
    return rows, total


def run(command, label):
    with (BUILD/(label+'.stdout.log')).open('xb') as stdout, (BUILD/(label+'.stderr.log')).open('xb') as stderr:
        child = subprocess.Popen(list(map(str, command)), cwd=ROOT, stdout=stdout, stderr=stderr,
            stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        write_json(BUILD/(label+'.started.json'), {'pid': child.pid, 'command': list(map(str, command)),
            'exact_popen_handle_retained': True})
        started, retained = time.monotonic(), False
        while child.poll() is None:
            if not retained and time.monotonic()-started > 600:
                retained = True
                write_json(BUILD/(label+'.retained.json'), {'pid': child.pid,
                    'status': 'BUILD_RETAINED_NO_KILL_OR_RESTART', 'exact_popen_handle_retained': True})
            time.sleep(.2)
        write_json(BUILD/(label+'.process.json'), {'pid': child.pid, 'exit_code': child.returncode,
            'terminal': True, 'deadline_exceeded': retained, 'wall_seconds': time.monotonic()-started})
        need(child.returncode == 0 and not retained, label+' failed; preserve diagnostics')


def validate_candidate():
    _, origin_pin = validate_origin()
    manifest = load(MANIFEST)
    need(manifest['scope'] == 'isolated-stderr-diagnostic-only' and manifest['origin_manifest'] == origin_pin,
         'Diagnostic origin differs')
    origin = load(ORIGIN)
    need(len(manifest['source_pins']) == 158 and len(manifest['artifact_pins']) == 9,
         'Diagnostic source/artifact closure incomplete')
    for name, expected in origin['source_pins'].items():
        need(pin(Path(name))['sha256'] == expected, 'Canonical origin changed')
    for name, expected in manifest['source_pins'].items():
        need(pin(Path(name))['sha256'] == expected, 'Isolated compiled source changed')
    for name, expected in manifest['artifact_pins'].items():
        need(pin(Path(name)) == expected, 'Diagnostic artifact changed')
    need(pin(Path(__file__)) == manifest['preparer'], 'Diagnostic preparer changed')
    before = read(BUILD/'durable_world.before.cpp')
    after = read(SOURCE/'engine/apps/durable_world.cpp')
    need(after.count(INSERTION.encode()) == 1 and after.replace(INSERTION.encode(), b'', 1) == before,
         'Diagnostic contains changes beyond exact stderr insertion')
    player = Path(manifest['player'])
    need(pin(player)['sha256'] == manifest['player_sha256'], 'Diagnostic player changed')
    return player, pin(MANIFEST)


def prepare():
    _, origin_pin = validate_origin()
    origin = load(ORIGIN)
    need(not SOURCE.exists() and not BUILD.exists(), 'Diagnostic source/build must be new')
    plain(SOURCE); plain(BUILD)
    rows, total = inventory()
    SOURCE.mkdir(); BUILD.mkdir(); (SOURCE/'engine').mkdir()
    write_json(BUILD/'seed-inventory.json', {'source': str(SEED), 'files': rows, 'bytes': total})
    record = {'status': 'INCOMPLETE', 'origin_manifest': origin_pin, 'seed_files': len(rows), 'seed_bytes': total}
    try:
        for name, info in rows.items():
            target = SOURCE/'engine'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            write(target, read(SEED/name))
            need(pin(target) == info, 'Snapshot copy mismatch')
        isolated = {}
        for name, expected in origin['source_pins'].items():
            canonical = Path(name)
            relative = canonical.relative_to(ROOT/'engine')
            target = SOURCE/'engine'/relative
            need(pin(canonical)['sha256'] == expected, 'Canonical pin changed before overlay')
            # Destination is this invocation's freshly copied source only.
            with long(target).open('wb') as stream:
                stream.write(read(canonical))
            need(pin(target)['sha256'] == expected, 'Isolated overlay differs')
            isolated[str(target)] = expected
        write_json(BUILD/'source-before.json', isolated)
        target = SOURCE/'engine/apps/durable_world.cpp'
        before = read(target)
        write(BUILD/'durable_world.before.cpp', before)
        needle = b'const auto stats=live.renderer.stats();require(pixels>10000&&stats.debug_errors==0&&stats.debug_warnings==0,"Chapter GPU readback or debug diagnostics failed");'
        need(before.count(needle) == 1, 'Expected one unchanged strict chapter guard')
        after = before.replace(needle, needle.replace(b';require', b';'+INSERTION.encode()+b'require'), 1)
        need(after.replace(INSERTION.encode(), b'', 1) == before, 'Only diagnostic insertion allowed')
        with target.open('wb') as stream:
            stream.write(after)
        write(BUILD/'diagnostic.diff', ''.join(difflib.unified_diff(before.decode().splitlines(True),
            after.decode().splitlines(True), fromfile='canonical/engine/apps/durable_world.cpp',
            tofile='isolated/engine/apps/durable_world.cpp')).encode())
        for name, expected in isolated.items():
            need(pin(Path(name))['sha256'] == (pin(target)['sha256'] if Path(name) == target else expected),
                 'Unexpected isolated source change')
        cmake = Path('C:/Program Files/CMake/bin/cmake.exe')
        run([cmake, '-S', SOURCE/'engine', '-B', BUILD, '-G', 'Visual Studio 17 2022', '-A', 'x64',
            '-DFETCHCONTENT_FULLY_DISCONNECTED=ON', '-DFETCHCONTENT_SOURCE_DIR_JOLTSOURCE=C:/AI-BS/t/r139d01/jolt',
            '-DFETCHCONTENT_SOURCE_DIR_SQLITESOURCE=C:/AI-BS/t/r139d01/sqlite',
            '-DAIBS_AUDIO_DEVICE_TESTS=OFF', '-DAIBS_RECORDING_TESTS=OFF',
            '-DAIBS_EVIDENCE_ROOT='+str(BUILD/'evidence')], 'configure')
        run([cmake, '--build', BUILD, '--config', 'Release', '--target', 'aibs_motherboard', '--parallel', '4'], 'build')
        frozen = BUILD/'frozen_v01'
        frozen.mkdir(); (frozen/'shaders').mkdir()
        artifacts = {}
        for name in origin['artifact_pins']:
            old = Path(name)
            relative = old.relative_to(Path(origin['player']).parent)
            built = BUILD/'Release'/relative if relative.name == 'aibs_motherboard.exe' else BUILD/relative
            target_artifact = frozen/relative
            write(target_artifact, read(built))
            artifacts[str(target_artifact)] = pin(target_artifact)
        sources = {name: pin(Path(name))['sha256'] for name in isolated}
        manifest = {'scope': 'isolated-stderr-diagnostic-only', 'origin_manifest': origin_pin,
            'origin': str(ORIGIN), 'seed_inventory': pin(BUILD/'seed-inventory.json'),
            'changed_path': str(target), 'diagnostic_diff': pin(BUILD/'diagnostic.diff'),
            'preparer': pin(Path(__file__)), 'source_pins': sources, 'canonical_source_pins': origin['source_pins'],
            'artifact_pins': artifacts, 'player': str(frozen/'aibs_motherboard.exe'),
            'player_sha256': artifacts[str(frozen/'aibs_motherboard.exe')]['sha256']}
        write_json(MANIFEST, manifest)
        player, manifest_pin = validate_candidate()
        record.update(status='BUILT_ISOLATED_DIAGNOSTIC_NOT_RUN', player=str(player), manifest=manifest_pin)
    except BaseException as error:
        record.update(status='FAILED_OR_RETAINED', error=str(error))
        raise
    finally:
        record['origin_unchanged'] = validate_origin()[1] == origin_pin
        write_json(BUILD/'preparation.json', record)
        print(record['status'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', required=True)
    parser.parse_args()
    prepare()
