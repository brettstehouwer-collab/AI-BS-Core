"""Controlled Prop01 Blender-to-private-SDK proof in a new output directory.

No build, install, profile update, real game save, provider call or deployment.
Requires the separately retained reviewed Blender5.3 and private SDK174 tools.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

import psutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('D:/AI-BS-Game-Resources/Prop01_Implementation_20261104_v01/asset_v01')
SDK = Path('D:/AI-BS-Game-Resources/P110/SDK174Recovery/sdk-preview-release/bin')
NATIVE = Path('D:/AI-BS-Game-Resources/Prop01_Native_Acceptance_20261105/build/Release')
SEED = Path('C:/Users/footb/.codex/visualizations/2026/11/01/01a19491-7a5c-71e0-a6ba-0dc4a3f58f44/prop01_implementation_20261104/native/cpu_compound_v03')
BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.3/blender.exe')
PINS = {
    SDK / 'aibs_assetc.exe': 'f2c4ed2cbbc5c570cd56c699fa3c2a4b5787e675f91c82c46792bebca4e9700f',
    NATIVE / 'prop01_native_acceptance.exe': '79778605d00964e4e4cf7349b1d352cf80cf7fc38a3fd9fc332073a58275bdd8',
    NATIVE / 'prop01_gpu_acceptance.exe': '8aad645aebce9f25c56a81a9d0c34882d5c743c6cd466e9bd8de36a3f10e4778',
}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def plain(path):
    for item in (path, *path.parents):
        if item.exists():
            require(not item.is_symlink() and not item.lstat().st_file_attributes & 0x400,
                    'Linked qualification paths are not supported')


def sha(path):
    plain(path)
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def protected():
    result = {}
    for tree in (SOURCE, SEED, ROOT / 'runtime/devtools/blender-rtx/profile', SDK / 'shaders'):
        require(tree.is_dir(), 'Required preserved input directory is missing')
        plain(tree)
        for path in tree.rglob('*'):
            plain(path)
            if path.is_file():
                result[str(path)] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--coordinate-convention', required=True,
                        choices=('legacy-rotation', 'dx12-left-handed'))
    args = parser.parse_args()
    output = args.output.absolute()
    require(output.parent == Path('D:/AI-BS-Game-Resources/RTX_Variants_20261111') and
            output.parent.is_dir() and not output.exists(), 'Use a NEW variant run under the reviewed RTX directory')
    plain(output)
    for path, expected in PINS.items():
        require(sha(path) == expected, 'Private native tool identity changed')
    before = protected()
    output.mkdir()
    (output / 'protected-before.private.json').write_text(json.dumps(before, indent=2), encoding='utf8')
    exporter = ROOT / 'engine/tools/export_blender_rtx_variant.py'
    report = {'schema': 1, 'utc': datetime.now(timezone.utc).isoformat(), 'status': 'RUNNING',
              'coordinate_convention': args.coordinate_convention, 'processes': [],
              'tool_pins': {str(p): sha(p) for p in (*PINS, BLENDER, exporter, Path(__file__).resolve())},
              'scope': 'Controlled named Prop01 variant and pinned privateSDK174 CPU/DX12 proof; not current-player, installed, performance or release qualification'}
    env = {key: value for key, value in os.environ.items() if key.upper() in {
        'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'APPDATA', 'LOCALAPPDATA', 'USERPROFILE'}}
    for key in ('CONFIG', 'SCRIPTS', 'DATAFILES', 'EXTENSIONS'):
        env['BLENDER_USER_' + key] = str(ROOT / 'runtime/devtools/blender-rtx/profile' / key.lower())
    env.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen')

    def save():
        (output / 'acceptance.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')

    def run(label, command):
        report['stage'] = label
        save()
        print('STAGE ' + label, flush=True)
        with (output / (label + '.stdout.log')).open('xb') as stdout, (output / (label + '.stderr.log')).open('xb') as stderr:
            child = subprocess.Popen([str(arg) for arg in command], cwd=ROOT, env=env,
                                     stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            state = {'stage': label, 'pid': child.pid, 'created': psutil.Process(child.pid).create_time(),
                     'terminal': False}
            report['processes'].append(state)
            save()
            # A deadline retains the exact live identity; it never kills work or
            # authorizes a duplicate run. Diagnose that child before continuing.
            code = child.wait(timeout=180)
            state.update(terminal=True, exit_code=code)
            save()
            require(code == 0, label + ' failed; retained output must be diagnosed before a new attempt')

    def passed(folder, name):
        data = json.loads((folder / name).read_text(encoding='utf8'))
        require(data['status'] in ('PASS', 'passed'), name + ' did not pass')
        report[name] = {key: value for key, value in data.items() if key != 'checks'}
        if 'checks' in data:
            report[name]['assertion_count'] = len(data['checks'])
        return data

    try:
        prefix = [BLENDER, '--background', '--factory-startup', '--disable-autoexec',
                  '--python-exit-code', '1', '--python', exporter, '--']
        run('blender_export', [*prefix, '--source', SOURCE / 'Prop01_Clean_Game_Master.blend',
                              '--output', output / 'variant', '--coordinate-convention', args.coordinate_convention])
        run('blender_reimport', [*prefix, '--verify', output / 'variant'])
        passed(output / 'variant', 'fresh_reimport_verification.json')
        manifest = json.loads((output / 'variant/variant_manifest.json').read_text(encoding='utf8'))
        require(manifest['coordinate_convention'] == args.coordinate_convention, 'Wrong exported coordinate convention')
        for role in ('hero', 'repeated'):
            pack = output / ('cooked_' + role)
            run('cook_' + role, [SDK / 'aibs_assetc.exe', '--cook-surface', '--source', manifest['native_obj'],
                                '--materials', manifest[role + '_aibmat'], '--asset-id', manifest[role + '_asset_id'],
                                '--name', 'Prop01 RTX ' + args.coordinate_convention + ' ' + role,
                                '--license', manifest['license'], '--output', pack, '--uv-origin', 'bottom-left'])
            run('inspect_' + role, [SDK / 'aibs_assetc.exe', '--inspect', pack])
        # The consumer deliberately moves +1.5m and retains it after Redo/Save.
        # Start at-24 so its final placement matches the GPU probe's-22.5 camera.
        run('native_create', [NATIVE / 'prop01_native_acceptance.exe', '--pack', output / 'cooked_hero',
                             '--output', output / 'cpu', '--base-content', SEED / 'base.aibd',
                             '--base-store', SEED / 'project/assets/packs', '--x', '-24', '--y', '.085', '--z', '-23'])
        run('native_reopen', [NATIVE / 'prop01_native_acceptance.exe', '--reopen', output / 'cpu'])
        created = passed(output / 'cpu', 'create-verification.json')
        passed(output / 'cpu', 'reopen-verification.json')
        require(all(part['center'][0] == -22.5 for part in created['proxy_parts']), 'GPU fixture final position mismatch')
        run('gpu_create', [NATIVE / 'prop01_gpu_acceptance.exe', '--verify-and-repair', '--source-v03', output / 'cpu',
                           '--hero-pack', output / 'cooked_hero', '--repeated-pack', output / 'cooked_repeated',
                           '--shaders', SDK / 'shaders', '--output', output / 'gpu'])
        run('gpu_reopen', [NATIVE / 'prop01_gpu_acceptance.exe', '--reopen-verify', '--output', output / 'gpu',
                           '--shaders', SDK / 'shaders'])
        passed(output / 'gpu', 'gpu-create-verification.json')
        passed(output / 'gpu', 'gpu-reopen-verification.json')
        require(all(sha(Path(path)) == value for path, value in report['tool_pins'].items()), 'Tool bytes changed during proof')
        report['status'] = 'PASS_CONTROLLED_BLENDER_NATIVE_PIPELINE_ART_REVIEW_PENDING'
    except BaseException as error:
        report.update(status='INCOMPLETE', failure_class=type(error).__name__)
        raise
    finally:
        report['protected_existing_files'] = len(before)
        report['protected_files_unchanged'] = protected() == before
        save()
        print(json.dumps({'status': report['status'], 'output': str(output),
                          'protected_files_unchanged': report['protected_files_unchanged']}), flush=True)
        require(report['protected_files_unchanged'], 'Protected source delta requires investigation; no rollback applied')


if __name__ == '__main__':
    main()
