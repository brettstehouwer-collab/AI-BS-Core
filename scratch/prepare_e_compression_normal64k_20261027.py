"""Preserve a stopped compression pass and prepare the operator's revised policy."""
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(r'C:\AI-BS')
OLD = ROOT / 'backups/e_drive_compression_20261027'
NEW = OLD / 'normal_64k_20261027T195041Z'
SCRATCH = ROOT / 'scratch'
SUFFIX = '_normal64k_20261027'
NAMES = {
    'runner': 'compress_e_ntfs' + SUFFIX + '.py',
    'restorer': 'restore_e_compressed' + SUFFIX + '.py',
    'finalizer': 'record_e_compression' + SUFFIX + '.py',
    'supervisor': 'supervise_e_compression' + SUFFIX + '.py',
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())

def replace_once(source, before, after):
    assert source.count(before) == 1, repr(before)
    return source.replace(before, after, 1)

stopped = json.loads((OLD / 'supervisor_completion.json').read_text())
assert stopped['receipt_validation_passed'] and stopped['final_checkpoint_written']
assert stopped['halt_reason'] == 'stop_requested' and not stopped['eligible_pass_complete']
assert stopped['final_checkpoint_sha256'] == sha((OLD / 'finish_checkpoint.json').read_bytes())
assert not (OLD / 'supervisor_failure.json').exists()
original_pins = json.loads((OLD / 'supervisor_start.json').read_text())['source_sha256']
assert all(sha(Path(name).read_bytes()) == digest for name, digest in original_pins.items())
assert (OLD / 'stop_requested').exists(), 'Keep the old pass stopped'

NEW.mkdir(exist_ok=False)
manifest = {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'authorization': 'Operator: go ahead and skip files under 64 KB and run it at normal priority, but keep all the verification checks',
    'minimum_file_bytes': 65536,
    'priority_mode': 'NORMAL_PRIORITY_CLASS',
    'shared_run_lock': str(OLD / 'run.lock'),
    'previous_run': str(OLD),
    'previous_supervisor_completion_sha256': sha((OLD / 'supervisor_completion.json').read_bytes()),
    'previous_run_receipt': stopped,
    'baseline_copies': [],
    'sources': [],
}
for name in ['plan.json', 'pilot_results.jsonl', 'pilot_receipt.json', 'results.jsonl',
             'intents.jsonl', 'restoration_results.jsonl', 'restoration_intents.jsonl',
             'reservation_reversal_probe.json']:
    before = (OLD / name).read_bytes()
    write(NEW / name, before)
    assert (OLD / name).read_bytes() == before
    assert sha((NEW / name).read_bytes()) == sha(before)
    manifest['baseline_copies'].append({'name': name, 'bytes': len(before), 'sha256': sha(before)})

runner_original = (SCRATCH / 'compress_e_ntfs_20261027.py').read_text()
runner = replace_once(runner_original, "OUT = Path(r'C:\\AI-BS\\backups\\e_drive_compression_20261027')",
                      'OUT = Path(' + repr(str(NEW)) + ')\nRUN_LOCK = OUT.parent / \'run.lock\'')
runner = replace_once(runner, 'FREE_FLOOR = 8 * 2**30', 'FREE_FLOOR = 8 * 2**30\nMIN_BYTES = 65536')
runner = replace_once(runner,
    '    priority_ok = bool(K.SetPriorityClass(K.GetCurrentProcess(), 0x100000))',
    '    fail_if_false(K.SetPriorityClass(K.GetCurrentProcess(), 0x20))\n'
    '    K.GetPriorityClass.argtypes = [w.HANDLE]\n'
    '    K.GetPriorityClass.restype = w.DWORD\n'
    '    priority_class = K.GetPriorityClass(K.GetCurrentProcess())\n'
    '    if priority_class != 0x20:\n'
    "        raise RuntimeError('Normal process priority was not verified')\n"
    '    priority_ok = True')
