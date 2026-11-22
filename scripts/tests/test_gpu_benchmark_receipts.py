"""Offline receipt retention tests; CUDA, inventory, controller and HTTP are fake."""
import asyncio
import copy
from contextlib import asynccontextmanager, ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx

from scripts import adaptive_gpu_benchmark as benchmark


class FakeDispatcher:
    def __init__(self):
        self.active = 0
        self.released = 0

    @asynccontextmanager
    async def lease(self, *args, **kwargs):
        self.active += 1
        try:
            yield {"keep_alive_s": 300, "num_ctx": 2048, "num_batch": 512}
        finally:
            self.active -= 1
            self.released += 1


class FakeHTTP:
    def __init__(self):
        self.models = [{"name": "fixture:latest", "digest": "fixture-digest", "size": 1000,
                        "details": {"family": "fixture"}}]
        self.resident = []
        self.calls = []
        self.created = []
        self.active = 0
        self.generate_count = 0
        self.fail_at = None
        self.block_at = None
        self.blocked_cancelled = 0
        self.waiting = asyncio.Event()
        self.embedding_data = {"embeddings": [[.1, .2] for _ in range(8)], "total_duration": 1000000}

    def __call__(self, **kwargs):
        self.created.append(kwargs)
        return self

    async def __aenter__(self):
        self.active += 1
        return self

    async def __aexit__(self, *exc):
        self.active -= 1

    async def get(self, url):
        data = ({"models": self.models} if url.endswith("/api/tags") else
                {"models": self.resident} if url.endswith("/api/ps") else {"version": "fixture"})
        return httpx.Response(200, json=data, request=httpx.Request("GET", url))

    async def post(self, url, *, json):
        self.calls.append((url, copy.deepcopy(json)))
        self.generate_count += 1
        if self.generate_count == self.fail_at:
            raise httpx.ConnectError("SECRET exception text and raw request prompt")
        if self.generate_count == self.block_at:
            self.waiting.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.blocked_cancelled += 1
                raise
        data = {"done": True, "response": "SECRET generated output", "prompt_eval_count": 10,
                "prompt_eval_cached_count": 3, "prompt_eval_duration": 1000000,
                "eval_count": 4, "eval_duration": 1000000}
        if url.endswith("/api/embed"):
            data = self.embedding_data
        return httpx.Response(200, json=data, request=httpx.Request("POST", url))


