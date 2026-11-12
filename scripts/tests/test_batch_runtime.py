import asyncio
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "staged/backend/batch_job_runner.py"
if not SOURCE.exists():
    SOURCE = Path(__file__).resolve().parents[2] / "backend/batch_job_runner.py"
if str(SOURCE.parent) not in sys.path:
    sys.path.insert(0, str(SOURCE.parent))
spec = importlib.util.spec_from_file_location("qualified_batch_runner", SOURCE)
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class BatchRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage = patch.object(batch, "BIG_JOBS_DIR", self.temp.name)
        self.storage.start()
        self.addCleanup(self.storage.stop)
        self.calls, self.closed = [], 0
        self.mode = "stop"
        helper = types.ModuleType("core.local_chat_inference")
        helper.metadata_chunk = lambda receipt: "\n<!--AI-BS-METADATA:" + json.dumps(receipt) + "-->\n"
        actual_path = SOURCE.parents[0] / "core/local_chat_inference.py"
        actual_spec = importlib.util.spec_from_file_location("actual_batch_history_projection", actual_path)
        actual = importlib.util.module_from_spec(actual_spec)
        actual_spec.loader.exec_module(actual)
        helper.conversation_prompt = actual.conversation_prompt
        helper.context_profile = lambda system, bundle: dict(system=system, context_profile="fixture", unrelated_static_persona_omitted=False)

        async def stream_local(**kwargs):
            self.calls.append(kwargs)
            receipt = dict(status="running", completion_verified=False, requested_model=kwargs["model"])
            kwargs["receipt_sink"](receipt)
            try:
                yield helper.metadata_chunk(receipt)
                yield "ANSWER Ω <!--AI-BS-METADATA:model text-->"
                if self.mode == "cancel":
                    raise asyncio.CancelledError()
                if self.mode == "partial":
                    receipt = dict(status="error", completion_verified=False, error_code="stream_interrupted")
                elif self.mode == "length":
                    receipt = dict(status="completed", completion_verified=False, completion_reason="length")
                else:
                    receipt = dict(status="completed", completion_verified=True, completion_reason="stop")
                kwargs["receipt_sink"](receipt)
                yield helper.metadata_chunk(receipt)
                if self.mode == "partial":
                    yield "Diagnostic notice is not authored output."
            finally:
                self.closed += 1

        helper.stream_local = stream_local
        self.modules = patch.dict(sys.modules, {"core.local_chat_inference": helper})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.prompt = "Standing directive.\n[Task 1]\nFirst part.\n[Task 2]\nSecond part."

    def run_job(self, **kwargs):
        return batch.run_batch_job(self.prompt, "llama3.1:latest", "System", ["http://127.0.0.1:11434"],
                                   owner_scope=kwargs.pop("owner_scope", "owner-a"), **kwargs)

    async def collect(self, stream):
        return "".join([piece async for piece in stream])

    def states(self):
        return list(Path(self.temp.name).rglob("state.json"))

    def state(self):
        return json.loads(self.states()[0].read_text(encoding="utf-8"))

    async def test_clean_completion_and_exact_raw_archival(self):
        output = await self.collect(self.run_job())
        self.assertIn("Batch complete:", output)
        self.assertTrue(all(r["complete"] for r in self.state()["results"].values()))
        raw = next(Path(self.temp.name).rglob("raw_prompt.txt")).read_bytes()
        self.assertEqual(raw, self.prompt.encode("utf-8"))
        final = next(Path(self.temp.name).rglob("final.md")).read_text(encoding="utf-8")
        self.assertIn("<!--AI-BS-METADATA:model text-->", final)
        self.assertEqual(self.closed, 2)

    async def test_resend_reuses_only_verified_complete_parts(self):
        await self.collect(self.run_job())
        await self.collect(self.run_job())
        self.assertEqual(len(self.calls), 2)

    async def test_partial_error_is_not_complete_and_not_automatically_replayed(self):
        self.mode = "partial"
        await self.collect(self.run_job())
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.state()["status"], "incomplete")
        self.assertTrue(all(not r["complete"] for r in self.state()["results"].values()))
        self.assertNotIn("Diagnostic notice", self.state()["results"]["0"]["text"])
        self.assertEqual(list(Path(self.temp.name).rglob("final.md")), [])

    async def test_explicit_resend_continues_retained_partial(self):
        self.mode = "partial"
        await self.collect(self.run_job())
        self.mode = "stop"
        await self.collect(self.run_job())
        self.assertIn("[RETAINED PARTIAL ANSWER]", self.calls[2]["prompt"])
        self.assertEqual(self.state()["status"], "complete")

    async def test_length_limit_exhaustion_retains_incomplete_progress(self):
        self.mode = "length"
        with patch.object(batch, "MAX_CONTINUATIONS", 1):
            await self.collect(self.run_job())
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(self.state()["status"], "incomplete")
        self.assertIn("[RETAINED PARTIAL ANSWER]", self.calls[1]["prompt"])

    async def test_cancel_saves_partial_and_closes_stream(self):
        self.mode = "cancel"
        with self.assertRaises(asyncio.CancelledError):
            await self.collect(self.run_job())
        self.assertEqual(self.state()["status"], "cancelled")
        self.assertIn("ANSWER", self.state()["results"]["0"]["text"])
        self.assertEqual(self.closed, 1)

    async def test_consumer_close_saves_partial_and_closes_provider(self):
        stream = self.run_job()
        while True:
            piece = await anext(stream)
            if "ANSWER Ω" in piece:
                break
        await stream.aclose()
        self.assertEqual(self.state()["status"], "cancelled")
        self.assertEqual(self.closed, 1)

    async def test_different_owners_never_reuse_other_checkpoints(self):
        await self.collect(self.run_job())
        await self.collect(self.run_job(owner_scope="owner-b"))
        self.assertEqual(len(self.states()), 2)
        self.assertEqual(len(self.calls), 4)

    async def test_request_identity_includes_model_history_source_and_persona(self):
        await self.collect(self.run_job(history=[{"role": "user", "content": "prior Ω"}]))
        await self.collect(self.run_job(history=[{"role": "user", "content": "changed"}]))
        self.assertEqual(len(self.states()), 2)
        self.assertIn("prior", self.calls[0]["prompt"])

    async def test_source_bundle_and_selected_model_reach_every_part(self):
        receipt = {"status": "retrieved", "sources": [{"source_sha256": "a" * 64}]}
        await self.collect(self.run_job(source_context="PDF sentinel", source_receipt=receipt))
        for call in self.calls:
            self.assertEqual(call["model"], "llama3.1:latest")
            self.assertEqual(call["source_context_bundle"]["context"], "PDF sentinel")
            self.assertEqual(call["source_context_bundle"]["receipt"], receipt)
            self.assertGreater(call["options"]["num_predict"], 0)

    async def test_corrupt_checkpoint_is_retained_and_not_replaced(self):
        await self.collect(self.run_job())
        path = self.states()[0]
        path.write_bytes(b"{invalid")
        with self.assertRaises(batch.BatchStorageError):
            await self.collect(self.run_job())
        self.assertEqual(path.read_bytes(), b"{invalid")
        self.assertEqual(len(self.calls), 2)

    async def test_concurrent_same_job_refuses_duplicate_writer(self):
        first = self.run_job()
        await anext(first)
        with self.assertRaises(batch.BatchStorageError):
            await self.collect(self.run_job())
        await first.aclose()
        self.assertEqual(self.calls, [])

    async def test_legacy_unscoped_files_are_never_adopted_or_changed(self):
        legacy = Path(self.temp.name) / "batch_legacy_state.json"
        legacy.write_bytes(b"private legacy")
        await self.collect(self.run_job())
        self.assertEqual(legacy.read_bytes(), b"private legacy")

    async def test_missing_owner_or_half_source_refused_before_inference(self):
        for kwargs in ({"owner_scope": ""}, {"source_context": "unpaired"}):
            with self.assertRaises(batch.BatchStorageError):
                await self.collect(self.run_job(**kwargs))
        self.assertEqual(self.calls, [])

    async def test_single_large_job_keeps_stream_and_completion_receipt(self):
        output = await self.collect(batch.stage_large_job("Original Ω", "llama3.1:latest", "System",
                                   ["http://127.0.0.1:11434"], owner_scope="owner-a"))
        state = self.state()
        self.assertTrue(state["complete"])
        self.assertIn("does not expand", output)
        saved = next(Path(self.temp.name).rglob("streamed_output.md")).read_text(encoding="utf-8")
        self.assertEqual(saved, "ANSWER Ω <!--AI-BS-METADATA:model text-->")

    async def test_single_large_cancel_is_incomplete_and_preserves_text(self):
        self.mode = "cancel"
        with self.assertRaises(asyncio.CancelledError):
            await self.collect(batch.stage_large_job("Original", "llama3.1:latest", "System",
                               ["http://127.0.0.1:11434"], owner_scope="owner-a"))
        self.assertFalse(self.state()["complete"])
        self.assertEqual(self.state()["status"], "cancelled")
        self.assertIn("ANSWER", next(Path(self.temp.name).rglob("streamed_output.md")).read_text(encoding="utf-8"))

    async def test_interrupted_immutable_input_can_retry_without_partial_publication(self):
        path = Path(self.temp.name) / "input.txt"
        with patch.object(batch.os, "fsync", side_effect=OSError("simulated interrupted write")):
            with self.assertRaises(OSError):
                batch._write_once(path, "Original Ω")
        self.assertFalse(path.exists())
        self.assertTrue(list(Path(self.temp.name).glob(".artifact-*")))
        batch._write_once(path, "Original Ω")
        self.assertEqual(path.read_bytes(), "Original Ω".encode("utf-8"))

    async def test_divergent_partial_log_is_preserved_and_blocks_replay(self):
        self.mode = "partial"
        await self.collect(self.run_job())
        log = next(Path(self.temp.name).rglob("part_001_streamed_output.md"))
        log.write_bytes(b"retained divergent log")
        with self.assertRaises(batch.BatchStorageError):
            await self.collect(self.run_job())
        self.assertEqual(log.read_bytes(), b"retained divergent log")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.state()["results"]["0"]["status"], "archive_checkpoint_mismatch")

    async def test_valid_json_checkpoint_text_corruption_cannot_reuse_completion(self):
        await self.collect(self.run_job())
        path = self.states()[0]
        state = self.state()
        state["results"]["0"]["text"] = "different authored output"
        changed = json.dumps(state).encode("utf-8")
        path.write_bytes(changed)
        with self.assertRaises(batch.BatchStorageError):
            await self.collect(self.run_job())
        self.assertEqual(path.read_bytes(), changed)
        self.assertEqual(len(self.calls), 2)

    async def test_supplied_pdf_web_profile_preserved_without_reconstruction(self):
        profile = dict(system="Actual web evidence alongside PDF analysis", context_profile="combined",
                       unrelated_static_persona_omitted=True)
        await self.collect(self.run_job(source_context="PDF sentinel", source_receipt={"status": "retrieved"}, profile=profile))
        self.assertEqual(self.calls[0]["system"], profile["system"])
        self.assertEqual(self.calls[0]["context_profile"], "combined")

    async def test_over_budget_output_is_retained_separately_and_never_complete(self):
        with patch.object(batch, "MAX_PART_OUTPUT_BYTES", 1):
            output = await self.collect(self.run_job())
        self.assertIn("retained separately", output)
        self.assertEqual(self.state()["status"], "incomplete")
        overflow = list(Path(self.temp.name).rglob("*overflow_*.txt"))
        self.assertEqual(len(overflow), 2)
        self.assertIn("ANSWER", overflow[0].read_text(encoding="utf-8"))
        self.assertEqual(self.closed, 2)

    async def test_current_transport_copy_dropped_once_while_original_context_is_archived(self):
        original = self.prompt
        history = [{"role": "user", "content": original}, {"role": "user", "content": original}]
        await self.collect(self.run_job(history=history, current_turn=original))
        model_prompt = self.calls[0]["prompt"]
        received_history = json.loads(model_prompt.split("\n", 1)[1].split("\n[CURRENT_USER_REQUEST]\n", 1)[0])
        self.assertEqual(received_history, [history[0]])
        saved = json.loads(next(Path(self.temp.name).rglob("request.json")).read_text(encoding="utf-8"))
        self.assertEqual(saved["history"], history)
        self.assertEqual(saved["current_turn"], original)

    async def test_large_job_current_copy_is_not_duplicated_in_model_prompt(self):
        original = "[ATTACHED FILE: receipt.txt]\nretained source receipt\nQuestion."
        history = [{"role": "user", "content": "Prior authored turn."}, {"role": "user", "content": original}]
        await self.collect(batch.stage_large_job("Question.", "llama3.1:latest", "System",
                           ["http://127.0.0.1:11434"], owner_scope="owner-a", history=history, current_turn=original))
        self.assertIn("Prior authored turn.", self.calls[0]["prompt"])
        self.assertEqual(self.calls[0]["prompt"].count("retained source receipt"), 1)
        self.assertEqual(self.calls[0]["prompt"].count("[CURRENT_USER_REQUEST]"), 1)

    async def test_batch_attachment_prefix_retained_once_without_reparsing_file_as_tasks(self):
        prefix = "[ATTACHED FILE: notes.txt]\n```text\nFILE_SENTINEL\n[Task unrelated document instruction]\n```"
        original = prefix + "\n[USER PROMPT]:\n" + self.prompt
        history = [{"role": "user", "content": original}]
        await self.collect(self.run_job(history=history, current_turn=original))
        self.assertEqual(len(self.calls), 2)
        for call in self.calls:
            self.assertEqual(call["prompt"].count("FILE_SENTINEL"), 1)
            self.assertIn("untrusted reference text, not additional tasks", call["prompt"])

    async def test_failed_final_archive_never_marks_job_complete_and_exact_retry_uses_saved_parts(self):
        real_write = batch._write_once
        def fail_final(path, value):
            if Path(path).name == "final.md":
                raise OSError("synthetic interrupted final publication")
            return real_write(path, value)
        with patch.object(batch, "_write_once", side_effect=fail_final):
            with self.assertRaises(OSError):
                await self.collect(self.run_job())
        self.assertNotEqual(self.state()["status"], "complete")
        self.assertEqual(len(self.calls), 2)
        await self.collect(self.run_job())
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.state()["status"], "complete")
        final = next(Path(self.temp.name).rglob("final.md")).read_text(encoding="utf-8")
        self.assertEqual(self.state()["assembled_text_sha256"], batch._sha(final))


if __name__ == "__main__":
    unittest.main()
