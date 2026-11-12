"""Inline selection scope is honest; durable RAG qualification is separate."""
import hashlib
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "staged/backend/core/sovereign_reasoning/document_engine.py"
if not SOURCE.exists():
    SOURCE = Path(__file__).resolve().parents[2] / "backend/core/sovereign_reasoning/document_engine.py"
spec = importlib.util.spec_from_file_location("actual_inline_document_engine", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
engine = module.SovereignDocumentEngine


class InlineDocumentScopeTests(unittest.TestCase):
    def attachment(self, content):
        return dict(content=content, filename="fixture.md", size_str="source text", ext="md")

    def test_short_full_text_reports_exact_unicode_text_scope(self):
        text = "# Scene\nΩ 😃\nExact punctuation—retained."
        result = engine.optimize_document_for_context(self.attachment(text), "read")
        self.assertIn(text, result)
        self.assertIn(f"{len(text.encode('utf-8')):,} UTF-8 bytes", result)
        self.assertIn(hashlib.sha256(text.encode("utf-8")).hexdigest(), result)
        self.assertIn("Full Inline Text", result)
        self.assertIn("not established", result)
        self.assertNotIn("Complete Ingestion", result)

    def test_large_sampling_preserves_legacy_windows_and_discloses_omission(self):
        text = "A" * 10000 + "UNSELECTED_SENTINEL" + "B" * 30000 + "C" * 10000
        result = engine.optimize_document_for_context(self.attachment(text), "overview")
        self.assertIn("A" * 6500, result)
        self.assertIn("B" * 6500, result)
        self.assertIn("C" * 6500, result)
        self.assertNotIn("UNSELECTED_SENTINEL", result)
        self.assertIn("Partial Inline Windows", result)
        self.assertIn("substantial source text is omitted", result)
        self.assertIn("not full-document review", result)
        self.assertNotIn("instantly retrieve", result)

    def test_target_section_extraction_is_retained_and_not_a_durable_index_claim(self):
        text = "# Chapter 1\n" + "x" * 23000 + "\n# Chapter 2\nExactly this selected section."
        result = engine.optimize_document_for_context(self.attachment(text), "chapter 2")
        self.assertIn("Exactly this selected section.", result)
        self.assertNotIn("x" * 100, result)
        self.assertIn("Selected 1 of 2 transient header sections", result)
        self.assertIn("Durable indexing", result)

    def test_payload_query_and_full_inline_content_still_reach_caller(self):
        raw = "[ATTACHED FILE: fixture.md (1 KB)]\n```md\nExact Ω source.\n```\n[USER PROMPT]:\nSummarize this."
        query, assembled = engine.prepare_chat_payload(raw)
        self.assertEqual(query, "Summarize this.")
        self.assertIn("Exact Ω source.", assembled)
        self.assertIn("[USER PROMPT]:\nSummarize this.", assembled)

    def test_multiple_explicit_numbers_do_not_select_generic_first_chapter(self):
        text = "# Chapter 1\n" + "x" * 23000 + "\n# Chapter 2\nSecond only.\n# Chapter 3\nThird only."
        result = engine.optimize_document_for_context(self.attachment(text), "chapter 2 and ch 3")
        self.assertIn("Second only.", result)
        self.assertIn("Third only.", result)
        self.assertNotIn("x" * 100, result)
        self.assertIn("Selected 2 of 3", result)

    def test_missing_requested_chapter_does_not_claim_it_was_extracted(self):
        text = "# Chapter 1\n" + "x" * 23000 + "\n# Chapter 2\nSecond only."
        result = engine.optimize_document_for_context(self.attachment(text), "chapter 99")
        self.assertIn("Partial Inline Windows", result)
        self.assertNotIn("Target Sections Extracted", result)


if __name__ == "__main__":
    unittest.main()