runner = replace_once(runner,
    "                if Path(item['path']).suffix.casefold() in ALREADY_ENCODED_EXT:",
    "                if item['size'] < MIN_BYTES:\n"
    "                    result = {'path': item['path'], 'status': 'skipped',\n"
    "                              'reason': 'below_64k_policy', 'planned_size': item['size'],\n"
    "                              'minimum_file_bytes': MIN_BYTES}\n"
    "                elif Path(item['path']).suffix.casefold() in ALREADY_ENCODED_EXT:")
runner = replace_once(runner, 'from restore_e_compressed_20261027 import restore',
                      'from ' + NAMES['restorer'][:-3] + ' import restore')
runner = replace_once(runner,
    "                progress = {'timestamp_utc': utc(), 'mode': mode, 'totals': dict(totals),",
    "                progress = {'timestamp_utc': utc(), 'mode': mode, 'totals': dict(totals),\n"
    "                            'minimum_file_bytes': MIN_BYTES, 'priority_mode': 'normal',\n"
    "                            'priority_class': priority_class, 'pid': os.getpid(),")
runner = replace_once(runner,
    "               'background_priority_applied': priority_ok, 'halt_reason': halt, 'totals': dict(totals),",
    "               'background_priority_applied': False, 'normal_priority_applied': priority_ok,\n"
    "               'priority_class': priority_class, 'minimum_file_bytes': MIN_BYTES,\n"
    "               'pid': os.getpid(), 'halt_reason': halt, 'totals': dict(totals),")
runner = replace_once(runner, "with (OUT / 'run.lock').open('a+b') as lock:",
                      "with RUN_LOCK.open('a+b') as lock:")

restorer_original = (SCRATCH / 'restore_e_compressed_20261027.py').read_text()
restorer = replace_once(restorer_original, 'import compress_e_ntfs_20261027 as core',
                        'import ' + NAMES['runner'][:-3] + ' as core')
restorer = replace_once(restorer, 'core.K.SetPriorityClass(core.K.GetCurrentProcess(), 0x100000)',
                        'core.K.SetPriorityClass(core.K.GetCurrentProcess(), 0x20)')

finalizer = (SCRATCH / 'record_e_compression_20261027.py').read_text()
finalizer = replace_once(finalizer, "out = root / 'backups/e_drive_compression_20261027'",
                         'out = Path(' + repr(str(NEW)) + ')')
finalizer = replace_once(finalizer, "script = root / 'scratch/compress_e_ntfs_20261027.py'",
                         "script = root / 'scratch/" + NAMES['runner'] + "'")
finalizer = replace_once(finalizer, "common = summary + ('Evidence:backups/e_drive_compression_20261027 including plan, intents, pilot and '",
    "summary += (' Operator-authorized revised policy: skip planned files below65,536bytes before opening; '\n"
    "            'normal process priority is set and verified before processing. Existing file exclusion, '\n"
    "            'same-handle full SHA-256/identity/size/time/compression-state verification, durable intents, '\n"
    "            'exclusive shared volume-run lock, free-space floor, no-net-gain restoration and error halts '\n"
    "            'remain. Previously processed files are not repeated. Prior background-pass receipts remain '\n"
    "            'unchanged in the parent evidence directory; baseline_prefix_verification.json checks '\n"
    "            'copied cumulative evidence prefixes. ')\n"
    "common = summary + ('Evidence:backups/e_drive_compression_20261027/" + NEW.name + " including plan, intents, pilot and '")

supervisor = (SCRATCH / 'supervise_e_compression_20261027.py').read_text()
supervisor = replace_once(supervisor, "out = root / 'backups/e_drive_compression_20261027'",
                          'out = Path(' + repr(str(NEW)) + ')')
for variable, key, old_name in [
    ('source', 'runner', 'compress_e_ntfs_20261027.py'),
    ('restorer', 'restorer', 'restore_e_compressed_20261027.py'),
    ('finalizer', 'finalizer', 'record_e_compression_20261027.py')]:
    supervisor = replace_once(supervisor, f"{variable} = root / 'scratch/{old_name}'",
                              f"{variable} = root / 'scratch/{NAMES[key]}'")
