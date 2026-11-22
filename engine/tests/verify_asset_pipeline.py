"""Exercise cooked-only native geometry/material GPU rendering from a clean package."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

ASSET_ID = '8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264'

def main():
    player, cooker, source, output = (Path(value).resolve() for value in sys.argv[1:])
    output.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='asset-pipeline-', dir=output))
    proof = {'schema_version': 1, 'status': 'failed', 'work_directory': str(run), 'checks': []}
    try:
        package = run / 'standalone'
        (package / 'shaders').mkdir(parents=True)
        shutil.copy2(player, package / player.name)
        shutil.copy2(cooker, package / cooker.name)
        for shader in ('motherboard.vs.cso', 'motherboard.ps.cso'):
            shutil.copy2(player.parent / 'shaders' / shader, package / 'shaders' / shader)
        pack = package / 'cooked'
        result = subprocess.run([str(package / cooker.name), '--source', str(source / 'motherboard.obj'),
            '--materials', str(source / 'motherboard.aibmat'), '--asset-id', ASSET_ID,
            '--name', 'Motherboard cooling assembly', '--license', str(source / 'motherboard-LICENSE.txt'),
            '--output', str(pack)], cwd=package, capture_output=True, timeout=30)
        (run / 'cook.stdout.log').write_bytes(result.stdout)
        (run / 'cook.stderr.log').write_bytes(result.stderr)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        assert (pack / 'catalog.aibcat').is_file()
        assert not any(pack.rglob('*.obj')) and not any(pack.rglob('*.py'))
        proof['checks'].append('Native cooker publishes a cooked-only package, explicit material data and original fixture license')
        capture, report = run / 'asset.bmp', run / 'native.json'
        result = subprocess.run([str(package / player.name), '--asset-showcase', '--asset-root', str(pack),
            '--asset-id', ASSET_ID, '--self-test', '--capture', str(capture), '--report', str(report)],
            cwd=package, capture_output=True, timeout=60)
        (run / 'render.stdout.log').write_bytes(result.stdout)
        (run / 'render.stderr.log').write_bytes(result.stderr)
        assert result.returncode == 0, result.stderr.decode(errors='replace')
        native = json.loads(report.read_text(encoding='utf-8'))
        assert native['status'] == 'passed' and native['asset_id'] == ASSET_ID
        assert native['triangles'] >= 500 and native['materials'] >= 4
        assert native['metrics']['debug_errors'] == 0 and native['metrics']['debug_layer'] is True
        assert native['metrics']['nonbackground_pixels'] > 10000
        assert native['metrics']['asset_gpu_bytes_changed'] > 100
        assert native['metrics']['material_gpu_bytes_changed'] > 100
        assert native['metrics']['camera_input_verified'] is True
        assert native['source_fallback'] is False and native['save_formats_changed'] is False
        assert capture.stat().st_size > 10000
        proof['native'] = native
        proof['checks'].append('Standalone DX12 scene loads verified cooked mesh; actual GPU pixels differ from boxes and material variant')
        proof['checks'].append('Native camera input and debug validation pass; original save formats and collision ownership unchanged')
        # A damaged published dependency must reject; it must never quietly show a source-backed fallback.
        mesh_path = next(pack.glob('*.aibmesh'))
        original = mesh_path.read_bytes()
        damaged = bytearray(original)
        damaged[-1] ^= 1
        mesh_path.write_bytes(damaged)
        rejected_report = run / 'rejected.json'
        result = subprocess.run([str(package / player.name), '--asset-showcase', '--asset-root', str(pack),
            '--asset-id', ASSET_ID, '--self-test', '--capture', str(run / 'rejected.bmp'), '--report', str(rejected_report)],
            cwd=package, capture_output=True, timeout=30)
        assert result.returncode != 0 and not (run / 'rejected.bmp').exists()
        mesh_path.write_bytes(original)
        proof['checks'].append('Tampered cooked mesh rejected before capture without source fallback')
        proof['capture'] = str(capture)
        proof['capture_sha256'] = hashlib.sha256(capture.read_bytes()).hexdigest()
        proof['status'] = 'passed'
    except Exception as exc:
        proof['error'] = str(exc)
    proof['completed_at'] = datetime.now(timezone.utc).isoformat()
    target = run / 'verification.json'
    target.write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': proof['status'], 'report': str(target), 'error': proof.get('error')}, indent=2))
    return 0 if proof['status'] == 'passed' else 1

if __name__ == '__main__':
    raise SystemExit(main())
