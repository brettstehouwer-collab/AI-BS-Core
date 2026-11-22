"""Cook an owned glTF fixture, then exercise its embedded character in native Play."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import uuid

from verify_character_cooker import fixture, ASSET_ID, CLIPS
from verify_companion_native import verify as verify_companion


def verify(cooker, native_fixture, player, output):
    cooker, native_fixture, player, output = map(lambda p: Path(p).resolve(), (cooker, native_fixture, player, output))
    output.mkdir(parents=True, exist_ok=True)
    work = output / ('character-native-' + str(uuid.uuid4()))
    work.mkdir()
    report = work / 'verification.json'
    result = {'schema_version': 1, 'status': 'failed', 'family_references_used': False,
              'model_inference': False, 'source_removed': False, 'processes_joined': False}
    children = []
    try:
        source, rights, pack = work / 'synthetic.glb', work / 'rights.txt', work / 'pack'
        source.write_bytes(fixture()[0])
        rights.write_text('Synthetic test fixture authored for AI-BS. No family references.\n', encoding='utf-8')
        args = [str(cooker), '--cook-character', '--source', str(source), '--asset-id', ASSET_ID,
                '--name', 'Synthetic animated guide', '--license', str(rights), '--output', str(pack)]
        for index, name, mode in CLIPS:
            args.extend(['--clip', str(index), name, mode])
        with (work / 'cook.stdout.log').open('xb') as out, (work / 'cook.stderr.log').open('xb') as err:
            child = subprocess.Popen(args, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            children.append(child)
            try:
                code = child.wait(timeout=120)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=15)
        if code:
            raise RuntimeError('Actual character cook failed: ' + (work / 'cook.stderr.log').read_text(errors='replace')[-2000:])
        result['cook_receipt'] = json.loads((work / 'cook.stdout.log').read_text(encoding='utf-8'))
        result['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        source.unlink()  # Exact test-owned import source only; native Play must use embedded cooked data.
        result['source_removed'] = not source.exists()
        native_output = work / 'native'
        if verify_companion(native_fixture, player, native_output, model_pack=pack):
            raise RuntimeError('Cooked character native controls/routes/restart proof failed; see native process evidence')
        proofs = list(native_output.glob('companion-native-*-verification.json'))
        if len(proofs) != 1:
            raise RuntimeError('Expected one owned native process report')
        proof = json.loads(proofs[0].read_text(encoding='utf-8'))
        if proof['status'] != 'passed' or not proof['processes_joined'] or len(proof['checks']) != 80:
            raise RuntimeError('Incomplete cooked character native acceptance')
        result.update(status='passed', checks=len(proof['checks']), native_report=str(proofs[0]),
                      native_processes_joined=proof['processes_joined'])
        result['executable_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (cooker, native_fixture, player)}
    except Exception as error:
        result['error'] = str(error)
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=15)
        result['processes_joined'] = all(child.poll() is not None for child in children)
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'report': str(report), **({'error': result['error']} if 'error' in result else {})}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(verify(*sys.argv[1:]))