supervisor = replace_once(supervisor, "'authorization': 'Operator: ignore steam and compress the rest',",
    "'authorization': 'Operator: skip files under64KB, use normal priority, retain all verification checks',\n"
    "           'minimum_file_bytes': 65536, 'priority_mode': 'normal',\n"
    "           'previous_run': str(out.parent), 'shared_run_lock': str(out.parent / 'run.lock'),")
supervisor = replace_once(supervisor,
    "    assert receipt['started_utc'] >= started, 'Stale completion receipt'",
    "    assert receipt['started_utc'] >= started, 'Stale completion receipt'\n"
    "    assert receipt['minimum_file_bytes'] == 65536 and receipt['priority_class'] == 0x20\n"
    "    assert receipt['normal_priority_applied'] and not receipt['background_priority_applied']\n"
    "    preparation = json.loads((out / 'preparation_manifest.json').read_text())\n"
    "    prefix_checks = []\n"
    "    for item in preparation['baseline_copies']:\n"
    "        prior = (out.parent / item['name']).read_bytes()\n"
    "        current = (out / item['name']).read_bytes()\n"
    "        assert sha(out.parent / item['name']) == item['sha256'], 'Prior evidence changed'\n"
    "        assert len(prior) == item['bytes'] and current.startswith(prior), 'Cumulative prefix changed'\n"
    "        prefix_checks.append({'name': item['name'], 'prior_sha256': item['sha256'],\n"
    "                              'prior_bytes': item['bytes'], 'prefix_preserved': True})\n"
    "    json_write('baseline_prefix_verification.json', {'timestamp_utc': utc(), 'files': prefix_checks})")
supervisor = replace_once(supervisor,
    "    status.update({'receipt_validation_passed': True, 'retained_compressed_files': len(retained),",
    "    status.update({'minimum_file_bytes': 65536, 'priority_mode': 'normal',\n"
    "                   'below_64k_policy_skips': sum(row.get('reason') == 'below_64k_policy' for row in results),\n"
    "                   'receipt_validation_passed': True, 'retained_compressed_files': len(retained),")
supervisor = replace_once(supervisor,
    "                'Inspect backups/e_drive_compression_20261027/supervisor_failure.json and retained '",
    "                'Inspect backups/e_drive_compression_20261027/" + NEW.name + "/supervisor_failure.json and retained '")

sources = {'runner': runner, 'restorer': restorer, 'finalizer': finalizer, 'supervisor': supervisor}
for key, text in sources.items():
    ast.parse(text, filename=NAMES[key])
    target = SCRATCH / NAMES[key]
    write(target, text.encode('utf-8'))
    write(NEW / NAMES[key], text.encode('utf-8'))
    manifest['sources'].append({'role': key, 'path': str(target), 'sha256': sha(target.read_bytes())})

prior_tree = ast.parse(runner_original)
new_tree = ast.parse(runner)
prior_functions = {node.name: ast.dump(node, include_attributes=False) for node in prior_tree.body if isinstance(node, ast.FunctionDef)}
new_functions = {node.name: ast.dump(node, include_attributes=False) for node in new_tree.body if isinstance(node, ast.FunctionDef)}
unchanged = [name for name in prior_functions if name != 'apply']
assert all(prior_functions[name] == new_functions[name] for name in unchanged)
old_restore = next(node for node in ast.parse(restorer_original).body if isinstance(node, ast.FunctionDef) and node.name == 'restore')
new_restore = next(node for node in ast.parse(restorer).body if isinstance(node, ast.FunctionDef) and node.name == 'restore')
assert ast.dump(old_restore, include_attributes=False) == ast.dump(new_restore, include_attributes=False)
manifest['unchanged_runner_functions_ast'] = unchanged
manifest['restoration_function_ast_unchanged'] = True
manifest['old_sources_unchanged'] = all(sha(Path(name).read_bytes()) == digest for name, digest in original_pins.items())
assert manifest['old_sources_unchanged']
write(NEW / 'preparation_manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
print(json.dumps({'prepared': str(NEW), 'source_files': len(sources), 'unchanged_functions': len(unchanged),
                  'prior_evidence_preserved': True, 'e_drive_mutations': False}))
