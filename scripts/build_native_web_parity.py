"""Stage and build a pure Qt Windows client with an explicit deployed-web baseline.

This is an internal parity candidate, not a completed parity or signed release.
It never imports application modules while staging, includes no backend package,
and does not launch the result, sign it, or invoke a legacy release script.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

# These immutable artifacts passed the complete LIVE file readback. A new web
# release needs a new reviewed admission, rather than merely accepting its label.
VERIFIED_WEB_BASELINE = {
    'sourceVersion': 'v5.329.52',
    'buildId': 'web-v5-329-52-c897be2867ed',
    'count': 189,
    'origin': 'https://ai-bs-dashboard.web.app',
    'manifestSha256': '88906ac960bcdd7d40337737c8b3634ed32d7bb996776bb103a09c70c476b8a2',
    'verificationSha256': '18ba3da843a869118903a5778b0503a10f18ff2388aaa6d1a03327ca4cde68dd',
}


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def checked_file(file: Path, boundary: Path) -> Path:
    if file.is_symlink():
        raise ValueError('Linked source file is not admitted')
    file = file.resolve(strict=True)
    file.relative_to(boundary.resolve(strict=True))
    if not file.is_file() or file.is_symlink():
        raise ValueError('Regular bounded source file required')
    return file


def native_modules() -> list[str]:
    """Resolve literal native imports without importing or running the application."""
    prior = ast.parse((ROOT / 'native_studio/AI_BS_Studio.spec').read_text(encoding='utf-8-sig'))
    names = {'native_studio', 'native_studio.app', 'native_studio.runtime_policy'}
    for node in ast.walk(prior):
        if isinstance(node, ast.keyword) and node.arg == 'hiddenimports':
            names.update(x for x in ast.literal_eval(node.value) if x.startswith('native_studio.'))
    scanned: set[str] = set()
    while names - scanned:
        name = sorted(names - scanned)[0]
        relative = 'native_studio/__init__.py' if name == 'native_studio' else name.replace('.', '/') + '.py'
        file = checked_file(ROOT / relative, ROOT / 'native_studio')
        tree = ast.parse(file.read_text(encoding='utf-8-sig'), filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('native_studio.'):
                names.add(node.module)
            elif isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names if alias.name.startswith('native_studio.'))
        scanned.add(name)
    if any(any(part.startswith(('test_', 'sign_', 'scratch_', 'build_')) for part in name.split('.')) for name in names):
        raise ValueError('Developer/signing scripts must not enter the application graph')
    return sorted(names)


def admit_web_baseline(web_manifest: Path) -> tuple[dict, str]:
    web_manifest = checked_file(web_manifest, ROOT / 'backups')
    proof_file = checked_file(web_manifest.with_name('live_verification.json'), ROOT / 'backups')
    trusted = VERIFIED_WEB_BASELINE
    if digest(web_manifest) != trusted['manifestSha256'] or digest(proof_file) != trusted['verificationSha256']:
        raise ValueError('Exact reviewed web artifact and LIVE verification bytes are required')
    web = json.loads(web_manifest.read_text(encoding='utf-8'))
    proof = json.loads(proof_file.read_text(encoding='utf-8'))
    if any(web.get(k) != trusted[k] or proof.get(k) != trusted[k] for k in ('sourceVersion', 'buildId', 'count')):
        raise ValueError('The actual verified web baseline is required')
    if (proof.get('origin') != trusted['origin'] or proof.get('passed') != trusted['count'] or
            proof.get('failed') != 0 or proof.get('versionMatch') is not True):
        raise ValueError('Complete successful LIVE verification is required')
    expected = {row['relative']: row for row in web['files']}
    observed = {row['relative']: row for row in proof['files']}
    if len(expected) != trusted['count'] or len(web['files']) != len(expected) or set(expected) != set(observed) or len(proof['files']) != len(observed):
        raise ValueError('Every unique hosted file must have exact readback proof')
    for name, row in expected.items():
        actual = observed[name]
        if (actual.get('status') != 200 or actual.get('match') is not True or
                actual.get('bytes') != row['bytes'] or actual.get('sha256') != row['sha256'] or
                actual.get('expectedSha256') != row['sha256']):
            raise ValueError('Hosted file proof differs from the reviewed artifact')
    if not proof.get('excludedProbes') or any(row.get('notPublished') is not True for row in proof['excludedProbes']):
        raise ValueError('Private hosting exclusions must remain verified')
    return web, digest(proof_file)


def stage(destination: Path, web_manifest: Path) -> dict:
    destination = destination.resolve()
    destination.relative_to((ROOT / 'backups').resolve())
    if destination.exists():
        raise ValueError('Retain existing attempts; a fresh staging directory is required')
    web_manifest = checked_file(web_manifest, ROOT / 'backups')
    web, verification_sha256 = admit_web_baseline(web_manifest)
    version = (ROOT / 'version.txt').read_text(encoding='utf-8').strip().removeprefix('v')
    parts = version.split('.')
    if len(parts) != 3 or any(not s.isdecimal() or int(s) > 65535 for s in parts):
        raise ValueError('Windows-compatible source version required')
    destination.mkdir()
    source = destination / 'source'
    source.mkdir()
    rows = []
    modules = native_modules()
    for name in modules:
        relative = 'native_studio/__init__.py' if name == 'native_studio' else name.replace('.', '/') + '.py'
        original = checked_file(ROOT / relative, ROOT / 'native_studio')
        out = source / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        before = digest(original)
        shutil.copyfile(original, out)
        if digest(out) != before or digest(original) != before:
            raise ValueError('Concurrent source change during freeze')
        rows.append({'relative': relative, 'bytes': out.stat().st_size, 'sha256': before})
    for original, relative in [(ROOT / 'version.txt', 'version.txt'), (ROOT / 'frontend/public/psychedelic_theme.jpg', 'assets/psychedelic_theme.jpg'), (ROOT / 'frontend/public/favicon.ico', 'assets/favicon.ico')]:
        original = checked_file(original, ROOT)
        out = source / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, out)
        if digest(original) != digest(out):
            raise ValueError('Resource readback mismatch')
        rows.append({'relative': relative, 'bytes': out.stat().st_size, 'sha256': digest(out)})
    baseline = {'schema': 1, 'artifact_scope': 'windows-pure-qt-parity-candidate', 'source_version': 'v' + version, 'web_version': web['sourceVersion'], 'web_build_id': web['buildId'], 'web_manifest_sha256': digest(web_manifest), 'web_verification_sha256': verification_sha256, 'web_url': VERIFIED_WEB_BASELINE['origin'], 'parity_verified': False, 'signing': 'NOT_SIGNED', 'backend_bundled': False, 'requires_existing_services': True, 'isolated_execution_available': False}
    (source / 'web_baseline.json').write_text(json.dumps(baseline, indent=2), encoding='utf-8')
    rows.append({'relative': 'web_baseline.json', 'bytes': (source / 'web_baseline.json').stat().st_size, 'sha256': digest(source / 'web_baseline.json')})
    # Construct a new spec; no original spec, signer, broad backend path or old binary is executed.
    spec = f'''from pathlib import Path
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
source = Path({str(source)!r})
version = {version!r}
pe_version = {tuple(map(int, parts)) + (0,)!r}
info = VSVersionInfo(ffi=FixedFileInfo(filevers=pe_version, prodvers=pe_version, mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)), kids=[StringFileInfo([StringTable('040904b0', [StringStruct('CompanyName','Stehouwer Publishing'), StringStruct('FileDescription','AI-BS Sovereign Studio'), StringStruct('FileVersion',version), StringStruct('ProductVersion',version), StringStruct('ProductName','AI-BS Sovereign Studio'), StringStruct('OriginalFilename','AI_BS_Studio.exe')])]), VarFileInfo([VarStruct('Translation',[1033,1200])])])
a = Analysis([str(source/'native_studio/app.py')], pathex=[str(source)], binaries=[], datas=[(str(source/'version.txt'),'.'),(str(source/'web_baseline.json'),'.'),(str(source/'assets/psychedelic_theme.jpg'),'assets')], hiddenimports={modules!r}, hookspath=[], hooksconfig={{}}, runtime_hooks=[], excludes=['backend','PyQt5','PySide2','PySide6','tkinter','IPython','notebook','torch','tensorflow','transformers','sentence_transformers','chromadb'], noarchive=False)
for name, file, kind in a.pure:
    if name == 'backend' or name.startswith('backend.'):
        raise ValueError('Backend package must not be bundled in the native client')
    # PyInstaller uses '-' for namespace packages; it is not a filesystem input.
    namespace_package = file == '-' and kind == 'PYMODULE'
    if file and not namespace_package and Path(file).resolve().is_relative_to(Path({str(ROOT)!r})) and not Path(file).resolve().is_relative_to(source):
        raise ValueError('Repository module outside frozen native source')
for name, file, kind in list(a.datas) + list(a.binaries):
    if kind in {{'BINARY','EXTENSION','DATA'}} and not any(Path(file).resolve().is_relative_to(base) for base in [source,Path({str(destination / 'work')!r}),Path({str(Path(sys.executable).parent.resolve())!r}),Path({str(Path(os.environ.get('SystemRoot', 'C:/Windows')).resolve())!r})]):
        raise ValueError('Native dependency outside Python/Windows/frozen build roots')
    suffix = Path(name).suffix.lower()
    standard_library_zip = name == 'base_library.zip' and Path(file).resolve().is_relative_to(Path({str(destination / 'work')!r}))
    public_ca_bundle = name.replace('\\\\','/').endswith('certifi/cacert.pem') and not Path(file).resolve().is_relative_to(Path({str(ROOT)!r})) and b'PRIVATE KEY' not in Path(file).read_bytes() and b'BEGIN CERTIFICATE' in Path(file).read_bytes()
    if (suffix in {{'.db','.sqlite','.sqlite3','.pfx','.p12','.key','.iso'}} or suffix == '.zip' and not standard_library_zip or suffix == '.pem' and not public_ca_bundle) or Path(name).name in {{'.env','AGENTS.md','CODEX_HANDOFF.md'}}:
        raise ValueError('Private/store/archive material is not native client data')
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='AI_BS_Studio', version=info, icon=str(source/'assets/favicon.ico'), debug=False, strip=False, upx=False, console=False, uac_admin=False)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='AI_BS_Studio')
'''
    ast.parse(spec)
    (destination / 'AI_BS_WebParity.spec').write_text(spec, encoding='utf-8')
    plan = {'schema': 1, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'root': str(destination), 'sourceVersion': 'v' + version, 'webBaseline': baseline, 'modules': modules, 'files': rows, 'builderSha256': digest(Path(__file__)), 'specSha256': digest(destination / 'AI_BS_WebParity.spec'), 'applicationExecuted': False, 'signed': False, 'requiresElevation': False}
    (destination / 'plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    return plan


def build(destination: Path) -> int:
    destination = destination.resolve(strict=True)
    destination.relative_to((ROOT / 'backups').resolve())
    plan = json.loads((destination / 'plan.json').read_text(encoding='utf-8'))
    if plan.get('builderSha256') != digest(Path(__file__)):
        raise ValueError('Build orchestration changed after staging')
    if plan['root'] != str(destination) or any((destination / name).exists() for name in ['dist', 'work', 'build_result.json']):
        raise ValueError('Fresh admitted plan required; preserve previous attempts')
    for row in plan['files']:
        if digest(checked_file(destination / 'source' / row['relative'], destination / 'source')) != row['sha256']:
            raise ValueError('Frozen build input changed')
    if digest(destination / 'AI_BS_WebParity.spec') != plan['specSha256']:
        raise ValueError('Frozen spec changed')
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', str(destination / 'dist'), '--workpath', str(destination / 'work'), '--log-level', 'INFO', str(destination / 'AI_BS_WebParity.spec')]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    environment = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'} and not k.upper().endswith(('TOKEN','PASSWORD','SECRET','API_KEY','ADMIN_KEY'))}
    python_root = Path(sys.executable).resolve().parent
    windows_root = Path(os.environ.get('SystemRoot', 'C:/Windows')).resolve(strict=True)
    environment['PATH'] = os.pathsep.join(map(str, [python_root, python_root / 'Scripts', windows_root / 'System32', windows_root]))
    for name in ['QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH']:
        environment.pop(name, None)
    timed_out = False
    with (destination / 'build_stdout.local.txt').open('xb') as stdout, (destination / 'build_stderr.local.txt').open('xb') as stderr:
        try:
            result = subprocess.run(args, cwd=destination, env=environment, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW, timeout=600)
            code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out, code = True, 124
    receipt = {'started': started, 'finished': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exit': code, 'timedOut': timed_out, 'applicationExecuted': False, 'signed': False, 'planSha256': digest(destination / 'plan.json')}
    (destination / 'build_result.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['stage', 'build'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--web-manifest', type=Path)
    args = parser.parse_args()
    if args.mode == 'build':
        return build(args.output)
    if not args.web_manifest:
        parser.error('stage requires --web-manifest')
    plan = stage(args.output, args.web_manifest)
    print(json.dumps({'sourceVersion': plan['sourceVersion'], 'modules': len(plan['modules']), 'frozenFiles': len(plan['files']), 'output': plan['root'], 'applicationExecuted': False, 'signed': False, 'parityVerified': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
