"""Read-only NVML adapter and CLI fallback, without contacting a real driver."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from gpu.gpu_telemetry import NvidiaSMITelemetry


class NVMLTests(unittest.TestCase):
    def driver(self):
        api = Mock()
        api.NVML_TEMPERATURE_GPU = 0
        api.nvmlDeviceGetCount.return_value = 1
        api.nvmlDeviceGetMemoryInfo.return_value = SimpleNamespace(total=24000*1048576, used=4000*1048576, free=20000*1048576)
        api.nvmlDeviceGetPciInfo.return_value = SimpleNamespace(pciDeviceId=0x268410DE)
        api.nvmlDeviceGetName.return_value = b'RTX 4090'
        api.nvmlDeviceGetUUID.return_value = 'GPU-synthetic'
        api.nvmlSystemGetDriverVersion.return_value = '617.42'
        api.nvmlDeviceGetVbiosVersion.return_value = 'synthetic'
        api.nvmlDeviceGetTemperature.return_value = 40
        api.nvmlDeviceGetPowerUsage.return_value = 100000
        api.nvmlDeviceGetPowerManagementLimit.return_value = 450000
        api.nvmlDeviceGetUtilizationRates.return_value = SimpleNamespace(gpu=10)
        return api

    def test_nvml_read_and_cleanup_use_no_mutators_or_subprocess(self):
        api = self.driver()
        with patch('gpu.gpu_telemetry.import_module', return_value=api), patch('gpu.gpu_telemetry.subprocess.run') as run:
            sample = NvidiaSMITelemetry(prefer_nvml=True).read(fresh=True)
        self.assertTrue(sample['available'])
        self.assertEqual(sample['source'], 'nvml')
        self.assertEqual(sample['gpu']['memory_used_mib'], 4000)
        self.assertEqual(sample['gpu']['pci_device_id'], '0x268410DE')
        self.assertEqual(sample['gpu']['name'], 'RTX 4090')
        api.nvmlShutdown.assert_called_once()
        run.assert_not_called()
        self.assertFalse(any('Set' in call[0] for call in api.mock_calls))

    def test_nvml_failure_cleans_up_and_falls_back_to_bounded_cli(self):
        api = self.driver()
        api.nvmlDeviceGetMemoryInfo.side_effect = RuntimeError('synthetic driver failure')
        raw = '0, GPU-test, RTX 4090, 0x268410DE, 617.42, test, 24000, 4000, 20000, 40, 100, 450, 10\n'
        with patch('gpu.gpu_telemetry.import_module', return_value=api), patch('gpu.gpu_telemetry.subprocess.run', return_value=SimpleNamespace(returncode=0, stdout=raw)) as run:
            sample = NvidiaSMITelemetry(prefer_nvml=True).read(fresh=True)
        self.assertTrue(sample['available'])
        self.assertEqual(sample['source'], 'nvidia-smi')
        api.nvmlShutdown.assert_called_once()
        self.assertLessEqual(run.call_args.kwargs['timeout'], 3)
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_fresh_memory_is_not_replaced_by_cached_sensors(self):
        api = self.driver()
        telemetry = NvidiaSMITelemetry(prefer_nvml=True)
        with patch('gpu.gpu_telemetry.import_module', return_value=api):
            telemetry.read(fresh=True)
            api.nvmlDeviceGetMemoryInfo.return_value = SimpleNamespace(total=24000*1048576, used=5000*1048576, free=19000*1048576)
            sample = telemetry.read(fresh=True)
        self.assertEqual(sample['gpu']['memory_used_mib'], 5000)
        self.assertEqual(api.nvmlDeviceGetMemoryInfo.call_count, 2)
        self.assertEqual(api.nvmlDeviceGetTemperature.call_count, 1)
        self.assertLessEqual(sample['gpu']['sensor_age_s'], 2)

    def test_cached_snapshot_advances_sensor_age_without_mutating_source(self):
        api = self.driver()
        telemetry = NvidiaSMITelemetry(prefer_nvml=True)
        with patch('gpu.gpu_telemetry.import_module', return_value=api), \
                patch('gpu.gpu_telemetry.time.monotonic', return_value=0.0) as clock, \
                patch('gpu.gpu_telemetry.subprocess.run') as run:
            initial = telemetry.read(fresh=True)
            clock.return_value = 1.9
            refreshed = telemetry.read(fresh=True)
            clock.return_value = 3.8
            cached = telemetry.read()
        self.assertEqual(initial['age_s'], 0.0)
        self.assertEqual(initial['gpu']['sensor_age_s'], 0.0)
        self.assertEqual(refreshed['age_s'], 0.0)
        self.assertEqual(refreshed['gpu']['sensor_age_s'], 1.9)
        self.assertEqual(cached['age_s'], 1.9)
        self.assertEqual(cached['gpu']['sensor_age_s'], 3.8)
        self.assertEqual(telemetry._cache['age_s'], 0.0)
        self.assertEqual(telemetry._cache['gpu']['sensor_age_s'], 1.9)
        self.assertEqual(api.nvmlDeviceGetMemoryInfo.call_count, 2)
        self.assertEqual(api.nvmlDeviceGetTemperature.call_count, 1)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
