"""Real audio cooker/store CLI proof using only generated synthetic PCM."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import struct
import subprocess
import uuid

ASSET_ID = '265a23aa-7368-470a-80e0-934643b328e2'


def digest(body):
    return hashlib.sha256(body).hexdigest()


def wav(pcm):
    fmt = struct.pack('<HHIIHH', 1, 2, 44100, 176400, 4, 16)
    body = b'WAVE' + b'JUNK' + struct.pack('<I', 3) + b'xyz\0' + b'fmt ' + struct.pack('<I', 16) + fmt
    body += b'data' + struct.pack('<I', len(pcm)) + pcm
    return b'RIFF' + struct.pack('<I', len(body)) + body


def verify(executable, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output / ('audio-cooker-' + str(uuid.uuid4()))
    work.mkdir()
    checks = []
    logs = []
    result = {'status': 'failed', 'work_directory': str(work), 'family_media_copied': False}

    def check(value, message):
        if not value:
            raise AssertionError(message)
        checks.append(message)

    def run(*args, success=True):
        child = subprocess.run([str(Path(executable).resolve()), *map(str, args)], capture_output=True, timeout=180,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        label = f'{len(logs):03}'
        (work / (label + '.stdout.log')).write_bytes(child.stdout)
        (work / (label + '.stderr.log')).write_bytes(child.stderr)
        logs.append({'arguments': list(map(str, args)), 'exit_code': child.returncode})
        check((child.returncode == 0) == success, 'Expected real process result for ' + str(args[0]))
        return json.loads(child.stdout) if success else None

    def parse_pcm(encoded):
        check(encoded[:12] == b'AIBAudio2\0\0\0', 'Typed audio magic/reserved bytes')
        check(struct.unpack_from('<II', encoded, 12) == (2, len(encoded) - 52), 'Exact audio version/body size')
        check(encoded[20:52] == hashlib.sha256(encoded[52:]).digest(), 'Independent body checksum')
        offset = 52
        strings = []
        for _ in range(3):
            length, = struct.unpack_from('<I', encoded, offset)
            offset += 4
            strings.append(encoded[offset:offset + length].decode('utf-8'))
            offset += length
        rate, channels, bits, reserved, frames, count = struct.unpack_from('<IIIIQQ', encoded, offset)
        offset += 32
        check((rate, channels, bits, reserved, frames, count) == (44100, 2, 16, 0, 8684544, 34738176),
              'Source rate/stereo/full196.928-second frame count preserved')
        pcm = encoded[offset:offset + count]
        offset += count
        check(encoded[offset:] == struct.pack('<II', 0, 0), 'WAV import has empty draft caption state')
        return strings, pcm

    try:
        pcm = bytes(range(256)) * (34738176 // 256)
        check(len(pcm) == 34738176, 'Large synthetic PCM fixture exceeds33MiB')
        source_bytes = wav(pcm)
        source = work / 'source.wav'
        source.write_bytes(source_bytes)
        license_path = work / 'rights.txt'
        license_bytes = b'Self-authored synthetic PCM fixture; no family media or third-party rights.\n'
        license_path.write_bytes(license_bytes)
        output_pack = work / 'cooked'
        arguments = ['--cook-audio', '--source', source, '--asset-id', ASSET_ID, '--name', 'Synthetic full source memory',
                     '--license', license_path, '--output', output_pack]
        receipt = run(*arguments)
        check(receipt['kind'] == 'audio' and receipt['sample_rate'] == 44100 and receipt['channels'] == 2,
              'Cook success receipt identifies audio source format')
        check(receipt['frame_count'] == 8684544 and receipt['pcm_bytes'] == len(pcm), 'Cook receipt counts complete PCM')
        names = {path.name for path in output_pack.iterdir()}
        filename = receipt['sha256'] + '.aibaud'
        check(names == {'catalog.aibcat', 'LICENSE.txt', 'provenance.json', filename}, 'Exact four-file typed pack')
        check(len(filename) == 71, 'Audio payload suffix is seven bytes, not legacy eight')
        encoded = (output_pack / filename).read_bytes()
        check(digest(encoded) == receipt['sha256'], 'Independent complete cooked-file SHA256')
        strings, cooked_pcm = parse_pcm(encoded)
        check(strings == [ASSET_ID, 'Synthetic full source memory', digest(source_bytes)], 'Whole RIFF source SHA includes skipped JUNK')
        check(cooked_pcm == pcm, 'Independent parsed PCM bytes equal complete original generated source')
        check((output_pack / 'LICENSE.txt').read_bytes() == license_bytes, 'Rights declaration preserved verbatim')
        provenance_bytes = (output_pack / 'provenance.json').read_bytes()
        provenance = json.loads(provenance_bytes)
        check(provenance['source'] == {'sha256': digest(source_bytes), 'bytes': len(source_bytes)}, 'Complete WAV provenance hash/length')
        check(str(source).encode() not in provenance_bytes and str(work).encode() not in provenance_bytes
              and b'source_path' not in provenance_bytes, 'No host paths embedded in provenance')
        inspected = run('--inspect', output_pack)['assets'][0]
        check(inspected['kind'] == 'audio' and inspected['frame_count'] == 8684544, 'Generic typed CLI inspection handles audio')
        store = work / 'store'
        store.mkdir()
        adopted = run('--adopt', output_pack, '--store', store)
        expected_manifest = 'AIBPACK 2\n' + ''.join(
            name + ' ' + str((output_pack / name).stat().st_size) + ' ' + digest((output_pack / name).read_bytes()) + '\n'
            for name in sorted(names))
        check(adopted['pack_sha256'] == digest(expected_manifest.encode()), 'Independent complete four-file pack identity')
        reference = ['--ref', adopted['asset_id'], adopted['asset_sha256'], adopted['pack_sha256']]
        run('--inspect-store', store, *reference, success=False)
        modern = run('--inspect-store', store, '--profile', 'warm-beginning', *reference)
        check(modern['assets'][0]['kind'] == 'audio' and modern['assets'][0]['pcm_bytes'] == len(pcm), 'Modern inspection retains whole audio')
        run('--stage-store', store, '--output', work / 'legacy', *reference, success=False)
        check(not (work / 'legacy').exists(), 'Rejected legacy staging leaves no final directory')
        staged = work / 'private'
        run('--stage-store', store, '--output', staged, '--profile', 'warm-beginning', *reference)
        check((staged / adopted['pack_sha256'] / filename).read_bytes() == encoded, 'Modern private stage owns exact complete audio')
        original_pack = {name: (output_pack / name).read_bytes() for name in names}
        run(*arguments, success=False)
        check(all((output_pack / name).read_bytes() == body for name, body in original_pack.items()), 'Existing output is never overwritten')
        run(*arguments[:-1], work / 'duplicate', '--name', 'Duplicate', success=False)
        malformed = work / 'truncated.wav'
        malformed.write_bytes(source_bytes[:-1])
        rejected = arguments.copy()
        rejected[2] = malformed
        rejected[-1] = work / 'malformed'
        run(*rejected, success=False)
        check(not (work / 'malformed').exists(), 'Malformed WAV publishes no pack')
        invalid_rights = work / 'invalid-rights.txt'
        invalid_rights.write_bytes(b'not\0valid')
        rejected = arguments.copy()
        rejected[-3] = invalid_rights
        rejected[-1] = work / 'invalid-rights'
        run(*rejected, success=False)
        check(not (work / 'invalid-rights').exists(), 'NUL rights declaration publishes no pack')
        rejected = arguments.copy()
        rejected[4] = 'invalid-uuid'
        rejected[-1] = work / 'invalid-id'
        run(*rejected, success=False)
        check(not (work / 'invalid-id').exists(), 'Invalid UUID publishes no pack')
        source.unlink()  # Exact self-created synthetic input only.
        run('--inspect-store', staged, '--profile', 'warm-beginning', *reference)
        check((staged / adopted['pack_sha256'] / filename).read_bytes() == encoded, 'No import-source fallback after removal')
        result.update(status='passed', source_wav_sha256=digest(source_bytes), pcm_sha256=digest(pcm),
                      cooked_sha256=digest(encoded), frame_count=8684544, sample_rate=44100, channels=2)
    except Exception as error:
        result['error'] = str(error)
    result.update(checks=checks, processes=logs, completed_at=datetime.now(timezone.utc).isoformat())
    report = output / (work.name + '-verification.json')
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'checks': len(checks), 'report': str(report), 'error': result.get('error')}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raise SystemExit(verify(args.executable, args.output))
