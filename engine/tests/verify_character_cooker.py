"""Exercise the real bounded character cook/inspect/store CLI using owned fixtures."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import struct
import subprocess
import uuid
import zlib

ASSET_ID = '9bc23fc4-43d7-4b1e-80d4-e2845569db21'
CLIPS = [(0, 'idle', 'loop'), (1, 'walk', 'loop'), (2, 'catchup', 'loop'), (3, 'guidance', 'once')]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def png():
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    rows = b'\0' + bytes([255, 0, 0, 0, 0, 255, 0, 63]) + b'\0' + bytes([0, 0, 255, 127, 255, 255, 255, 255])
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


def fixture():
    blob = bytearray()
    views, accessors = [], []

    def view(raw):
        blob.extend(b'\0' * ((-len(blob)) % 4))
        result = len(views)
        views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(raw)})
        blob.extend(raw)
        return result

    def accessor(values, kind, component, width, *, limits=None):
        formats = {5126: 'f', 5123: 'H', 5121: 'B'}
        raw = struct.pack('<' + formats[component] * len(values), *values)
        result = len(accessors)
        entry = {'bufferView': view(raw), 'componentType': component, 'count': len(values) // width, 'type': kind}
        if limits:
            entry.update(min=limits[0], max=limits[1])
        accessors.append(entry)
        return result

    position = accessor([-.5, 0, 0, .5, 0, 0, 0, 1, 0], 'VEC3', 5126, 3, limits=([-.5, 0, 0], [.5, 1, 0]))
    normal = accessor([0, 0, -1] * 3, 'VEC3', 5126, 3)
    uv = accessor([0, 1, 1, 1, .5, 0], 'VEC2', 5126, 2)
    joints = accessor([0, 1, 0, 0] * 3, 'VEC4', 5121, 4)
    weights = accessor([.25, .75, 0, 0] * 3, 'VEC4', 5126, 4)
    indices = accessor([0, 2, 1], 'SCALAR', 5123, 1)
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    inverse_child = identity.copy()
    inverse_child[13] = -1
    inverse_bind = accessor(identity + inverse_child, 'MAT4', 5126, 16)
    time = accessor([0, 1], 'SCALAR', 5126, 1, limits=([0], [1]))
    loop_time = accessor([0, .5, 1], 'SCALAR', 5126, 1, limits=([0], [1]))
    animations = []
    for index in range(4):
        angle = .1 * (index + 1)
        rotations = [0, 0, 0, 1, 0, 0, math.sin(angle), math.cos(angle)]
        if index < 3:
            rotations.extend([0, 0, 0, 1])
        rotation = accessor(rotations, 'VEC4', 5126, 4)
        animations.append({'name': 'Source' + str(index), 'samplers': [{'input': loop_time if index < 3 else time, 'output': rotation, 'interpolation': 'LINEAR'}],
                           'channels': [{'sampler': 0, 'target': {'node': 1, 'path': 'rotation'}}]})
    image = png()
    image_view = view(image)
    document = {'asset': {'version': '2.0', 'generator': 'AI-BS synthetic character CLI proof'},
                'scene': 0, 'scenes': [{'nodes': [0, 2]}],
                'nodes': [{'children': [1]}, {'translation': [0, 1, 0]}, {'mesh': 0, 'skin': 0, 'translation': [90, 0, 0]}],
                'skins': [{'skeleton': 0, 'joints': [0, 1], 'inverseBindMatrices': inverse_bind}],
                'meshes': [{'primitives': [{'attributes': {'POSITION': position, 'NORMAL': normal, 'TEXCOORD_0': uv,
                                                           'JOINTS_0': joints, 'WEIGHTS_0': weights}, 'indices': indices, 'material': 0}]}],
                'materials': [{'doubleSided': True, 'alphaMode': 'OPAQUE', 'pbrMetallicRoughness': {
                    'metallicFactor': 0, 'roughnessFactor': 1, 'baseColorFactor': [1, 1, 1, 1], 'baseColorTexture': {'index': 0}}}],
                'textures': [{'sampler': 0, 'source': 0}], 'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}],
                'images': [{'bufferView': image_view, 'mimeType': 'image/png'}],
                'buffers': [{'byteLength': len(blob)}], 'bufferViews': views, 'accessors': accessors, 'animations': animations}
    raw_json = json.dumps(document, separators=(',', ':')).encode()
    raw_json += b' ' * ((-len(raw_json)) % 4)
    binary = bytes(blob) + b'\0' * ((-len(blob)) % 4)
    glb = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(raw_json) + 8 + len(binary)) + struct.pack('<II', len(raw_json), 0x4E4F534A) + raw_json + struct.pack('<II', len(binary), 0x004E4942) + binary
    external = copy.deepcopy(document)
    external['buffers'][0]['uri'] = 'buffers/skin.bin'
    external['images'][0] = {'uri': 'textures/albedo.png', 'mimeType': 'image/png'}
    return glb, json.dumps(external, separators=(',', ':')).encode(), bytes(blob), image


def verify(executable, output):
    executable, output = Path(executable).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output / ('character-cooker-' + str(uuid.uuid4()))
    work.mkdir()
    logs = work / 'logs'
    logs.mkdir()
    report = output / (work.name + '-verification.json')
    result = {'schema_version': 1, 'status': 'failed', 'checks': [], 'work_directory': str(work),
              'family_references_used': False, 'gpu_requested': False, 'model_inference': False, 'network_download': False}
    children = []

    def check(value, message):
        if not value:
            raise AssertionError(message)
        result['checks'].append(message)

    def run(*args):
        label = f'{len(children):03}'
        with (logs / (label + '.stdout.log')).open('xb') as stdout, (logs / (label + '.stderr.log')).open('xb') as stderr:
            child = subprocess.Popen([str(executable), *map(str, args)], stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            children.append(child)
            try:
                code = child.wait(timeout=120)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=15)
        return code, (logs / (label + '.stdout.log')).read_text(encoding='utf-8', errors='replace'), (logs / (label + '.stderr.log')).read_text(encoding='utf-8', errors='replace')

    try:
        glb, gltf, binary, image = fixture()
        sources = work / 'sources'
        sources.mkdir()
        source, external, buffer, texture, license_file = [sources / name for name in ('figure.glb', 'figure.gltf', 'skin.bin', 'albedo.png', 'rights.txt')]
        originals = {source: glb, external: gltf, buffer: binary, texture: image, license_file: b'Self-authored synthetic character fixture. No family references.\n'}
        for path, body in originals.items():
            path.write_bytes(body)

        def cook(pack, *, src=source, clips=CLIPS, resources=(), extra=(), rate=30, rights=license_file):
            args = ['--cook-character', '--source', src, '--asset-id', ASSET_ID, '--name', 'Synthetic articulated guide', '--license', rights, '--output', pack, '--bake-rate', rate]
            for index, name, mode in clips:
                args.extend(['--clip', index, name, mode])
            for uri, path in resources:
                args.extend(['--resource', uri, path])
            return run(*args, *extra)

        pack = work / 'pack'
        code, stdout, stderr = cook(pack)
        check(code == 0, 'Actual character cooker imports strict GLB with four selected clips: ' + stderr)
        receipt = json.loads(stdout)
        check(receipt['kind'] == 'character' and receipt['joint_count'] == 2 and receipt['clip_count'] == 4 and receipt['vertices'] == 3 and receipt['triangles'] == 1, 'Receipt identifies indexed character skeleton and selected animation counts')
        check(receipt['image_count'] == 1 and receipt['decoded_image_bytes'] == 20 and receipt['decoded_bytes'] > 20, 'Opaque PNG produces a complete owned2x2 sRGB mip chain with separate decoded charge')
        checksum = receipt['sha256']
        check((pack / 'catalog.aibcat').read_text() == f'AIBCAT 2\ncharacter {ASSET_ID} {checksum} {checksum}.aibchar\n', 'Canonical typed character catalog and suffix match actual payload digest')
        snapshot = {p.name: p.read_bytes() for p in pack.iterdir()}
        check(set(snapshot) == {checksum + '.aibchar', 'catalog.aibcat', 'LICENSE.txt', 'provenance.json'} and digest(snapshot[checksum + '.aibchar']) == checksum, 'Exactly four immutable pack files contain full cooked checksum identity')
        check(snapshot['LICENSE.txt'] == originals[license_file], 'Rights declaration copied byte-for-byte')
        provenance = json.loads(snapshot['provenance.json'])
        manifest = f'AIBS_GLTF_SOURCE 1\nsource {len(glb)} {digest(glb)}\n'.encode()
        check(provenance['source_manifest']['sha256'] == digest(manifest) and provenance['source'] == {'sha256': digest(glb), 'bytes': len(glb)}, 'Full source-manifest digest covers exact original document bytes')
        check(provenance['options']['clips'] == [{'source_animation': i, 'name': n, 'looping': m == 'loop'} for i, n, m in CLIPS] and provenance['options']['bake_rate'] == 30, 'Provenance records ordered clip selections and explicit bake rate')
        check(provenance['options']['source_skin_to_cooked'] == [0, 1] and len(provenance['options']['baked_intervals_seconds']) == 4 and all(abs(x - 1 / 30) < 1e-14 for x in provenance['options']['baked_intervals_seconds']), 'Actual importer joint remap and uniform bake intervals recorded')
        check(provenance['import_memory']['parser_peak_bytes'] > 0 and provenance['import_memory']['engine_owned_live_upper_bound_bytes'] > 0 and provenance['importer']['commit'] == '360db1a95480fe102ae9c69b27c5d101167ff5ba', 'Pinned importer and scoped actual diagnostics retained')
        check(str(work).encode() not in snapshot['provenance.json'] and str(sources).replace('\\', '/').encode() not in snapshot['provenance.json'] and b'footb' not in snapshot['provenance.json'], 'Provenance contains no automatic absolute host paths')
        check(cook(work / 'same')[0] == 0 and {p.name: p.read_bytes() for p in (work / 'same').iterdir()} == snapshot, 'Equivalent fresh cooks are byte deterministic across output locations')
        check(cook(pack)[0] != 0 and {p.name: p.read_bytes() for p in pack.iterdir()} == snapshot, 'Existing immutable output is preserved on repeated cook')
        code, inspected, error = run('--inspect', pack)
        row = json.loads(inspected)['assets'][0]
        check(code == 0 and row['kind'] == 'character' and row['sha256'] == checksum and row['asset_sha256'] == checksum and row['joint_count'] == 2 and row['clip_count'] == 4, 'Generic inspection reports typed character and complete immutable identity: ' + error)
        source.unlink()
        texture.unlink()
        buffer.unlink()
        check(run('--inspect', pack)[0] == 0, 'A fresh inspector needs only embedded cooked bytes after authoring sources are deleted')
        for path, body in originals.items():
            path.write_bytes(body)
        store = work / 'store'
        store.mkdir()
        code, adopted, error = run('--adopt', pack, '--store', store)
        reference = json.loads(adopted)
        refs = [reference[k] for k in ('asset_id', 'asset_sha256', 'pack_sha256')]
        canonical = 'AIBPACK 2\n' + ''.join(name + ' ' + str(len(body)) + ' ' + digest(body) + '\n' for name, body in sorted(snapshot.items()))
        check(code == 0 and reference['pack_sha256'] == digest(canonical.encode()), 'Adoption pins canonical four-file v2 manifest: ' + error)
        check(run('--inspect-store', store, '--ref', *refs)[0] != 0, 'Legacy inspection rejects character instead of treating it as scenery')
        code, inspected, error = run('--inspect-store', store, '--profile', 'warm-beginning', '--ref', *refs)
        row = json.loads(inspected)['assets'][0]
        check(code == 0 and row['kind'] == 'character' and row['sha256'] == checksum and all(row[k] == reference[k] for k in ('asset_id', 'asset_sha256', 'pack_sha256')), 'Modern store inspection verifies exact requested character reference and metadata: ' + error)
        closure = work / 'closure'
        check(run('--stage-store', store, '--output', closure, '--ref', *refs)[0] != 0 and not closure.exists(), 'Legacy staging rejects character without final publication')
        code, staged, error = run('--stage-store', store, '--output', closure, '--profile', 'warm-beginning', '--ref', *refs)
        check(code == 0 and json.loads(staged)['refs'][0] == {k: reference[k] for k in ('asset_id', 'asset_sha256', 'pack_sha256')}, 'Modern private staging publishes the pinned complete character dependency: ' + error)
        check(run('--inspect-store', closure, '--profile', 'warm-beginning', '--ref', *refs)[0] == 0, 'Staged character pack reopens in an independent process')
        wrong = refs.copy()
        wrong[1] = '0' * 64
        check(run('--inspect-store', store, '--profile', 'warm-beginning', '--ref', *wrong)[0] != 0, 'Typed inspection cannot ignore a mismatching requested immutable reference')
        target = pack / (checksum + '.aibchar')
        target.write_bytes(snapshot[target.name] + b'corrupt')
        check(run('--inspect', pack)[0] != 0 and run('--adopt', pack, '--store', store)[0] != 0, 'Changed cooked bytes reject inspection and adoption')
        target.write_bytes(snapshot[target.name])
        target = store / reference['pack_sha256'] / 'LICENSE.txt'
        target.write_bytes(snapshot['LICENSE.txt'] + b'changed')
        rejected = work / 'corrupt-closure'
        check(run('--inspect-store', store, '--profile', 'warm-beginning', '--ref', *refs)[0] != 0 and run('--stage-store', store, '--output', rejected, '--profile', 'warm-beginning', '--ref', *refs)[0] != 0 and not rejected.exists(), 'Changed pinned rights reject typed loading/staging without publication')
        target.write_bytes(snapshot['LICENSE.txt'])
        resources = [('buffers/skin.bin', buffer), ('textures/albedo.png', texture)]
        extpack = work / 'external-pack'
        code, external_result, error = cook(extpack, src=external, resources=resources)
        check(code == 0, 'JSON glTF imports only explicitly supplied buffer and image resources: ' + error)
        external_provenance = json.loads((extpack / 'provenance.json').read_text())
        canonical = f'AIBS_GLTF_SOURCE 1\nsource {len(gltf)} {digest(gltf)}\n' + ''.join(uri + ' ' + str(path.stat().st_size) + ' ' + digest(path.read_bytes()) + '\n' for uri, path in resources)
        check(external_provenance['source_manifest']['sha256'] == digest(canonical.encode()), 'External document, URI, resource lengths and actual hashes all enter the source identity')
        check(cook(work / 'reversed-resources', src=external, resources=list(reversed(resources)))[0] == 0 and {p.name: p.read_bytes() for p in (work / 'reversed-resources').iterdir()} == {p.name: p.read_bytes() for p in extpack.iterdir()}, 'Explicit resource order does not change canonical cooked bytes or provenance')
        check(cook(work / 'missing-resources', src=external)[0] != 0 and not (work / 'missing-resources').exists(), 'No implicit glTF filesystem fallback exists beside source')
        for label, kwargs in [('duplicate-option', {'extra': ('--name', 'duplicate')}), ('unknown-option', {'extra': ('--auto-import', 'yes')}), ('bad-loop', {'clips': [(0, 'idle', 'automatic')]}), ('duplicate-clip-name', {'clips': [(0, 'idle', 'loop'), (1, 'idle', 'once')]}), ('bad-rate', {'rate': 61}), ('negative-rate', {'rate': -1}), ('missing-value', {'extra': ('--resource', 'incomplete')}), ('duplicate-resource', {'src': external, 'resources': resources + [resources[0]]}), ('bad-uri', {'src': external, 'resources': [('../skin.bin', buffer)]}), ('extra-glb-resource', {'resources': [('unused.bin', buffer)]})]:
            destination = work / label
            check(cook(destination, **kwargs)[0] != 0 and not destination.exists(), 'Strict character CLI rejects ' + label + ' before publication')
        for label, raw in [('empty-rights', b''), ('nul-rights', b'rights\0bad'), ('invalid-utf8-rights', b'\xff'), ('oversized-rights', b'x' * (65536 + 1))]:
            license_file.write_bytes(raw)
            destination = work / label
            check(cook(destination)[0] != 0 and not destination.exists(), 'Explicit UTF-8 rights policy rejects ' + label)
        license_file.write_bytes(originals[license_file])
        source.write_bytes(b'not a glTF source')
        check(cook(work / 'bad-source')[0] != 0 and not (work / 'bad-source').exists(), 'Malformed source leaves no partial output')
        source.write_bytes(originals[source])
        huge = sources / 'too-large.bin'
        with huge.open('wb') as stream:
            stream.seek(32 * 1024 * 1024)
            stream.write(b'\0')
        check(cook(work / 'oversized-source', src=huge)[0] != 0 and not (work / 'oversized-source').exists(), 'Source length is bounded before memory allocation')
        check(cook(work / 'oversized-closure', src=external, resources=[('buffers/skin.bin', huge), ('textures/albedo.png', texture)])[0] != 0 and not (work / 'oversized-closure').exists(), 'Aggregate source/resource byte budget rejects before publication')
        check(not list(work.glob('*.assetc-*')), 'All rejected requests leave no owned staging directories')
        check(all(path.read_bytes() == body for path, body in originals.items()), 'Synthetic authoring sources and rights remain unchanged after all rejection cases')
        result['status'] = 'passed'
        result['executable_sha256'] = digest(executable.read_bytes())
        result['source_sha256'] = digest(Path(__file__).read_bytes())
    except Exception as error:
        result['error_type'], result['error'] = type(error).__name__, str(error)
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=15)
        result['processes_joined'] = all(child.poll() is not None for child in children)
        result['process_count'] = len(children)
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'report': str(report), 'checks': len(result['checks']), **({'error': result['error']} if 'error' in result else {})}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raise SystemExit(verify(args.executable, args.output))
