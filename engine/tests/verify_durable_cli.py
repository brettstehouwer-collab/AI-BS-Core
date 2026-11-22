"""Native verification arguments cannot select a player's default save."""
from pathlib import Path
import json
import os
import subprocess
import sys
import uuid


def verify(executable, output):
    work = output.resolve() / 'durable-cli-proof' / str(uuid.uuid4())
    work.mkdir(parents=True)
    environment = os.environ.copy()
    environment['LOCALAPPDATA'] = str(work / 'isolated-localappdata')
    common = ['--durable-world', '--durable-step', 'repair', '--capture', str(work / 'frame.bmp'),
              '--durable-report', str(work / 'report.json')]
    # The isolated environment makes a pre-fix failure harmless to actual saves.
    result = subprocess.run([str(executable.resolve()), *common], env=environment,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode != 0, 'Proof mode silently used the default player database'
    assert not (work / 'isolated-localappdata').exists(), 'Rejected proof created default game data'
    # A malformed proof must return an error, without an interactive MessageBox.
    result = subprocess.run([str(executable.resolve()), '--durable-world', '--durable-step', 'seed',
                             '--world-db', str(work / 'invalid.sqlite')], env=environment,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode != 0 and not (work / 'invalid.sqlite').exists()
    print(json.dumps({'status': 'passed', 'checks': [
        'Proof mode requires an explicit database and leaves default player data absent',
        'Malformed proof arguments return without GUI prompts or database creation']}))


if __name__ == '__main__':
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
