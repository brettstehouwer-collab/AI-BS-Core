"""Publish atomic build observations for the native AI-BS progress view."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import os


def report(configuration: str, status: str, stage: str) -> None:
    target = Path(__file__).resolve().parents[1] / 'out/build_progress.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(target.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        data = {'schema_version': 1, 'events': [], 'configurations': {}}
    now = datetime.now(timezone.utc).isoformat()
    data.update(schema_version=1, configuration=configuration, status=status, stage=stage, updated_at=now)
    if stage == 'starting':
        data.pop('completed_at', None)
    if status in ('passed', 'failed'):
        data['completed_at'] = now
        data['configurations'][configuration] = {'status': status, 'completed_at': now}
    data['events'] = (data['events'] + [{'at': now, 'configuration': configuration, 'status': status, 'stage': stage}])[-100:]
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('configuration', choices=['Debug', 'Release'])
    parser.add_argument('status', choices=['running', 'passed', 'failed'])
    parser.add_argument('stage')
    args = parser.parse_args()
    report(args.configuration, args.status, args.stage)
