"""Separate native GPU processes prove persistent visible world changes."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os


def verify(executable: Path, output: Path):
    checks = []
    result = {'schema_version': 1, 'status': 'failed', 'checks': checks}
    output.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='aibs-visible-world-') as directory:
            work = Path(directory)
            slot = work / 'world.aibs'
            def run(step, label):
                report = work / (label + '.json')
                capture = work / (label + '.bmp')
                child = subprocess.run([str(executable), '--world-step', step, '--checkpoint', str(slot),
                                        '--capture', str(capture), '--world-report', str(report)],
                                       capture_output=True, text=True, timeout=35)
                if child.returncode:
                    raise AssertionError(f'{label}: {child.returncode}: {child.stdout} {child.stderr}')
                data = json.loads(report.read_text())
                assert data['status'] == 'passed', data
                return data, capture.read_bytes()
            seeded, dark = run('seed', 'seed')
            rejected = subprocess.run([str(executable), '--world-step', 'undo', '--checkpoint', str(slot),
                                       '--capture', str(work / 'protected.bmp'), '--world-report', str(work / 'protected.json')],
                                      capture_output=True, text=True, timeout=35)
            assert rejected.returncode != 0, 'Undo removed the starting motherboard'
            checks.append('Starting motherboard cannot be undone into an invalid saved world')
            edited, lit = run('edit', 'edit')
            assert seeded['world_id'] == edited['world_id']
            assert edited['entity_count'] == seeded['entity_count'] + 1
            assert edited['memory_events'] == seeded['memory_events'] + 2
            assert dark != lit, 'Repair/build did not change actual GPU pixels'
            checks.append('Repair and relay construction change GPU pixels through persisted entity state')
            restored, reloaded = run('verify', 'restart')
            assert restored['entity_ids'] == edited['entity_ids'] and restored['world_id'] == edited['world_id']
            assert restored['memory_events'] == edited['memory_events'] and restored['checkpoint_id'] == edited['checkpoint_id']
            assert reloaded == lit, 'Restart changed visible saved world'
            checks.append('Separate process reload restores identical visible geometry, UUIDs and Adam history')
            undone, _ = run('undo', 'undo')
            assert undone['entity_count'] == seeded['entity_count']
            redone, redone_pixels = run('redo', 'redo')
            assert redone['entity_ids'] == edited['entity_ids'] and redone_pixels == lit
            checks.append('Undo and redo survive process restarts and preserve restored object identity')
            removed, _ = run('delete', 'delete')
            final, _ = run('verify', 'deleted-restart')
            assert removed['entity_count'] == seeded['entity_count'] and final['entity_ids'] == removed['entity_ids']
            checks.append('Dismantled relays stay removed after restart; initial entities are not reseeded')
            assert edited['metrics']['invalid_mesh_rejected'] and edited['metrics']['empty_scene_cleared']
            checks.append('Invalid GPU replacement preserves prior mesh; empty scene clears and restores safely')
            result.update(status='passed', world_id=final['world_id'], checkpoint_id=final['checkpoint_id'],
                          revision=final['revision'], restored_revision=restored['revision'],
                          entity_count=final['entity_count'], object_count=final['object_count'],
                          memory_events=final['memory_events'], stable_ids=final['entity_ids'],
                          entity_ids=list(final['entity_ids'].values()), adapter=final['adapter'],
                          metrics={'gpu_pixels_changed': True, 'reload_pixels_identical': True, 'processes': 8,
                                   'debug_layer': final['metrics']['debug_layer'], 'debug_errors': final['metrics']['debug_errors']})
            (output / 'world-scene-dark.bmp').write_bytes(dark)
            (output / 'world-scene-restored.bmp').write_bytes(reloaded)
    except Exception as exc:
        result['error'] = str(exc)
        checks.append('FAILED: ' + str(exc))
        raise
    finally:
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        temporary = output / 'world_scene_verification.tmp'
        temporary.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, output / 'world_scene_verification.json')


if __name__ == '__main__':
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
