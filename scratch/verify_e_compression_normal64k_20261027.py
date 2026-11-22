"""Exercise revised dispatch/priority admission without reading or changing E: files."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import types

ROOT = Path(r'C:\AI-BS')
OUT = ROOT / 'backups/e_drive_compression_20261027/normal_64k_20261027T195041Z'
SOURCE = ROOT / 'scratch/compress_e_ntfs_normal64k_20261027.py'
spec = importlib.util.spec_from_file_location('compression_policy_synthetic_test', SOURCE)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

class Priority:
    def __init__(self, set_ok=True, reported=0x20):
        self.calls = []
        self.GetCurrentProcess = lambda: 123
        self.SetPriorityClass = lambda handle, value: self.calls.append((handle, value)) or set_ok
        self.GetPriorityClass = lambda handle: reported

test_root = OUT / 'synthetic_policy_checks'
test_root.mkdir(exist_ok=False)
results = []
original_disk_usage = core.shutil.disk_usage
original_out, original_kernel, original_volume, original_compress = core.OUT, core.K, core.volume_snapshot, core.compress_one

try:
    for label, priority, expect_error in [
        ('size_boundary', Priority(), False),
        ('priority_set_denied', Priority(set_ok=False), True),
        ('priority_query_mismatch', Priority(reported=0x4000), True),
    ]:
        case = test_root / label
        case.mkdir()
        paths = [r'E:\synthetic_65535.wav', r'E:\synthetic_65536.wav', r'E:\synthetic_65537.wav']
        plan = {'files': [{'path': path, 'size': size} for path, size in zip(paths, [65535, 65536, 65537])],
                'file_count': 3, 'free_before': 20 * 2**30}
        (case / 'plan.json').write_text(json.dumps(plan))
        (case / 'pilot_receipt.json').write_text(json.dumps({'all_content_verified': True, 'compressed_verified': 2}))
        (case / 'intents.jsonl').write_text('')
        called = []
        def no_mutation_compress(item):
            assert item['size'] >= 65536, 'Sub-threshold file reached the file-opening implementation'
            called.append(item['path'])
            return {'path': item['path'], 'status': 'skipped', 'reason': 'synthetic_file_guard'}
        core.OUT, core.K = case, priority
        core.volume_snapshot = lambda: {'available_bytes': 20 * 2**30}
        core.compress_one = no_mutation_compress
        core.shutil.disk_usage = lambda path: types.SimpleNamespace(free=20 * 2**30)
        raised = None
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                core.apply('all')
        except (OSError, RuntimeError) as exc:
            raised = type(exc).__name__
        assert bool(raised) == expect_error, (label, raised)
        assert priority.calls == [(123, 0x20)], priority.calls
        if expect_error:
            assert not called and not (case / 'results.jsonl').exists(), 'Priority admission failed after dispatch'
            assert not (case / 'completion.json').exists()
        else:
            rows = [json.loads(line) for line in (case / 'results.jsonl').read_text().splitlines()]
            assert rows[0]['reason'] == 'below_64k_policy' and rows[0]['path'] == paths[0]
            assert called == paths[1:], 'The exact64KiB boundary was skipped incorrectly'
            receipt = json.loads((case / 'completion.json').read_text())
            assert receipt['normal_priority_applied'] and receipt['priority_class'] == 0x20
            assert not receipt['background_priority_applied'] and receipt['minimum_file_bytes'] == 65536
            assert receipt['eligible_pass_complete'] and receipt['remaining_count'] == 0
        results.append({'case': label, 'passed': True, 'guard_calls': len(called), 'expected_error': raised})
finally:
    core.shutil.disk_usage = original_disk_usage
    core.OUT, core.K, core.volume_snapshot, core.compress_one = original_out, original_kernel, original_volume, original_compress

report = {'all_passed': True, 'e_file_reads_or_mutations': False, 'cases': results,
          'scope': 'Dispatch and priority fail-closed behavior only; unchanged preservation functions separately compared by AST'}
(OUT / 'policy_verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
