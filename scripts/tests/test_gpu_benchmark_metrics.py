"""Offline benchmark evidence checks; no model, GPU or network execution."""
import hashlib
import json
from pathlib import Path
import ssl
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from gpu.benchmark_runner import ollama_metrics, summarize
from orchestrator.gpu_task_dispatcher import _LOCAL_HTTP_CONTEXT, local_ollama_host
from gpu.compute_scheduler import GPUAdmissionError


class BenchmarkMetricsTests(unittest.TestCase):
    def test_nan_negative_and_infinite_samples_cannot_enter_percentiles(self):
        for values in ([], [-1], [float("nan")], [float("inf")]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                summarize(values)
        self.assertEqual(summarize([1, 2, 3, 4, 5])["p95"], 4.8)

    def test_ollama_nan_zero_and_unavailable_durations_do_not_create_rates(self):
        for invalid in (None, 0, -1, True, float("nan"), float("inf"), "10"):
            with self.subTest(invalid=invalid):
                result = ollama_metrics({"eval_count": 10, "eval_duration": invalid,
                                         "load_duration": invalid}, .1)
                self.assertIsNone(result["decode_tokens_s"])
                if invalid != 0 or isinstance(invalid, bool):
                    self.assertIsNone(result["load_s"])
                json.dumps(result, allow_nan=False)

    def test_ns_conversion_cache_counts_and_output_fingerprint_are_separate(self):
        result = ollama_metrics({"response": "synthetic", "load_duration": 5_000_000,
            "prompt_eval_count": 100, "prompt_eval_cached_count": 99,
            "prompt_eval_duration": 2_000_000_000, "eval_count": 10,
            "eval_duration": 500_000_000}, 2.7)
        self.assertEqual(result["load_s"], .005)
        self.assertEqual(result["prefill_tokens_s"], 50)
        self.assertEqual(result["cached_tokens"], 99)
        self.assertEqual(result["decode_tokens_s"], 20)
        self.assertEqual(result["output_sha256"], hashlib.sha256(b"synthetic").hexdigest())
        self.assertNotIn("response", result)
        self.assertIn("no uncached-prefill claim", result["prefill_caveat"])

    def test_invalid_wall_or_response_is_rejected_and_missing_load_is_unknown(self):
        for invalid in (-1, True, float("nan"), float("inf"), None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                ollama_metrics({}, invalid)
        with self.assertRaises(ValueError):
            ollama_metrics({"response": {}}, 1)
        self.assertIsNone(ollama_metrics({}, 1)["load_s"])

    def test_local_metadata_context_avoids_ca_loading_without_disabling_verification(self):
        self.assertTrue(_LOCAL_HTTP_CONTEXT.check_hostname)
        self.assertEqual(_LOCAL_HTTP_CONTEXT.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(_LOCAL_HTTP_CONTEXT.cert_store_stats()["x509_ca"], 0)
        for endpoint in ("https://127.0.0.1:11434", "http://example.com:11434"):
            with self.subTest(endpoint=endpoint), self.assertRaises(GPUAdmissionError):
                local_ollama_host(endpoint)


if __name__ == "__main__":
    unittest.main()
