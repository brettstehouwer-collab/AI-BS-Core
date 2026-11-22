"""Offline GPU evidence tests: extracted definitions, fake DLL and temporary stores."""
import ast
import ctypes
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
GPU_FIELDS = ('gpu_name', 'core_temp_c', 'fan_speed_pct', 'memory_used_mb',
              'memory_total_mb', 'power_usage_w', 'gpu_util_pct', 'core_clock_mhz',
              'memory_clock_mhz')


class FakeNVML:
    def __init__(self, init=0, handle=0, failed=(), fan=100, auto_result=0, fan_count=1):
        self.init_result = init; self.handle_result = handle
        self.failed = set(failed); self.fan = fan; self.auto_result = auto_result
        self.fan_count = fan_count; self.shutdowns = 0; self.sets = []

    def nvmlInit_v2(self): return self.init_result
    def nvmlShutdown(self): self.shutdowns += 1; return 0
    def nvmlDeviceGetHandleByIndex_v2(self, index, pointer):
        if not self.handle_result: pointer._obj.value = 1
        return self.handle_result
    def nvmlDeviceGetName(self, handle, buffer, size):
        if 'name' in self.failed: return 1
        buffer.value = b'Offline fixture GPU'; return 0
    def _number(self, field, pointer, value):
        if field in self.failed: return 1
        pointer._obj.value = value; return 0
    def nvmlDeviceGetTemperature(self, handle, sensor, pointer): return self._number('temperature', pointer, 0)
    def nvmlDeviceGetFanSpeed(self, handle, pointer): return self._number('fan', pointer, self.fan)
    def nvmlDeviceGetPowerUsage(self, handle, pointer): return self._number('power', pointer, 0)
    def nvmlDeviceGetNumFans(self, handle, pointer): return self._number('fan_count', pointer, self.fan_count)
    def nvmlDeviceGetMemoryInfo(self, handle, pointer):
        if 'memory' in self.failed: return 1
        pointer._obj.total = 16 * 1024**2; pointer._obj.used = 0; pointer._obj.free = pointer._obj.total
        return 0
    def nvmlDeviceGetUtilizationRates(self, handle, pointer):
        if 'utilization' in self.failed: return 1
        pointer._obj.gpu = 0; pointer._obj.memory = 0; return 0
    def nvmlDeviceSetFanSpeed_v2(self, handle, index, value):
        self.sets.append((index, value)); return 0
    def nvmlDeviceDefaultFanSpeed(self, handle, index):
        self.sets.append((index, 'auto')); return self.auto_result


class HardwareEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aibs-offline-hardware-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'evidence.sqlite'
        source = ROOT/'backend/modules/gpu_hardware_telemetry.py'
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        nodes = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef))]
        namespace = {'__name__': 'isolated_gpu_evidence', '__file__': str(source), '_db_path': self.path}
        exec(compile(ast.fix_missing_locations(ast.Module(nodes, [])), str(source), 'exec'), namespace)
        import logging
        namespace['logger'] = logging.getLogger('offline-hardware-fixture')
        self.dll = FakeNVML(); self.dll_loads = 0
        def load(name): self.dll_loads += 1; return self.dll
        namespace['ctypes'] = types.SimpleNamespace(**{name: getattr(ctypes, name) for name in
            ('c_uint','c_void_p','c_ulonglong','Structure','byref','create_string_buffer')}, CDLL=load)
        self.namespace = namespace
        psutil = types.ModuleType('psutil')
        psutil.cpu_percent = lambda interval=None: 0.0
        psutil.virtual_memory = lambda: types.SimpleNamespace(used=0, total=16*1024**3)
        p = patch.dict(sys.modules, {'psutil': psutil}); p.start(); self.addCleanup(p.stop)
        self.engine = namespace['SovereignGpuTelemetry'](self.path)

    def query(self): return self.engine.query_nvml_telemetry()

    def test_constructor_and_missing_history_never_initialize_store(self):
        self.assertFalse(self.path.exists())
        self.assertEqual(self.engine.get_recent_logs(), [])
        self.assertFalse(self.path.exists())

    def test_missing_dll_has_null_gpu_fields_and_no_fabricated_history(self):
        self.namespace['ctypes'].CDLL = lambda name: (_ for _ in ()).throw(OSError('offline DLL absent'))
        data = self.query()
        self.assertFalse(data['nvml_online'])
        for field in GPU_FIELDS:
            self.assertIsNone(data[field], field)
            self.assertEqual(data['field_status'][field], 'unavailable')
        self.assertFalse(data['history_recorded'])
        self.assertFalse(self.path.exists())

    def test_initialization_and_handle_failures_do_not_claim_online_or_write_history(self):
        for init, handle in [(1, 0), (0, 1)]:
            with self.subTest(init=init, handle=handle):
                self.dll = FakeNVML(init=init, handle=handle)
                data = self.query()
                self.assertFalse(data['nvml_online'])
                self.assertTrue(all(data[field] is None for field in GPU_FIELDS))
                self.assertFalse(self.path.exists())
                self.assertEqual(self.dll.shutdowns, int(init == 0))

    def test_partial_fields_keep_valid_zero_and_never_retain_fallbacks(self):
        self.dll = FakeNVML(failed=('temperature', 'fan', 'memory'))
        data = self.query()
        self.assertTrue(data['nvml_online'])
        for field in ('core_temp_c', 'fan_speed_pct', 'memory_used_mb', 'memory_total_mb',
                      'core_clock_mhz', 'memory_clock_mhz'):
            self.assertIsNone(data[field], field)
            self.assertEqual(data['field_status'][field], 'unavailable')
        for field in ('power_usage_w', 'gpu_util_pct'):
            self.assertEqual(data[field], 0)
            self.assertEqual(data['field_status'][field], 'measured')
        self.assertNotIn('LOCKED', data['status_flag'])
        self.assertEqual(self.dll.shutdowns, 1)

    def test_all_failed_sensors_are_unavailable_even_after_successful_nvml_init(self):
        self.dll = FakeNVML(failed=('name','temperature','fan','memory','power','utilization'))
        data = self.query()
        self.assertFalse(data['nvml_online'])
        self.assertFalse(data['history_recorded'])
        self.assertTrue(all(data[field] is None for field in GPU_FIELDS))
        self.assertFalse(self.path.exists())

    def test_observed_fan_at_100_percent_does_not_prove_enforced_fan_lock(self):
        data = self.query()
        self.assertTrue(data['nvml_online'])
        self.assertEqual(data['fan_speed_pct'], 100)
        self.assertEqual(data['field_status']['fan_speed_pct'], 'measured')
        self.assertNotIn('LOCKED', data['status_flag'])
        self.assertFalse(data['fan_enforcement_verified'])
        self.assertEqual(data['default_fan_target_pct'], 100)
        self.assertEqual(self.dll.sets, [])

    def test_host_sensor_failure_returns_none_instead_of_demo_values(self):
        with patch.dict(sys.modules, {'psutil': None}): data = self.query()
        for field in ('cpu_util_pct', 'ram_used_gb', 'ram_total_gb'):
            self.assertIsNone(data[field])
            self.assertEqual(data['field_status'][field], 'unavailable')

    def test_legacy_history_is_preserved_and_clearly_unverified(self):
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS gpu_thermal_logs(id INTEGER PRIMARY KEY,timestamp TEXT,gpu_name TEXT,core_temp_c INTEGER)')
            conn.execute("INSERT INTO gpu_thermal_logs(id,timestamp,gpu_name,core_temp_c) VALUES(1,'2026-10-29 00:00:00','legacy fixture',32)")
            conn.commit()
        self.query()
        history = self.engine.get_recent_logs()
        legacy = next(row for row in history if row['gpu_name'] == 'legacy fixture')
        self.assertEqual(legacy['verification'], 'legacy_unverified')
        self.assertEqual(legacy['field_status']['core_temp_c'], 'unavailable')
        self.assertTrue(any(row['verification'] == 'recorded_measurement' for row in history))
        with closing(sqlite3.connect(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM gpu_thermal_logs').fetchone()[0], 1)

    def test_unverified_data_cannot_be_admitted_as_new_history(self):
        accepted = self.engine.log_telemetry({'gpu_name': 'caller assertion', 'core_temp_c': 32})
        self.assertFalse(accepted)
        self.assertFalse(self.path.exists())

    def test_manual_request_acceptance_is_separate_from_observed_enforcement(self):
        self.dll = FakeNVML(failed=('fan',))
        result = self.engine.set_fan_speed()
        self.assertTrue(result['success'])
        self.assertFalse(result['enforcement_verified'])
        self.assertEqual(result['target_speed'], 100)
        self.assertIsNone(result['observed_speed_pct'])
        self.assertNotIn('locked', result['message'].lower())
        self.assertEqual(self.dll.sets, [(0, 100)])

    def test_auto_driver_request_failure_is_not_reported_restored(self):
        self.dll = FakeNVML(auto_result=1)
        result = self.engine.set_fan_speed(speed=0, auto=True)
        self.assertFalse(result['success'])
        self.assertFalse(result['enforcement_verified'])
        self.assertNotIn('restored', result['message'].lower())
        self.assertEqual(self.dll.shutdowns, 1)

    def test_rejected_input_never_loads_hardware_binding(self):
        for speed in (True, '100', 100.0, -1, 101, 20):
            with self.subTest(speed=speed):
                result = self.engine.set_fan_speed(speed=speed)
                self.assertFalse(result['success'])
                self.assertEqual(self.dll_loads, 0)


if __name__ == '__main__': unittest.main()
