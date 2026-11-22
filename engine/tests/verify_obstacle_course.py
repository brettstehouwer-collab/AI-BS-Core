"""Two real native processes prove traversal and saved inclined-world restart."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    player = Path(sys.argv[1]).resolve(strict=True)
    output = Path(sys.argv[2]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = output / 'obstacle_course_verification.json'
    result = {'schema_version': 1, 'status': 'failed', 'checks': [], 'metrics': {}}
    work = output / 'course-checkpoints' / str(uuid.uuid4())
    work.mkdir(parents=True)
    try:
        stages = []
        for stage in ('traverse', 'restart'):
            capture = output / f'obstacle-course-{stage}.bmp'
            evidence = work / f'{stage}.json'
            process = subprocess.run([str(player), '--course-test', stage, '--checkpoint', str(work / 'course.aibs'),
                                      '--capture', str(capture), '--course-report', str(evidence)],
                                     capture_output=True, text=True, timeout=35)
            if process.returncode:
                raise RuntimeError(f'{stage} exit {process.returncode}: {process.stdout} {process.stderr}')
            data = json.loads(evidence.read_text(encoding='utf-8'))
            if data.get('status') != 'passed' or data.get('stage') != stage:
                raise RuntimeError(f'Invalid native {stage} evidence')
            stages.append(data)
        first, restored = stages
        for field in ('world_id', 'checkpoint_id', 'revision', 'memory_events', 'entity_ids', 'ramp_rotation', 'target_state', 'object_count'):
            if first[field] != restored[field]:
                raise RuntimeError(f'{field} changed across real process restart')
        if first['revision'] != 2 or first['memory_events'] != 2 or first['target_state'] != 100:
            raise RuntimeError('Repair did not survive exactly once')
        if (output / 'obstacle-course-traverse.bmp').read_bytes() != (output / 'obstacle-course-restart.bmp').read_bytes():
            raise RuntimeError('Restored inclined world changed rendered GPU pixels')
        metrics = dict(first['metrics'])
        metrics.update(restored['metrics'])
        names = ('steps', 'slopes', 'walls', 'falls', 'focus', 'restart', 'interaction')
        if any(metrics.get(name) is not True for name in names) or metrics['debug_errors'] != 0:
            raise RuntimeError('Course is missing a verified traversal gate')
        result.update(status='passed', adapter=restored['adapter'], world_id=restored['world_id'],
                      checkpoint_id=restored['checkpoint_id'], metrics=metrics,
                      checks=first['checks'] + restored['checks'] +
                      ['World/entity IDs, saved orientation and repair history preserved across two processes',
                       'Restored native GPU pixels match the saved inclined motherboard exactly'])
    except Exception as exc:
        result.update(error=str(exc), checks=[str(exc)])
    result['completed_at'] = datetime.now(timezone.utc).isoformat()
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
