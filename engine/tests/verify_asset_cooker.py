"""Real cooker process regression; all authored test inputs live in owned scratch."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile

ASSET_ID = '8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264'
TRIANGLE = 'v 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl copper\nf 1 2 3\n'
MATERIALS = 'AIBMAT 1\ncopper 0.8 0.35 0.05 0\n'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(executable: Path, report: Path):
    data = {'schema_version': 1, 'status': 'failed', 'checks': [],
            'executable': str(executable), 'source_fixture': None,
            'model_inference': False, 'network_download': False}
    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        data['checks'].append(label)
    try:
        check(executable.is_file(), 'Real native asset cooker executable exists')
        with tempfile.TemporaryDirectory(prefix='aibs-assetc-') as temporary:
            root = Path(temporary)
            source, materials, license_path = root/'mesh.obj', root/'mesh.aibmat', root/'LICENSE-input.txt'
            source.write_text(TRIANGLE, encoding='utf-8')
            materials.write_text(MATERIALS, encoding='utf-8')
            license_path.write_text('Self-authored synthetic regression triangle. No third-party source.\n', encoding='utf-8')
            initial = {path: sha(path) for path in (source, materials, license_path)}
            def run(output, *, source_path=source, material_path=materials, license_file=license_path,
                    asset_id=ASSET_ID, name='Synthetic triangle', extra=()):
                arguments = [str(executable), '--source', str(source_path), '--materials', str(material_path),
                    '--asset-id', asset_id, '--name', name, '--license', str(license_file), '--output', str(output), *extra]
                return subprocess.run(arguments, capture_output=True, text=True, encoding='utf-8',
                                      errors='replace', timeout=30, check=False)
            def reject(output, label, **kwargs):
                before = set(root.iterdir())
                process = run(output, **kwargs)
                check(process.returncode != 0 and not output.exists(), label)
                check(set(root.iterdir()) == before, label + ': no orphan staging directory')
            first = root/'first'
            process = run(first)
            check(process.returncode == 0, 'Valid OBJ/material/license process cooks successfully: ' + process.stderr)
            check(Path(json.loads(process.stdout)['output_root']) == first,
                  'Native success reports the actual published pack root')
            catalog = (first/'catalog.aibcat').read_text(encoding='utf-8')
            check(re.fullmatch(r'AIBCAT 1\n' + ASSET_ID + r' ([0-9a-f]{64}) \1\.aibmesh\n', catalog) is not None,
                  'Catalog has canonical identity, cooked SHA256 and digest-based relative filename')
            digest = catalog.splitlines()[1].split()[1]
            cooked = first/(digest+'.aibmesh')
            check(sha(cooked) == digest, 'Catalog digest matches actual immutable cooked bytes')
            check({path.name for path in first.iterdir()} == {digest+'.aibmesh', 'catalog.aibcat', 'LICENSE.txt', 'provenance.json'},
                  'Fresh publication contains exactly cooked mesh, catalog, license and provenance')
            provenance = json.loads((first/'provenance.json').read_text(encoding='utf-8'))
            for key, path in (('source', source), ('materials', materials), ('license', license_path)):
                check(provenance[key]['sha256'] == sha(path) and provenance[key]['bytes'] == path.stat().st_size,
                      key + ' exact bytes and SHA256 retained in provenance')
            check((first/'LICENSE.txt').read_bytes() == license_path.read_bytes(), 'Supplied license copied byte-for-byte')
            check(provenance['asset_id'] == ASSET_ID and provenance['importer']['format_version'] == 1 and
                  provenance['options'] == {'units': 'meters', 'up_axis': '+Y', 'axis_conversion': 'none',
                                             'material_model': 'opaque-base-color-emission-v1',
                                             'external_material_libraries': 'ignored-explicit-material-table-only'},
                  'Provenance states explicit version, units, axis and actual material capability')
            check(provenance['cooked']['file'] == cooked.name and provenance['cooked']['sha256'] == digest,
                  'Provenance binds actual cooked artifact')
            def inspect(pack):
                return subprocess.run([str(executable), '--inspect', str(pack)], capture_output=True,
                                      text=True, encoding='utf-8', errors='replace', timeout=30, check=False)
            inspection = inspect(first)
            inspected = json.loads(inspection.stdout)
            check(inspection.returncode == 0 and inspected['status'] == 'passed' and
                  inspected['assets'] == [{'asset_id': ASSET_ID, 'name': 'Synthetic triangle',
                    'sha256': digest, 'triangles': 1, 'materials': 1}] and len(inspection.stdout.encode('utf-8')) <= 64*1024,
                  'Read-only native inspection validates/decode catalog bytes and returns bounded actual mesh data')
            before_cooked = cooked.read_bytes()
            cooked.write_bytes(before_cooked+b'tampered')
            check(inspect(first).returncode != 0, 'Native inspection rejects tampered cooked bytes')
            cooked.write_bytes(before_cooked)
            check(inspect(first).returncode == 0, 'Inspection succeeds again after exact test-byte restoration')
            def store_command(*arguments):
                return subprocess.run([str(executable), *map(str, arguments)], capture_output=True,
                                      text=True, encoding='utf-8', errors='replace', timeout=30, check=False)
            def ref_arguments(reference):
                return ['--ref', reference['asset_id'], reference['asset_sha256'], reference['pack_sha256']]
            store = root/'project-packs'; store.mkdir()
            original_pack = {p.name: p.read_bytes() for p in first.iterdir()}
            adopted = store_command('--adopt', first, '--store', store)
            adopted_receipt = json.loads(adopted.stdout)
            reference = {key: adopted_receipt[key] for key in ('asset_id', 'asset_sha256', 'pack_sha256')}
            canonical = 'AIBPACK 1\n'+''.join(name+' '+str(len(original_pack[name]))+' '+
                hashlib.sha256(original_pack[name]).hexdigest()+'\n' for name in sorted(original_pack))
            check(adopted.returncode == 0 and adopted_receipt['status'] == 'passed' and
                  reference == {'asset_id': ASSET_ID, 'asset_sha256': digest,
                    'pack_sha256': hashlib.sha256(canonical.encode('ascii')).hexdigest()},
                  'Native adopt pins UUID, mesh digest and canonical all-four-file manifest digest')
            adopted_pack = store/reference['pack_sha256']
            check({p.name: p.read_bytes() for p in adopted_pack.iterdir()} == original_pack and
                  {p.name: p.read_bytes() for p in first.iterdir()} == original_pack,
                  'Adopt copies exact pack bytes while preserving every source file')
            retry = store_command('--adopt', first, '--store', store)
            check(retry.returncode == 0 and json.loads(retry.stdout) == adopted_receipt and len(list(store.iterdir())) == 1,
                  'Exact adoption retry reuses the immutable existing pack')
            inspected_store = store_command('--inspect-store', store, *ref_arguments(reference))
            store_row = json.loads(inspected_store.stdout)['assets'][0]
            check(inspected_store.returncode == 0 and all(store_row[key] == value for key, value in reference.items()) and
                  store_row['name'] == 'Synthetic triangle' and store_row['triangles'] == store_row['materials'] == 1,
                  'Read-only native store inspection loads the pinned asset and actual metadata')
            long_parent = root/('long-project-'+'d'*55)/('dependencies-'+'e'*45)
            long_parent.mkdir(parents=True)
            long_store = long_parent/'packs'; long_store.mkdir()
            long_adopted = store_command('--adopt', first, '--store', long_store)
            check(long_adopted.returncode == 0 and len(str(long_store/reference['pack_sha256']/(digest+'.aibmesh'))) > 260,
                  'Native adoption regression uses a real project dependency file beyond legacy MAX_PATH')
            check(store_command('--inspect-store', long_store, *ref_arguments(reference)).returncode == 0,
                  'Store CLI metadata preflight and native decode both support long immutable dependency paths')
            old_license = (adopted_pack/'LICENSE.txt').read_bytes()
            (adopted_pack/'LICENSE.txt').write_bytes(old_license+b'changed')
            check(store_command('--inspect-store', store, *ref_arguments(reference)).returncode != 0,
                  'Store inspection rejects changed license bytes even when geometry is unchanged')
            check(store_command('--adopt', first, '--store', store).returncode != 0 and
                  (adopted_pack/'LICENSE.txt').read_bytes() == old_license+b'changed',
                  'Adoption rejects corrupt existing pack without repairing or replacing it')
            (adopted_pack/'LICENSE.txt').write_bytes(old_license)
            rights_variant = root/'rights-variant'
            license_path.write_text('Different explicit self-authored synthetic rights declaration.\n', encoding='utf-8')
            check(run(rights_variant).returncode == 0, 'Fresh native cook creates a distinct explicit license/provenance variant')
            license_path.write_text('Self-authored synthetic regression triangle. No third-party source.\n', encoding='utf-8')
            adopted_variant = store_command('--adopt', rights_variant, '--store', store)
            second_reference = {key: json.loads(adopted_variant.stdout)[key] for key in reference}
            check(adopted_variant.returncode == 0 and second_reference['asset_sha256'] == reference['asset_sha256'] and
                  second_reference['pack_sha256'] != reference['pack_sha256'],
                  'Same mesh with different license/provenance receives a distinct immutable pack identity')
            closure = root/'private-closure'
            staged = store_command('--stage-store', store, '--output', closure,
                                   *ref_arguments(reference), *ref_arguments(reference))
            check(staged.returncode == 0 and json.loads(staged.stdout)['refs'] == [reference, reference] and
                  {p.name for p in closure.iterdir()} == {reference['pack_sha256']},
                  'Fresh private snapshot stages the deduplicated dependency closure with exact reference receipt')
            closure_before = {p.relative_to(closure).as_posix(): sha(p) for p in closure.rglob('*') if p.is_file()}
            check(store_command('--stage-store', store, '--output', closure, *ref_arguments(reference)).returncode != 0 and
                  closure_before == {p.relative_to(closure).as_posix(): sha(p) for p in closure.rglob('*') if p.is_file()},
                  'Fresh snapshot mode preserves and rejects an existing destination')
            merged = store_command('--stage-store', store, '--output', closure, *ref_arguments(second_reference), '--merge')
            check(merged.returncode == 0 and {p.name for p in closure.iterdir()} ==
                  {reference['pack_sha256'], second_reference['pack_sha256']} and
                  all(sha(closure/relative) == value for relative, value in closure_before.items()),
                  'Merge publishes only the new immutable dependency and preserves previous snapshot bytes')
            check(store_command('--inspect-store', closure, *ref_arguments(reference), *ref_arguments(second_reference)).returncode == 0,
                  'Staged dependencies reopen independently with both exact pinned references')
            missing_reference = dict(reference, pack_sha256='0'*64)
            failed_store = root/'failed-private-store'
            before_failure = set(root.iterdir())
            check(store_command('--stage-store', store, '--output', failed_store,
                  *ref_arguments(reference), *ref_arguments(missing_reference)).returncode != 0 and
                  not failed_store.exists() and set(root.iterdir()) == before_failure,
                  'Missing dependency rejects fresh closure with no final or orphan staging output')
            invalid_reference = dict(reference, asset_sha256='A'*64)
            check(store_command('--inspect-store', store, *ref_arguments(invalid_reference)).returncode != 0,
                  'Store CLI rejects noncanonical digest syntax before filesystem resolution')
            traversing_store = str(store)+'/../'+store.name
            check(store_command('--inspect-store', traversing_store, *ref_arguments(reference)).returncode != 0 and
                  store_command('--stage-store', traversing_store, '--output', failed_store,
                                *ref_arguments(reference)).returncode != 0 and not failed_store.exists(),
                  'Raw parent traversal rejects before absolute-path normalization in store CLI modes')
            too_many_refs = [part for _ in range(65) for part in ref_arguments(reference)]
            check(store_command('--stage-store', store, '--output', failed_store, *too_many_refs).returncode != 0 and
                  not failed_store.exists(), 'Store CLI rejects more than64 references without publication')
            data['asset_store_reference'] = reference
            many = root/'many-records'; many.mkdir()
            records = []
            for index in range(65):
                uid = f'11111111-1111-4111-8111-{index:012x}'
                fake_digest = hashlib.sha256(str(index).encode('ascii')).hexdigest()
                records.append(f'{uid} {fake_digest} {fake_digest}.aibmesh\n')
            (many/'catalog.aibcat').write_bytes(('AIBCAT 1\n'+''.join(records)).encode('ascii'))
            inspection = inspect(many)
            check(inspection.returncode != 0 and 'at most 64' in inspection.stderr and not inspection.stdout,
                  'CLI rejects catalogs over 64 records before loading assets or emitting partial JSON')
            def declared_variant(pack, uid, encoded_name):
                # AIBMesh1 envelope/leading strings are part of the public file
                # contract. Recompute both checksums to exercise valid decoding
                # followed by CLI JSON limits, rather than corruption rejection.
                payload = before_cooked[48:]
                id_length = struct.unpack_from('<I', payload)[0]
                name_offset = 4+id_length
                name_length = struct.unpack_from('<I', payload, name_offset)[0]
                tail = payload[name_offset+4+name_length:]
                payload = struct.pack('<I', len(uid))+uid.encode('ascii')+struct.pack('<I', len(encoded_name))+encoded_name+tail
                blob = before_cooked[:12]+struct.pack('<I', len(payload))+hashlib.sha256(payload).digest()+payload
                value = hashlib.sha256(blob).hexdigest()
                (pack/(value+'.aibmesh')).write_bytes(blob)
                return f'{uid} {value} {value}.aibmesh\n'
            invalid_text = root/'invalid-json-text'; invalid_text.mkdir()
            record = declared_variant(invalid_text, ASSET_ID, b'\xffinvalid-utf8')
            (invalid_text/'catalog.aibcat').write_bytes(('AIBCAT 1\n'+record).encode('ascii'))
            inspection = inspect(invalid_text)
            check(inspection.returncode != 0 and not inspection.stdout,
                  'Inspection never emits malformed UTF-8 JSON from an otherwise checksummed asset name')
            large_json = root/'large-json'; large_json.mkdir()
            records = [declared_variant(large_json, f'22222222-2222-4222-8222-{index:012x}', b'X'*2048)
                       for index in range(40)]
            (large_json/'catalog.aibcat').write_bytes(('AIBCAT 1\n'+''.join(records)).encode('ascii'))
            inspection = inspect(large_json)
            check(inspection.returncode != 0 and '64 KiB' in inspection.stderr and not inspection.stdout,
                  'Valid decoded long names cannot exceed bounded 64 KiB inspection JSON or emit a partial document')
            second = root/'second'
            check(run(second).returncode == 0 and
                  {p.name: p.read_bytes() for p in first.iterdir()} == {p.name: p.read_bytes() for p in second.iterdir()},
                  'Repeated fresh cooks are byte-for-byte deterministic, including catalog and provenance')
            raced = root/'publication-race'
            race_arguments = [str(executable), '--source', str(source), '--materials', str(materials),
                '--asset-id', ASSET_ID, '--name', 'Synthetic triangle', '--license', str(license_path), '--output', str(raced)]
            racers = [subprocess.Popen(race_arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            try:
                for process in racers:
                    process.communicate(timeout=30)
                check(sorted(process.returncode for process in racers) == [0, 1] and inspect(raced).returncode == 0,
                      'Competing processes publish exactly one valid fresh immutable pack')
                check(not list(root.glob('publication-race.assetc-*')), 'Publication loser removes only its own staging files/directory')
            finally:
                for process in racers:
                    if process.poll() is None:
                        process.kill(); process.wait(timeout=5)
            before = {p.name: sha(p) for p in first.iterdir()}
            check(run(first).returncode != 0 and before == {p.name: sha(p) for p in first.iterdir()},
                  'Existing output pack cannot be overwritten')
            empty = root/'empty-existing'; empty.mkdir()
            check(run(empty).returncode != 0 and not list(empty.iterdir()), 'Even existing empty output is preserved and rejected')
            reject(root/'unknown-option', 'Unknown CLI option rejected', extra=('--unknown', 'value'))
            reject(root/'duplicate-option', 'Duplicate CLI option rejected', extra=('--name', 'duplicate'))
            reject(root/'invalid-id', 'Invalid persistent asset UUID rejected', asset_id='../../not-a-uuid')
            reject(root/'missing-license', 'Missing license input rejected', license_file=root/'missing.txt')
            license_path.write_bytes(b' \r\n\t')
            reject(root/'empty-license', 'Whitespace-only license declaration rejected')
            license_path.write_text('Self-authored synthetic regression triangle. No third-party source.\n', encoding='utf-8')
            for label, text in (
                    ('future-version', 'AIBMAT 2\ncopper 0 0 0 0\n'),
                    ('duplicate-material', MATERIALS + 'copper 0 0 0 0\n'),
                    ('nan-material', 'AIBMAT 1\ncopper nan 0 0 0\n'),
                    ('range-material', 'AIBMAT 1\ncopper 2 0 0 0\n'),
                    ('extra-material-field', 'AIBMAT 1\ncopper 0 0 0 0 extra\n'),
                    ('oversize-name', 'AIBMAT 1\n' + 'x'*65 + ' 0 0 0 0\n')):
                materials.write_text(text, encoding='utf-8')
                reject(root/label, label + ' rejected before publication')
            materials.write_text(MATERIALS, encoding='utf-8')
            source.write_text(TRIANGLE.replace('usemtl copper', 'usemtl missing'), encoding='utf-8')
            reject(root/'missing-material', 'OBJ cannot resolve an undeclared material')
            source.write_text(TRIANGLE + 'mtllib ../../missing.mtl\n', encoding='utf-8')
            ignored_library = root/'inert-library'
            check(run(ignored_library).returncode == 0,
                  'Standard OBJ mtllib metadata is inert; nonexistent external library is never required')
            ignored_receipt = json.loads((ignored_library/'provenance.json').read_text(encoding='utf-8'))
            check(ignored_receipt['materials']['sha256'] == initial[materials] and
                  ignored_receipt['options']['external_material_libraries'] == 'ignored-explicit-material-table-only' and
                  {p.suffix for p in ignored_library.iterdir()} == {'.aibmesh', '.aibcat', '.txt', '.json'},
                  'Explicit material bytes remain authoritative and published pack retains no external dependency')
            source.write_text(TRIANGLE, encoding='utf-8')
            materials.write_bytes(b'X' * (64*1024+1))
            reject(root/'large-materials', 'Oversize material input rejected before read/publication')
            materials.write_text(MATERIALS, encoding='utf-8')
            license_path.write_bytes(b'X' * (64*1024+1))
            reject(root/'large-license', 'Oversize license declaration rejected before read/publication')
            license_path.write_text('Self-authored synthetic regression triangle. No third-party source.\n', encoding='utf-8')
            source.write_bytes(b'X' * (32*1024*1024+1))
            reject(root/'large-source', 'Oversize OBJ input rejected before read/publication')
            source.write_text(TRIANGLE, encoding='utf-8')
            check(all(sha(path) == digest for path, digest in initial.items()), 'All original synthetic inputs preserved after restored rejection fixtures')
            detailed = Path(__file__).resolve().parents[1]/'assets/source/motherboard.obj'
            if detailed.is_file():
                output = root/'detailed'
                process = run(output, source_path=detailed, material_path=detailed.with_suffix('.aibmat'),
                              license_file=detailed.with_name('motherboard-LICENSE.txt'), name='Self-authored motherboard teaching fixture')
                check(process.returncode == 0, 'Self-authored detailed motherboard source cooks through real CLI: ' + process.stderr)
                triangles = sum(line.startswith('f ') for line in detailed.read_text(encoding='utf-8').splitlines())
                check(2500 <= triangles <= 10000, 'Detailed fixture contains thousands of authored triangles')
                data['source_fixture'] = {'path': str(detailed), 'sha256': sha(detailed), 'triangles': triangles}
        data['status'] = 'passed'
    except Exception as error:
        data['error_type'] = type(error).__name__
        data['error'] = str(error)
    data['completed_at'] = datetime.now(timezone.utc).isoformat()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': data['status'], 'checks': len(data['checks']), 'report': str(report),
                      **({'error': data['error']} if 'error' in data else {})}))
    return 0 if data['status'] == 'passed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    raise SystemExit(verify(args.executable.resolve(), args.report))
