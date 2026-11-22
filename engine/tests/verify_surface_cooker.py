"""Exercise the real typed surface cooker/store CLI using owned synthetic files."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

ASSET_ID = '876721b8-1abe-492a-926f-f5b922d23be9'
OBJ = ('v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\n'
       'usemtl pcb\nf 1/1 2/2 3/3\nusemtl metal\nf 1/1 2/2 3/3\n'
       'usemtl plastic\nf 1/1 2/2 3/3\n')
MATERIALS = 'AIBMAT 2\npcb 1 1 1 0 board.png\nmetal 0.5 0.5 0.5 0 board.png\nplastic 0.1 0.1 0.1 0 -\n'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def png():
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
    pixels = b'\x00'+bytes([10, 150, 30, 255, 30, 200, 50, 255])
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 1, 8, 6, 0, 0, 0))+
            chunk(b'IDAT', zlib.compress(pixels))+chunk(b'IEND', b''))

def verify(executable, report):
    data = {'schema_version': 1, 'status': 'failed', 'checks': [], 'model_inference': False, 'network_download': False}
    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        data['checks'].append(message)
    def run(*args):
        return subprocess.run([str(executable), *map(str, args)], capture_output=True, text=True,
                              encoding='utf-8', errors='replace', check=False, timeout=30)
    try:
        with tempfile.TemporaryDirectory(prefix='aibs-surface-cooker-') as temporary:
            root = Path(temporary)
            source, materials, license_file, image = [root/name for name in ('board.obj', 'board.aibmat', 'rights.txt', 'board.png')]
            source.write_text(OBJ, encoding='utf-8')
            materials.write_text(MATERIALS, encoding='utf-8')
            license_file.write_text('Self-authored synthetic surface regression.\n', encoding='utf-8')
            image.write_bytes(png())
            originals = {p.name: p.read_bytes() for p in (source, materials, license_file, image)}
            def cook(out, *, origin='bottom-left', mat=materials, src=source, extra=()):
                return run('--cook-surface', '--source', src, '--materials', mat, '--asset-id', ASSET_ID,
                           '--name', 'Motherboard surface fixture', '--license', license_file,
                           '--output', out, '--uv-origin', origin, *extra)
            pack = root/'first'
            process = cook(pack)
            check(process.returncode == 0, 'Surface OBJ/AIBMAT2 process cooks successfully: '+process.stderr)
            receipt = json.loads(process.stdout)
            check(receipt['kind'] == 'surface' and receipt['image_count'] == 1, 'Receipt reports typed surface with deduplicated image')
            digest = receipt['sha256']
            check((pack/'catalog.aibcat').read_text() == f'AIBCAT 2\nsurface {ASSET_ID} {digest} {digest}.aibsurf\n', 'Typed catalog uses canonical version, kind and digest basename')
            check({p.name for p in pack.iterdir()} == {digest+'.aibsurf', 'catalog.aibcat', 'LICENSE.txt', 'provenance.json'}, 'Publication contains exactly four immutable files')
            check(sha(pack/(digest+'.aibsurf')) == digest and receipt['decoded_image_bytes'] == 12, 'Cooked digest and decoded mip byte charge match actual2x1 image')
            provenance = json.loads((pack/'provenance.json').read_text())
            check(provenance['schema_version'] == 2 and provenance['options']['uv_origin'] == 'bottom-left', 'Provenance records typed importer and explicit UV origin')
            check(provenance['textures'] == [{'file': 'board.png', 'sha256': sha(image), 'bytes': image.stat().st_size}], 'Texture source bytes are pinned once in provenance')
            check((pack/'LICENSE.txt').read_bytes() == license_file.read_bytes(), 'Supplied rights declaration is copied unchanged')
            snapshot = {p.name: p.read_bytes() for p in pack.iterdir()}
            same = root/'same'
            check(cook(same).returncode == 0 and {p.name: p.read_bytes() for p in same.iterdir()} == snapshot, 'Fresh equivalent cooks are byte deterministic')
            check(cook(pack).returncode != 0 and {p.name: p.read_bytes() for p in pack.iterdir()} == snapshot, 'Existing pack cannot be overwritten')
            top = root/'top'
            check(cook(top, origin='top-left').returncode == 0 and sha(next(top.glob('*.aibsurf'))) != digest, 'Changing explicit UV origin changes cooked surface identity')
            inspected = run('--inspect', pack)
            row = json.loads(inspected.stdout)['assets'][0]
            check(inspected.returncode == 0 and row['kind'] == 'surface' and row['sha256'] == digest and row['triangles'] == 3 and row['materials'] == 3 and row['image_count'] == 1, 'Generic inspect explicitly loads typed surface metadata')
            source.unlink(); image.unlink()
            check(run('--inspect', pack).returncode == 0, 'Inspection depends only on cooked embedded resources, with sources absent')
            source.write_bytes(originals[source.name]); image.write_bytes(originals[image.name])
            store = root/'store'; store.mkdir()
            adopted = run('--adopt', pack, '--store', store)
            reference = json.loads(adopted.stdout)
            ref = [reference[k] for k in ('asset_id', 'asset_sha256', 'pack_sha256')]
            canonical = 'AIBPACK 2\n'+''.join(name+' '+str(len(value))+' '+hashlib.sha256(value).hexdigest()+'\n' for name, value in sorted(snapshot.items()))
            check(adopted.returncode == 0 and reference['pack_sha256'] == hashlib.sha256(canonical.encode()).hexdigest(), 'Adoption pins canonical v2 four-file manifest identity')
            check(run('--inspect-store', store, '--ref', *ref).returncode != 0, 'Legacy profile rejects typed surface dependencies')
            modern = run('--inspect-store', store, '--profile', 'warm-beginning', '--ref', *ref)
            row = json.loads(modern.stdout)['assets'][0]
            check(modern.returncode == 0 and row['asset_id'] == ASSET_ID and row['kind'] == 'surface' and row['image_count'] == 1 and row['decoded_bytes'] > 12, 'Explicit modern store inspection retains identity plus typed/resident metadata')
            closure = root/'closure'
            check(run('--stage-store', store, '--output', closure, '--ref', *ref).returncode != 0 and not closure.exists(), 'Default legacy staging cannot silently admit typed content')
            staged = run('--stage-store', store, '--output', closure, '--profile', 'warm-beginning', '--ref', *ref)
            check(staged.returncode == 0 and json.loads(staged.stdout)['refs'][0] == {k: reference[k] for k in ('asset_id', 'asset_sha256', 'pack_sha256')}, 'Explicit modern staging publishes pinned dependency receipt')
            check(run('--inspect-store', closure, '--profile', 'warm-beginning', '--ref', *ref).returncode == 0, 'Staged typed dependency reopens independently')
            target=pack/(digest+'.aibsurf');saved=target.read_bytes();target.write_bytes(saved+b'corrupt')
            check(run('--inspect', pack).returncode != 0 and run('--adopt', pack, '--store', store).returncode != 0, 'Malformed cooked payload rejects typed inspection and adoption')
            target.write_bytes(saved)
            target=store/reference['pack_sha256']/'LICENSE.txt';saved=target.read_bytes();target.write_bytes(saved+b'changed')
            rejected_closure=root/'corrupt-closure'
            check(run('--inspect-store', store, '--profile', 'warm-beginning', '--ref', *ref).returncode != 0 and
                  run('--stage-store', store, '--output', rejected_closure, '--profile', 'warm-beginning', '--ref', *ref).returncode != 0 and
                  not rejected_closure.exists(), 'Changed pinned license rejects inspection and staging without publication')
            target.write_bytes(saved)
            for filename in ('../board.png', 'sub/board.png', 'sub\\board.png', 'C:\\board.png', 'board.png:stream', 'NUL.png', 'board.jpg'):
                materials.write_text('AIBMAT 2\npcb 1 1 1 0 '+filename+'\nmetal 1 1 1 0 -\nplastic 1 1 1 0 -\n')
                out = root/'rejected'
                before = set(root.iterdir()); rejected = cook(out)
                check(rejected.returncode != 0 and not out.exists() and set(root.iterdir()) == before, 'Unsafe or unsupported texture basename rejects atomically: '+filename)
            materials.write_text(MATERIALS)
            for label, kwargs in [('bad-origin', {'origin': 'automatic'}), ('duplicate-option', {'extra': ('--uv-origin', 'top-left')}), ('unknown-option', {'extra': ('--guess', 'yes')})]:
                out=root/label;check(cook(out, **kwargs).returncode != 0 and not out.exists(), 'Strict surface CLI rejects '+label)
            image.write_bytes(b'not a PNG')
            check(cook(root/'bad-png').returncode != 0 and not (root/'bad-png').exists(), 'Malformed image rejects before publication')
            image.write_bytes(originals[image.name])
            materials.write_text('AIBMAT 1\npcb 1 1 1 0\n')
            check(cook(root/'wrong-material-version').returncode != 0, 'Surface mode requires explicit AIBMAT2')
            materials.write_text(MATERIALS)
            check(run('--inspect-store', store, '--profile', 'auto', '--ref', *ref).returncode != 0 and run('--inspect-store', store, '--profile', 'warm-beginning', '--profile', 'warm-beginning', '--ref', *ref).returncode != 0, 'Unknown or duplicate modern profile rejects')
            check(not list(root.glob('*.assetc-*')), 'All failed cooks leave no owned staging directories')
            check(all(p.read_bytes() == originals[p.name] for p in (source, materials, license_file, image)), 'All original synthetic authoring inputs remain unchanged')
        data['status'] = 'passed'
    except Exception as error:
        data['error_type'], data['error'] = type(error).__name__, str(error)
    data['completed_at'] = datetime.now(timezone.utc).isoformat()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': data['status'], 'checks': len(data['checks']), **({'error': data['error']} if 'error' in data else {})}))
    return 0 if data['status'] == 'passed' else 1

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('executable',type=Path);parser.add_argument('report',type=Path)
    args=parser.parse_args();raise SystemExit(verify(args.executable.resolve(),args.report))
