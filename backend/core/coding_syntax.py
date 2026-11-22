"""Parse selected JavaScript/JSX as data using the installed trusted parser.

No evaluation, imports from candidate source, package scripts, plugins from project
configuration, network requests or generated commands. This is not project testing.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

PARSER = Path(__file__).resolve().parents[2]/'frontend/node_modules/@babel/parser/lib/index.js'
_SCRIPT = r'''
const fs = require('node:fs');
const parser = require(process.argv[1]);
const bytes = fs.readFileSync(0);
if (bytes.length > 65536) process.exit(2);
const files = JSON.parse(bytes.toString('utf8'));
const result = files.map(file => {
  try {
    parser.parse(file.content, {sourceType: file.path.endsWith('.mjs') ? 'module' :
      file.path.endsWith('.cjs') ? 'commonjs' : 'unambiguous',
      plugins: ['jsx'], errorRecovery: false, attachComment: false});
    return {path: file.path, kind: 'syntax', status: 'passed'};
  } catch(error) {
    return {path: file.path, kind: 'syntax', status: 'failed',
      message: 'SyntaxError', line: error.loc?.line ?? null, column: error.loc?.column ?? null};
  }
});
process.stdout.write(JSON.stringify(result));
'''


def available():
    return bool(shutil.which('node') and PARSER.is_file())


def javascript_checks(files):
    if not files:
        return []
    pending = [{'path': f['path'], 'kind': 'syntax', 'status': 'not_run',
                'reason': 'The installed JavaScript syntax parser is unavailable.'} for f in files]
    node = shutil.which('node')
    if not node or not PARSER.is_file():
        return pending
    wire = json.dumps(files, ensure_ascii=False).encode('utf-8')
    if len(wire) > 65536 or len(files) > 20:
        raise ValueError('Selected JavaScript syntax input exceeds the bound')
    environment = {k: v for k, v in os.environ.items() if k.upper() in {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'}}
    try:
        parser_hash = hashlib.sha256(PARSER.read_bytes()).hexdigest()
        result = subprocess.run([str(Path(node).resolve()), '--max-old-space-size=96', '--no-addons',
                                 '-e', _SCRIPT, str(PARSER)],
                                input=wire, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                cwd=PARSER.parent, env=environment, timeout=5,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode or len(result.stdout) > 16384:
            raise ValueError('Syntax parser did not complete')
        checks = json.loads(result.stdout)
        if not isinstance(checks, list) or len(checks) != len(files):
            raise ValueError('Unexpected syntax result')
        for source, check in zip(files, checks):
            if (not isinstance(check, dict) or check.get('path') != source['path'] or
                    check.get('kind') != 'syntax' or check.get('status') not in {'passed', 'failed'}):
                raise ValueError('Unbound syntax result')
            check['parser_sha256'] = parser_hash
        if hashlib.sha256(PARSER.read_bytes()).hexdigest() != parser_hash:
            raise ValueError('Syntax parser changed')
        return checks
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return [{**check, 'reason': 'JavaScript syntax parsing did not complete; project checks were not run.'}
                for check in pending]
