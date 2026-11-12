"""Offline admission/telemetry tests: synthetic device data, no model or GPU execution."""
import asyncio
import copy
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from gpu import AdaptiveGPUController, GPUAdmissionError
from gpu.gpu_telemetry import NvidiaSMITelemetry, parse_nvidia_csv
from gpu.model_residency import ModelResidencyManager, adaptive_embedding_batches, build_embedding_batches
from gpu.precision_router import precision_recommendation
from gpu.compute_scheduler import latency_summary


def observed(*, used=4000, total=24000, temperature=50):
    return {"available": True, "observed_at_unix": time.time(), "age_s": 0,
            "gpu": {"memory_total_mib": total, "memory_used_mib": used, "memory_free_mib": total-used,
                    "temperature_c": temperature, "power_w": 100, "power_limit_w": 450}}


class Source:
    def __init__(self):
        self.value = observed()
    async def sample(self):
        return copy.deepcopy(self.value)


class ControllerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.source = Source()
        self.controller = AdaptiveGPUController(self.source, max_wait_s=.15, poll_s=.005)

    async def wait_queued(self, count):
        for _ in range(100):
            if (await self.controller.snapshot())["scheduler"]["queued"] == count:
                return
            await asyncio.sleep(.001)
        self.fail("waiter did not reach expected queue state")

    async def test_single_active_serializes_concurrent_requests(self):
        entered, release = asyncio.Event(), asyncio.Event()
        order = []
        async def first():
            async with self.controller.lease("first", estimated_vram_mib=1000):
                order.append("first")
                entered.set()
                await release.wait()
        async def second():
            async with self.controller.lease("second", estimated_vram_mib=1000):
                order.append("second")
        one = asyncio.create_task(first())
        await entered.wait()
        two = asyncio.create_task(second())
        await self.wait_queued(1)
        snap = await self.controller.snapshot()
        self.assertEqual(snap["scheduler"]["active"], 1)
        self.assertEqual(snap["scheduler"]["reserved_mib"], 1000)
        self.assertEqual(order, ["first"])
        release.set()
        await asyncio.gather(one, two)
        self.assertEqual(order, ["first", "second"])
        self.assertEqual((await self.controller.snapshot())["scheduler"]["reserved_mib"], 0)

    async def test_priority_then_fifo_and_cancelled_waiter_removed(self):
        order = []
        async def worker(name, priority):
            async with self.controller.lease(name, priority=priority, estimated_vram_mib=1000):
                order.append(name)
        async with self.controller.lease("blocker", estimated_vram_mib=1000):
            low = asyncio.create_task(worker("low", 50))
            await self.wait_queued(1)
            high = asyncio.create_task(worker("high", 1))
            await self.wait_queued(2)
            high2 = asyncio.create_task(worker("high2", 1))
            await self.wait_queued(3)
            cancelled = asyncio.create_task(worker("cancelled", 0))
            await self.wait_queued(4)
            cancelled.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await cancelled
            await self.wait_queued(3)
        await asyncio.gather(low, high, high2)
        self.assertEqual(order, ["high", "high2", "low"])
        self.assertEqual((await self.controller.snapshot())["scheduler"]["cancelled_waiters"], 1)

    async def test_queue_bound_is_enforced(self):
        self.controller.max_queue = 1
        async def waiter():
            async with self.controller.lease("waiter", estimated_vram_mib=1000):
                pass
        async with self.controller.lease("active", estimated_vram_mib=1000):
            task = asyncio.create_task(waiter())
            await self.wait_queued(1)
            with self.assertRaises(GPUAdmissionError) as error:
                async with self.controller.lease("overflow", estimated_vram_mib=1000):
                    self.fail("overflow admitted")
            self.assertEqual(error.exception.reason, "queue_full")
        await task

    async def test_body_exception_releases_reservation(self):
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            async with self.controller.lease("model", estimated_vram_mib=1000):
                raise RuntimeError("synthetic")
        snapshot = await self.controller.snapshot()
        self.assertEqual(snapshot["scheduler"]["active"], 0)
        self.assertEqual(snapshot["scheduler"]["reserved_mib"], 0)

    async def test_active_cancellation_releases_and_next_request_runs(self):
        entered = asyncio.Event()
        async def worker():
            async with self.controller.lease("model", estimated_vram_mib=1000):
                entered.set()
                await asyncio.Event().wait()
        task = asyncio.create_task(worker())
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        async with self.controller.lease("next", estimated_vram_mib=1000):
            self.assertEqual((await self.controller.snapshot())["scheduler"]["active"], 1)

    async def test_pressure_defers_then_admits_with_fresh_memory(self):
        self.source.value = observed(used=19000)
        entered = asyncio.Event()
        async def worker():
            async with self.controller.lease("model", estimated_vram_mib=2000):
                entered.set()
        task = asyncio.create_task(worker())
        await self.wait_queued(1)
        self.assertFalse(entered.is_set())
        self.source.value = observed(used=4000)
        await task
        self.assertTrue(entered.is_set())

    async def test_pressure_timeout_leaves_no_stale_queue(self):
        self.source.value = observed(used=19000)
        with self.assertRaises(GPUAdmissionError) as error:
            async with self.controller.lease("model", estimated_vram_mib=2000):
                self.fail("pressure admission")
        self.assertEqual(error.exception.reason, "vram_pressure")
        self.assertEqual((await self.controller.snapshot())["scheduler"]["queued"], 0)

    async def test_no_telemetry_cannot_admit(self):
        self.source.value = {"available": False}
        with self.assertRaises(GPUAdmissionError) as error:
            async with self.controller.lease("model", estimated_vram_mib=1):
                self.fail("missing telemetry admitted")
        self.assertEqual(error.exception.reason, "telemetry_unavailable")

    async def test_hanging_telemetry_times_out_and_cleans_queue(self):
        entered, cancelled = asyncio.Event(), asyncio.Event()
        calls = 0
        async def source():
            nonlocal calls
            calls += 1
            if calls == 1:
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()
            return observed()
        self.controller.telemetry_provider = source
        self.controller.max_wait_s = .03
        async def worker():
            async with self.controller.lease("hung", estimated_vram_mib=1000):
                self.fail("hanging telemetry admitted")
        with self.assertRaises(GPUAdmissionError) as error:
            await asyncio.wait_for(worker(), timeout=.5)
        self.assertEqual(error.exception.reason, "telemetry_timeout")
        self.assertTrue(error.exception.retryable)
        self.assertTrue(entered.is_set())
        self.assertTrue(cancelled.is_set())
        scheduler = (await self.controller.snapshot())["scheduler"]
        self.assertEqual(scheduler["queued"], 0)
        self.assertEqual(scheduler["active"], 0)
        self.assertEqual(scheduler["reserved_mib"], 0)
        self.assertEqual(scheduler["rejected"], 1)
        self.assertEqual(scheduler["cancelled_waiters"], 0)
        async with self.controller.lease("next", estimated_vram_mib=1000):
            pass

    async def test_thermal_power_and_stale_readings_block(self):
        for value, expected in [(observed(temperature=85), "thermal_limit"),
                                (dict(observed(), age_s=30), "telemetry_stale"),
                                (dict(observed(), observed_at_unix=time.time()-30), "telemetry_stale")]:
            with self.subTest(expected=expected):
                self.source.value = value
                with self.assertRaises(GPUAdmissionError) as error:
                    async with self.controller.lease("model", estimated_vram_mib=1000):
                        self.fail("unhealthy admitted")
                self.assertEqual(error.exception.reason, expected)
        self.source.value = observed()
        self.source.value["gpu"]["power_w"] = 500
        with self.assertRaises(GPUAdmissionError) as error:
            async with self.controller.lease("model", estimated_vram_mib=1000):
                pass
        self.assertEqual(error.exception.reason, "power_limit")

    async def test_oversize_fails_without_waiting(self):
        with self.assertRaises(GPUAdmissionError) as error:
            async with self.controller.lease("model", estimated_vram_mib=20000):
                pass
        self.assertEqual(error.exception.reason, "vram_request_exceeds_profile")

    async def test_zero_increment_requires_actual_gpu_residency(self):
        with self.assertRaises(GPUAdmissionError) as error:
            async with self.controller.lease("model"):
                pass
        self.assertEqual(error.exception.reason, "vram_estimate_required")
        self.controller.update_residency([{"name": "model:latest", "size_vram": 2 * 1024 ** 3}])
        async with self.controller.lease("model") as token:
            self.assertEqual(token["reserved_mib"], 0)
            self.assertLessEqual(token["keep_alive_s"], 300)

    async def test_zero_estimate_still_obeys_profile_used_memory(self):
        self.controller.update_residency([{"name": "model", "size_vram": 2 * 1024 ** 3}])
        self.source.value = observed(used=19000)
        with self.assertRaises(GPUAdmissionError) as error:
            async with self.controller.lease("model"):
                pass
        self.assertEqual(error.exception.reason, "vram_pressure")

    async def test_realtime_observation_defers_background_not_audio(self):
        self.controller.record_realtime_observation(latency_ms=20, deadline_ms=10, underruns=1)
        with self.assertRaises(GPUAdmissionError) as error:
            async with self.controller.lease("background", estimated_vram_mib=1000):
                pass
        self.assertEqual(error.exception.reason, "realtime_pressure")
        async with self.controller.lease("audio", workload="audio", estimated_vram_mib=1000):
            pass

    async def test_realtime_queue_bypasses_blocked_background_head(self):
        self.controller.record_realtime_observation(latency_ms=20, deadline_ms=10)
        async def background():
            async with self.controller.lease("background", priority=0, estimated_vram_mib=1000):
                self.fail("background admitted during realtime pressure")
        task = asyncio.create_task(background())
        await self.wait_queued(1)
        async with self.controller.lease("audio", workload="audio", priority=20, estimated_vram_mib=1000):
            self.assertEqual((await self.controller.snapshot())["scheduler"]["active"], 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_queued_zero_estimate_rechecks_residency_at_admission(self):
        async def worker():
            async with self.controller.lease("model"):
                self.fail("expired residency admitted")
        with patch.object(self.controller.residency, "contains", side_effect=[True, False]):
            async with self.controller.lease("blocker", estimated_vram_mib=1000):
                task = asyncio.create_task(worker())
                await self.wait_queued(1)
            with self.assertRaises(GPUAdmissionError) as error:
                await task
        self.assertEqual(error.exception.reason, "vram_estimate_required")

    async def test_older_sample_cannot_admit_after_intervening_completed_lease(self):
        first_sample_started, release_first_sample = asyncio.Event(), asyncio.Event()
        calls = 0
        async def source():
            nonlocal calls
            calls += 1
            if calls == 1:
                first_sample_started.set()
                await release_first_sample.wait()
                return observed(used=4000)
            return observed(used=4000 if calls == 2 else 19000)
        self.controller.telemetry_provider = source
        async def low():
            async with self.controller.lease("low", priority=50, estimated_vram_mib=1000):
                self.fail("predecessor's stale sample admitted")
        low_task = asyncio.create_task(low())
        await first_sample_started.wait()
        async with self.controller.lease("high", priority=1, estimated_vram_mib=1000):
            pass
        release_first_sample.set()
        with self.assertRaises(GPUAdmissionError) as error:
            await low_task
        self.assertEqual(error.exception.reason, "vram_pressure")
        self.assertGreaterEqual(calls, 3)

    async def test_profile_changes_explicit_and_experimental_unavailable(self):
        await self.controller.set_profile("realtime")
        self.assertEqual((await self.controller.snapshot())["profile"]["vram_fraction"], .55)
        with self.assertRaises(GPUAdmissionError):
            await self.controller.set_profile("experimental")
        async with self.controller.lease("model", estimated_vram_mib=1000):
            with self.assertRaises(GPUAdmissionError) as error:
                await self.controller.set_profile("balanced")
            self.assertEqual(error.exception.reason, "profile_in_use")

    async def test_invalid_estimates_cannot_poison_accounting(self):
        for estimate in (float("nan"), float("inf"), -1, True):
            with self.subTest(estimate=estimate), self.assertRaises(ValueError):
                async with self.controller.lease("model", estimated_vram_mib=estimate):
                    pass
        self.assertEqual((await self.controller.snapshot())["scheduler"]["reserved_mib"], 0)

    async def test_repeated_same_model_requests_cannot_replace_active_budget(self):
        async def worker():
            async with self.controller.lease("same", estimated_vram_mib=4000):
                pass
        async with self.controller.lease("same", estimated_vram_mib=3000):
            task = asyncio.create_task(worker())
            await self.wait_queued(1)
            self.assertEqual((await self.controller.snapshot())["scheduler"]["reserved_mib"], 3000)
        await task


class TelemetryAndPolicyTests(unittest.TestCase):
    ROW = "0, GPU-id, NVIDIA GeForce RTX 4090, 0x268410DE, 581.0, stock, 24564, 4000, 20564, 50, 100, 450, 20\n"

    def test_csv_reports_actual_values_and_missing_fields_as_unknown(self):
        gpu = parse_nvidia_csv(self.ROW.replace(", 50,", ", [N/A],"))[0]
        self.assertEqual(gpu["memory_used_mib"], 4000)
        self.assertIsNone(gpu["temperature_c"])
        self.assertEqual(gpu["pci_device_id"], "0x268410DE")

    def test_subprocess_is_readonly_bounded_and_cached(self):
        with patch("gpu.gpu_telemetry.subprocess.run", return_value=Mock(returncode=0, stdout=self.ROW)) as runner:
            source = NvidiaSMITelemetry()
            first, second = source.read(), source.read()
            self.assertTrue(first["available"])
            self.assertEqual(runner.call_count, 1)
            command = runner.call_args.args[0]
            self.assertEqual(command[0], "nvidia-smi")
            self.assertTrue(command[1].startswith("--query-gpu="))
            self.assertNotIn("shell", runner.call_args.kwargs)
            self.assertEqual(runner.call_args.kwargs["timeout"], 3)
            second["gpu"]["memory_used_mib"] = 0
            self.assertEqual(source.read()["gpu"]["memory_used_mib"], 4000)
            source.read(fresh=True)
            self.assertEqual(runner.call_count, 2)

    def test_timeout_malformed_and_missing_device_are_unavailable(self):
        responses = [subprocess.TimeoutExpired("nvidia-smi", 3),
                     Mock(returncode=0, stdout="wrong,columns"),
                     Mock(returncode=0, stdout=self.ROW.replace("0, GPU-id", "1, GPU-id")),
                     Mock(returncode=1, stdout="")]
        for response in responses:
            with self.subTest(response=response):
                kwargs = {"side_effect": response} if isinstance(response, Exception) else {"return_value": response}
                with patch("gpu.gpu_telemetry.subprocess.run", **kwargs):
                    result = NvidiaSMITelemetry().read()
                    self.assertFalse(result["available"])
                    self.assertIsNone(result["gpu"])

    def test_residency_expires_and_cpu_models_are_not_gpu_resident(self):
        manager = ModelResidencyManager(max_age_s=10)
        with patch("gpu.model_residency.time.monotonic", side_effect=[100, 111]):
            manager.update([{"name": "model", "size_vram": 1000}])
            self.assertFalse(manager.contains("model"))
        manager = ModelResidencyManager()
        manager.update([{"name": "model", "size_vram": 0}])
        self.assertFalse(manager.contains("model"))

    def test_batching_preserves_input_and_order_without_truncation(self):
        inputs = ["abc", "def", "ghi", "jkl"]
        batches = build_embedding_batches(inputs, max_items=3, max_chars=6)
        self.assertEqual(batches, [["abc", "def"], ["ghi", "jkl"]])
        self.assertEqual([value for batch in batches for value in batch], inputs)
        self.assertEqual(len(adaptive_embedding_batches(inputs, available_mib=256)), 4)
        with self.assertRaises(ValueError):
            build_embedding_batches(["too long"], max_chars=2)

    def test_precision_cannot_override_ollama_or_claim_kernel_use(self):
        decision = precision_recommendation("chat", backend="ollama", requested="bf16", model_quantization="Q4_K_M")
        self.assertEqual(decision["precision"], "backend_managed")
        self.assertEqual(decision["model_quantization"], "Q4_K_M")
        self.assertFalse(decision["changed"])
        self.assertFalse(decision["tensor_core_use_verified"])
        with self.assertRaises(ValueError):
            precision_recommendation("matrix", backend="torch", supported=("fp16",), requested="bf16")

    def test_latency_percentiles_have_defined_empty_and_small_sample_behavior(self):
        self.assertIsNone(latency_summary([])["p99_ms"])
        self.assertEqual(latency_summary([10])["p95_ms"], 10)
        self.assertEqual(latency_summary([10, 20, 30])["p95_ms"], 29)


if __name__ == "__main__":
    unittest.main()