class BenchmarkReceipts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aibs-benchmark-receipts-")
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "new-run"
        self.http = FakeHTTP()
        self.dispatcher = FakeDispatcher()
        self.controller = Mock()
        self.controller.snapshot = AsyncMock(return_value={"health": {"admission_available": True}})
        self.inventory = Mock(return_value={"fixture": True})
        self.matrix = Mock(return_value={"status": "measured", "fixture": True})
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, replacement in (("collect_inventory", self.inventory),
                                  ("cuda_matrix_benchmark", self.matrix),
                                  ("get_controller", Mock(return_value=self.controller)),
                                  ("OllamaDispatcher", Mock(return_value=self.dispatcher))):
            self.stack.enter_context(patch.object(benchmark, name, replacement))
        self.stack.enter_context(patch.object(benchmark.httpx, "AsyncClient", self.http))

    def receipt(self):
        return json.loads((self.output / "benchmark_results.json").read_text(encoding="utf-8"))

    def assert_no_diagnostics(self):
        self.inventory.assert_not_called()
        self.matrix.assert_not_called()
        self.controller.snapshot.assert_not_called()
        self.assertEqual(self.http.created, [])
        benchmark.OllamaDispatcher.assert_not_called()

    async def test_existing_receipt_is_refused_without_touching_bytes_or_hardware(self):
        self.output.mkdir()
        original = b'{"original":"receipt retained byte for byte"}\r\n'
        path = self.output / "benchmark_results.json"
        path.write_bytes(original)
        with self.assertRaises(FileExistsError):
            await benchmark.run(self.output, 3)
        self.assertEqual(path.read_bytes(), original)
        self.assert_no_diagnostics()

    async def test_existing_empty_directory_and_existing_file_are_refused(self):
        self.output.mkdir()
        occupied = Path(self.temp.name) / "occupied-file"
        occupied.write_bytes(b"original")
        for output in (self.output, occupied):
            with self.subTest(output=output), self.assertRaises(FileExistsError):
                await benchmark.run(output, 3)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertEqual(occupied.read_bytes(), b"original")
        self.assert_no_diagnostics()

    async def test_inventory_failure_has_safe_terminal_receipt(self):
        self.inventory.side_effect = ValueError("SECRET inventory failure")
        with self.assertRaises(ValueError):
            await benchmark.run(self.output, 3)
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["failures"], [{"exception_type": "ValueError", "stage": "inventory"}])
        self.assertIn("finished", receipt)
        self.assertNotIn("SECRET", json.dumps(receipt))
        self.matrix.assert_not_called()

    async def test_failed_matrix_keeps_inventory_and_before_checkpoint(self):
        self.matrix.side_effect = RuntimeError("SECRET CUDA diagnostic")
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 3)
        receipt = self.receipt()
        self.assertEqual(receipt["inventory"], {"fixture": True})
        self.assertTrue(receipt["before"]["health"]["admission_available"])
        self.assertEqual(receipt["failures"], [{"exception_type": "RuntimeError", "stage": "matrix"}])
        self.assertEqual(receipt["status"], "failed")
        self.assertNotIn("SECRET", json.dumps(receipt))
        self.assertEqual(self.http.calls, [])

    async def test_admission_failure_is_terminal_before_cuda_or_http(self):
        self.controller.snapshot.return_value = {"health": {"admission_available": False}}
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 3)
        receipt = self.receipt()
        self.assertFalse(receipt["before"]["health"]["admission_available"])
        self.assertEqual(receipt["failures"][0]["stage"], "before_snapshot")
        self.assertEqual(receipt["status"], "failed")
        self.matrix.assert_not_called()
        self.assertEqual(self.http.created, [])

    async def test_mid_trial_http_failure_retains_completed_samples_and_releases(self):
        self.http.fail_at = 4  # Two warmups, completed baseline, failed governed trial.
        with self.assertRaises(httpx.ConnectError):
            await benchmark.run(self.output, 3)
        receipt = self.receipt()
        self.assertEqual(len(receipt["llm"]["stock_baseline"]), 1)
        self.assertEqual(receipt["llm"]["stock_optimized"], [])
        self.assertEqual(receipt["failures"], [{"exception_type": "ConnectError",
                                               "stage": "llm_trial_0_stock_optimized"}])
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(self.dispatcher.active, 0)
        self.assertEqual(self.http.active, 0)
        self.assertNotIn("SECRET", json.dumps(receipt))
        self.assertNotIn("The test robot sorts", json.dumps(receipt))

    async def test_cancellation_records_terminal_stage_after_lease_cleanup(self):
        self.http.block_at = 4
        task = asyncio.create_task(benchmark.run(self.output, 3))
        await asyncio.wait_for(self.http.waiting.wait(), timeout=5)
        self.assertEqual(self.dispatcher.active, 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "cancelled")
        self.assertEqual(receipt["failures"], [{"exception_type": "CancelledError",
                                               "stage": "llm_trial_0_stock_optimized"}])
        self.assertEqual(self.dispatcher.active, 0)
        self.assertEqual(self.http.active, 0)
        self.assertEqual(len(receipt["llm"]["stock_baseline"]), 1)

    async def test_no_model_is_explicitly_incomplete_with_terminal_timestamp(self):
        self.http.models = []
        await benchmark.run(self.output, 3)
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "incomplete")
        self.assertIn("finished", receipt)
        self.assertEqual(receipt["llm"]["reason"], "no_bounded_installed_model")
        self.assertNotEqual(receipt["result"], "stock_smoke_benchmarks_complete_not_release_acceptance")
        self.assertEqual(self.http.calls, [])

    async def test_concurrent_failure_cancels_siblings_before_terminal_receipt(self):
        self.http.fail_at = 12  # After warmups, six paired samples and baseline concurrency.
        self.http.block_at = 13
        with self.assertRaises(httpx.ConnectError):
            await asyncio.wait_for(benchmark.run(self.output, 3), timeout=5)
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["failures"], [{"exception_type": "ConnectError",
                                               "stage": "concurrent_stock_optimized"}])
        self.assertIn("stock_baseline", receipt["concurrent_requests"])
        self.assertNotIn("stock_optimized", receipt["concurrent_requests"])
        self.assertEqual(self.http.blocked_cancelled, 1)
        self.assertEqual(self.dispatcher.active, 0)
        self.assertEqual(self.http.active, 0)

    async def test_terminal_storage_failure_preserves_last_commit_and_original_exception(self):
        self.http.fail_at = 4
        original_replace = benchmark.os.replace

        def reject_terminal(source, target):
            candidate = json.loads(Path(source).read_text(encoding="utf-8"))
            if candidate["status"] == "failed":
                raise PermissionError("SECRET terminal storage failure")
            original_replace(source, target)

        with patch.object(benchmark.os, "replace", side_effect=reject_terminal):
            with self.assertRaises(httpx.ConnectError) as caught:
                await benchmark.run(self.output, 3)
        committed = self.receipt()
        self.assertEqual(committed["status"], "running")
        self.assertEqual(len(committed["llm"]["stock_baseline"]), 1)
        candidates = [json.loads(path.read_text(encoding="utf-8"))
                      for path in self.output.glob(".benchmark_results.*.tmp")]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["status"], "failed")
        self.assertEqual(candidates[0]["failures"][0]["exception_type"], "ConnectError")
        self.assertNotIn("SECRET", json.dumps(candidates))
        self.assertIn("PermissionError", " ".join(caught.exception.__notes__))

    async def test_success_uses_matching_batch_options_and_atomic_checkpoints(self):
        commits = []
        original_replace = benchmark.os.replace

        def observe_replace(source, target):
            source, target = Path(source), Path(target)
            self.assertEqual(source.parent, self.output)
            self.assertEqual(target, self.output / "benchmark_results.json")
            commits.append(json.loads(source.read_text(encoding="utf-8")))
            original_replace(source, target)

        with patch.object(benchmark.os, "replace", side_effect=observe_replace):
            await benchmark.run(self.output, 3)
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["failures"], [])
        self.assertIn("finished", receipt)
        self.assertGreater(len(commits), 10)
        self.assertEqual(commits[0]["status"], "running")
        self.assertEqual(commits[-1], receipt)
        self.assertEqual(len(self.http.created), 1)
        self.assertEqual(self.http.created[0]["timeout"], 120.0)
        self.assertIs(self.http.created[0]["trust_env"], False)
        self.assertTrue(self.http.created[0]["verify"].check_hostname)
        self.assertIn("request", self.http.created[0]["event_hooks"])
        self.assertEqual(len(self.http.calls), 20)
        options = [payload["options"] for _, payload in self.http.calls]
        self.assertTrue(all(option["num_batch"] == 512 for option in options))
        self.assertTrue(all(option == options[0] for option in options))
        self.assertEqual(receipt["protocol"]["options"]["num_batch"], 512)
        caveats = " ".join(receipt["protocol"]["confounds"]).lower()
        self.assertIn("cache", caveats)
        self.assertIn("quality", caveats)
        self.assertNotIn("SECRET", json.dumps(receipt))
        self.assertNotIn("The test robot sorts", json.dumps(receipt))

    async def test_pinned_model_digest_and_llm_only_protocol_are_retained(self):
        await benchmark.run(self.output, 6, model_name="fixture:latest",
                            model_digest="fixture-digest", phases=("llm",))
        receipt = self.receipt()
        self.matrix.assert_not_called()
        self.assertEqual(receipt["model"]["name"], "fixture:latest")
        self.assertEqual(receipt["model"]["digest"], "fixture-digest")
        self.assertEqual(receipt["protocol"]["phases"], ["llm"])
        self.assertTrue(receipt["protocol"]["balanced_condition_order"])
        self.assertEqual(len(self.http.calls), 14)
        self.assertEqual(receipt["matrix"]["status"], "not_run")
        for sample in receipt["llm"]["stock_baseline"]:
            self.assertEqual(sample["admission_duration_s"], 0)
            self.assertGreaterEqual(sample["http_duration_s"], 0)
        for sample in receipt["llm"]["stock_optimized"]:
            self.assertGreaterEqual(sample["admission_duration_s"], 0)
            self.assertGreaterEqual(sample["http_duration_s"], 0)
        self.assertGreaterEqual(len(receipt["health_checks"]), 15)

    async def test_digest_mismatch_stops_before_matrix_or_model_work(self):
        with self.assertRaises(ValueError):
            await benchmark.run(self.output, 6, model_name="fixture:latest",
                                model_digest="different-digest")
        self.matrix.assert_not_called()
        self.assertEqual(self.http.calls, [])
        self.assertEqual(self.receipt()["halt_reason"], "model_digest_mismatch")

    async def test_other_resident_model_is_refused_before_any_gpu_work(self):
        self.http.resident = [{"name": "private-production:latest"}]
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 6, model_name="fixture:latest")
        self.matrix.assert_not_called()
        self.assertEqual(self.http.calls, [])
        receipt = self.receipt()
        self.assertEqual(receipt["halt_reason"], "nonbenchmark_model_resident")
        self.assertNotIn("private-production", json.dumps(receipt))

    async def test_health_pressure_after_warmup_stops_before_following_request(self):
        snapshots = 0

        async def observe():
            nonlocal snapshots
            snapshots += 1
            return {"health": {"admission_available": snapshots < 3,
                               "reason": "thermal_limit" if snapshots >= 3 else None}}

        self.controller.snapshot.side_effect = observe
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 6, phases=("llm",))
        self.assertEqual(len(self.http.calls), 1)
        self.assertEqual(self.receipt()["halt_reason"], "gpu_health_unavailable")
        self.assertEqual(self.dispatcher.active, 0)

    async def test_realtime_pressure_refuses_before_matrix_or_inference(self):
        self.controller.snapshot.return_value = {
            "health": {"admission_available": True}, "stability": {"realtime_pressure": True}}
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 6)
        self.matrix.assert_not_called()
        self.assertEqual(self.http.calls, [])
        self.assertEqual(self.receipt()["halt_reason"], "realtime_pressure")

    async def test_concurrency_balances_both_group_orders_without_serial_llm_phase(self):
        await benchmark.run(self.output, 6, phases=("concurrency",))
        receipt = self.receipt()
        self.matrix.assert_not_called()
        self.assertEqual(len(self.http.calls), 14)  # Two warmups and four groups of three.
        for condition in ("stock_baseline", "stock_optimized"):
            self.assertEqual(len(receipt["concurrent_requests"][condition]["rounds"]), 2)
            self.assertEqual(receipt["concurrent_requests"][condition]["requests"], 6)
        self.assertEqual(receipt["protocol"]["concurrent_condition_order"],
                         [["stock_baseline", "stock_optimized"],
                          ["stock_optimized", "stock_baseline"]])

    async def test_unknown_phase_fails_without_hardware_or_http(self):
        with self.assertRaises(ValueError):
            await benchmark.run(self.output, 6, phases=("unbounded",))
        self.inventory.assert_not_called()
        self.matrix.assert_not_called()
        self.assertEqual(self.http.created, [])

    async def test_matrix_only_needs_no_installed_model_and_never_posts(self):
        self.http.models = []
        await benchmark.run(self.output, 6, phases=("matrix",))
        self.matrix.assert_called_once_with(2048, 6)
        self.assertEqual(self.http.calls, [])
        self.assertEqual(self.receipt()["status"], "completed")

    async def test_terminal_pressure_cannot_write_completed_receipt(self):
        snapshots = 0

        async def observe():
            nonlocal snapshots
            snapshots += 1
            return {"health": {"admission_available": snapshots < 16}}

        self.controller.snapshot.side_effect = observe
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 6, phases=("llm",))
        receipt = self.receipt()
        self.assertEqual(len(self.http.calls), 14)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["failures"][0]["stage"], "after_snapshot")
        self.assertFalse(receipt["after"]["health"]["admission_available"])

    async def test_model_entering_residency_between_requests_stops_remaining_work(self):
        original_post = self.http.post

        async def post(url, *, json):
            response = await original_post(url, json=json)
            self.http.resident = [{"name": "private-production:latest"}]
            return response

        self.http.post = post
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 6, phases=("llm",))
        self.assertEqual(len(self.http.calls), 1)
        self.assertEqual(self.receipt()["halt_reason"], "nonbenchmark_model_resident")
        self.assertNotIn("private-production", json.dumps(self.receipt()))

    async def test_existing_resident_digest_must_match_the_pin(self):
        self.http.resident = [{"name": "fixture:latest", "digest": "older-digest"}]
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 6, model_name="fixture:latest",
                                model_digest="fixture-digest", phases=("llm",))
        self.assertEqual(self.http.calls, [])
        self.assertEqual(self.receipt()["halt_reason"], "resident_model_digest_mismatch")

    async def test_catalog_digest_change_between_requests_stops_remaining_work(self):
        original_post = self.http.post

        async def post(url, *, json):
            response = await original_post(url, json=json)
            self.http.models[0]["digest"] = "replacement-digest"
            return response

        self.http.post = post
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 6, phases=("llm",))
        self.assertEqual(len(self.http.calls), 1)
        self.assertEqual(self.receipt()["halt_reason"], "model_digest_changed")

    async def test_zero_available_budget_stops_before_any_gpu_work(self):
        self.controller.snapshot.return_value = {"health": {"admission_available": True},
                                                  "available_budget_mib": 0}
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 6)
        self.matrix.assert_not_called()
        self.assertEqual(self.http.created, [])
        self.assertEqual(self.receipt()["halt_reason"], "vram_pressure")

    async def test_even_serial_trials_execute_the_recorded_abba_order(self):
        observed = []
        original_post = self.http.post

        async def post(url, *, json):
            observed.append(self.dispatcher.active > 0)
            return await original_post(url, json=json)

        self.http.post = post
        await benchmark.run(self.output, 6, phases=("llm",))
        self.assertEqual(observed[:2], [False, True])
        self.assertEqual(observed[2:], [False, True, True, False] * 3)

    async def test_failed_matrix_numerical_validation_retains_measurement_and_halts(self):
        measurement = {"status": "measured", "dtypes": {"fp16": {"numerical_pass": False,
                         "relative_l2_error": .5, "tolerance": .002}}}
        self.matrix.return_value = measurement
        with self.assertRaises(RuntimeError):
            await benchmark.run(self.output, 6)
        receipt = self.receipt()
        self.assertEqual(receipt["matrix"], measurement)
        self.assertEqual(receipt["status"], "failed")
        self.assertEqual(receipt["halt_reason"], "matrix_numerical_check_failed")
        self.assertEqual(receipt["result"], "stock_smoke_benchmarks_failed_matrix_numerical_validation")
        self.assertEqual(self.http.calls, [])

    def enable_embeddings(self):
        self.http.models.append({"name": "nomic-embed-text:latest", "digest": "embed-digest", "size": 1000,
                                 "details": {"family": "nomic-bert"}})
        self.http.resident = [{"name": "fixture:latest", "digest": "fixture-digest"}]

    async def test_embedding_only_retains_pin_timing_and_health_without_llm_requests(self):
        self.enable_embeddings()
        await benchmark.run(self.output, 6, model_name="fixture:latest", model_digest="fixture-digest",
                            phases=("embeddings",))
        receipt = self.receipt()
        self.assertEqual(len(self.http.calls), 1)
        self.assertTrue(self.http.calls[0][0].endswith("/api/embed"))
        self.assertEqual(receipt["llm"]["status"], "not_run")
        self.assertEqual(receipt["embeddings"]["status"], "measured")
        self.assertTrue(receipt["embeddings"]["ordered_count_pass"])
        self.assertTrue(receipt["embeddings"]["vectors_valid"])
        self.assertGreaterEqual(receipt["embeddings"]["admission_duration_s"], 0)
        self.assertGreaterEqual(receipt["embeddings"]["http_duration_s"], 0)
        self.assertEqual([item["stage"] for item in receipt["health_checks"]],
                         ["before_snapshot", "embeddings", "after_snapshot"])
        self.matrix.assert_not_called()

    async def test_invalid_embedding_vectors_are_terminal_with_retained_safe_measurement(self):
        self.enable_embeddings()
        for index, vectors in enumerate((None, [], [[.1, .2]], [[.1], []] * 4,
                                         [["SECRET vector value"]] * 8, [[True]] * 8)):
            with self.subTest(vectors=vectors):
                self.output = Path(self.temp.name) / f"invalid-embedding-{index}"
                self.http.embedding_data = {"embeddings": vectors, "total_duration": 1000000}
                with self.assertRaises(RuntimeError):
                    await benchmark.run(self.output, 6, model_name="fixture:latest",
                                        model_digest="fixture-digest", phases=("embeddings",))
                receipt = self.receipt()
                self.assertEqual(receipt["status"], "failed")
                self.assertEqual(receipt["embeddings"]["status"], "failed")
                self.assertEqual(receipt["halt_reason"], "embedding_validation_failed")
                self.assertEqual(receipt["result"], "stock_smoke_benchmarks_failed_embedding_validation")
                self.assertNotIn("SECRET", json.dumps(receipt))
                self.assertEqual(self.dispatcher.active, 0)
                self.assertEqual(self.http.active, 0)

    def test_failed_atomic_replace_keeps_previous_receipt_and_candidate_evidence(self):
        self.output.mkdir()
        benchmark._save_receipt(self.output, {"checkpoint": "original"})
        path = self.output / "benchmark_results.json"
        original = path.read_bytes()
        with patch.object(benchmark.os, "replace", side_effect=PermissionError("SECRET filesystem error")):
            with self.assertRaises(PermissionError):
                benchmark._save_receipt(self.output, {"checkpoint": "next"})
        self.assertEqual(path.read_bytes(), original)
        candidates = list(self.output.glob(".benchmark_results.*.tmp"))
        self.assertEqual(len(candidates), 1)
        self.assertEqual(json.loads(candidates[0].read_text(encoding="utf-8")), {"checkpoint": "next"})


if __name__ == "__main__":
    unittest.main()
