"""Synthetic screenplay geometry and opt-in private-source roundtrip qualification."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import fitz
from PIL import Image, ImageChops
from reportlab.pdfgen.canvas import Canvas

ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / "backend/core/matrix_docs.py").is_file())
ENGINE_PATH = Path(os.environ.get("AIBS_SCREENPLAY_PDF_ENGINE", ROOT / "backend/core/screenplay_pdf.py"))
if not ENGINE_PATH.exists():
    ENGINE_PATH = Path(__file__).with_name("screenplay_pdf.py")
spec = importlib.util.spec_from_file_location("screenplay_pdf_fixture_engine", ENGINE_PATH)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def make_fixture(*, font="Courier", drawings=False, first_body_number=2):
    """Call only after the PDF-operation marker; returns synthetic PDF bytes."""
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(612, 792), invariant=1)
    canvas.setFont(font, 12)
    canvas.drawString(270, 792 - 277.2, "Synthetic Title")
    canvas.drawString(280, 792 - 377.6, "Written by:")
    canvas.drawString(270, 792 - 391.6, "Fixture Author")
    canvas.showPage()
    canvas.setFont(font, 12)
    for x, y, text in [(525.6, 36, f"{first_body_number}."), (114, 61.2, "INT. FIXTURE ROOM - DAY"),
                       (114, 87.2, "A <blue> & gold cup."), (114, 101.2, "The fixture retains curly ’ punctuation."),
                       (270.24, 127.2, "MIRA"), (229.2, 141.2, "(quietly)"),
                       (186, 155.2, "First wrapped dialogue line"), (186, 169.2, "second wrapped line."),
                       (526.8, 195.2, ".")]:
        canvas.drawString(x, 792-y, text)
    if drawings:
        canvas.rect(50, 50, 20, 20)
    canvas.showPage()
    canvas.setFont(font, 12)
    for x, y, text in [(525.6, 36, f"{first_body_number + 1}."), (114, 61.2, "EXT. FIXTURE STREET - NIGHT"),
                       (114, 87.2, "The last source line survives.")]:
        canvas.drawString(x, 792-y, text)
    canvas.showPage()
    canvas.save()
    return output.getvalue()


def pixel_differences(source, regenerated):
    results = []
    with fitz.open(stream=source, filetype="pdf") as left, fitz.open(stream=regenerated, filetype="pdf") as right:
        if left.page_count != right.page_count:
            raise AssertionError("Source and regenerated page counts differ")
        for index in range(left.page_count):
            a = left[index].get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            b = right[index].get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            difference = ImageChops.difference(Image.frombytes("RGB", (a.width, a.height), a.samples),
                                               Image.frombytes("RGB", (b.width, b.height), b.samples))
            changed = sum(difference.convert("L").point(lambda value: 255 if value else 0).histogram()[1:])
            results.append(dict(page=index+1, changed_pixels=changed, difference_bbox=difference.getbbox()))
    return results


class SyntheticScreenplayPdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = make_fixture()
        cls.packet = engine.parse_pdf(cls.source)

    def test_pdf_page_labels_title_and_logical_wrapping_are_preserved(self):
        packet = self.packet
        self.assertEqual((packet["page_count"], packet["title_page_count"], packet["body_page_count"]), (3, 1, 2))
        self.assertEqual([page["printed_label"] for page in packet["pages"]], ["", "2.", "3."])
        self.assertEqual(sum(p["starts_new_page"] for p in packet["paragraphs"]), 1)
        dialogue = [paragraph for paragraph in packet["paragraphs"] if paragraph["type"] == "Dialogue"]
        self.assertEqual(len(dialogue), 1)
        self.assertEqual(len(dialogue[0]["line_ids"]), 2)
        self.assertIn("second wrapped line.", dialogue[0]["text"])
        self.assertEqual(packet["source_sha256"], hashlib.sha256(self.source).hexdigest())
        self.assertTrue(any(warning["kind"] == "single_punctuation_line_preserved" for warning in packet["warnings"]))

    def test_derived_rag_offsets_and_hashes_match_exact_utf8_lines(self):
        packet = self.packet
        raw = packet["rag_text"].encode("utf-8")
        by_id = {line["id"]: line for page in packet["pages"] for line in page["lines"]}
        self.assertEqual(hashlib.sha256(raw).hexdigest(), packet["rag_sha256"])
        for row in packet["rag_lines"]:
            text = by_id[row["line_id"]]["text"]
            self.assertEqual(raw[row["byte_start"]:row["byte_end"]], text.encode("utf-8"))
            self.assertEqual(packet["rag_text"][row["char_start"]:row["char_end"]], text)
            self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), row["text_sha256"])

    def test_fdx_has_separate_title_standard_roles_and_real_page_break_attributes(self):
        xml = ET.fromstring(engine.to_fdx(self.packet))
        self.assertEqual(xml.tag, "FinalDraft")
        self.assertEqual(len(xml.findall("./TitlePage/Content/Paragraph")), 3)
        paragraphs = xml.findall("./Content/Paragraph")
        self.assertTrue(all(paragraph.get("Type") in engine.ROLES for paragraph in paragraphs))
        self.assertEqual(sum(p.get("StartsNewPage") == "Yes" for p in paragraphs), 1)
        self.assertEqual(engine._token_hash("".join(p.itertext()) for p in paragraphs), self.packet["body_token_sha256"])
        self.assertNotIn("Synthetic Title", " ".join("".join(p.itertext()) for p in paragraphs))
        self.assertIn("<blue> & gold", " ".join("".join(p.itertext()) for p in paragraphs))
        self.assertNotIn("Page Break", {p.get("Type") for p in paragraphs})
        self.assertEqual(engine.to_fountain(self.packet).count("\n===\n"), 1)

    def test_fdx_first_and_wrapped_lines_share_the_same_left_column(self):
        xml = ET.fromstring(engine.to_fdx(self.packet))
        settings = xml.findall("./ElementSettings")
        self.assertEqual({setting.get("Type") for setting in settings}, engine.ROLES)
        for setting in settings:
            with self.subTest(role=setting.get("Type")):
                paragraph = setting.find("ParagraphSpec")
                # Final Draft interprets FirstIndent relative to LeftIndent.
                wrapped_column = float(paragraph.get("LeftIndent"))
                first_column = wrapped_column + float(paragraph.get("FirstIndent"))
                self.assertEqual(first_column, wrapped_column)
                self.assertEqual(paragraph.get("FirstIndent"), "0")

    def test_fdx_separates_blocks_without_splitting_character_dialogue_groups(self):
        xml = ET.fromstring(engine.to_fdx(self.packet))
        before = {setting.get("Type"): setting.find("ParagraphSpec").get("SpaceBefore")
                  for setting in xml.findall("./ElementSettings")}
        for role in ("Action", "Scene Heading", "Character", "Transition"):
            with self.subTest(role=role):
                self.assertEqual(before[role], "12")
        for role in ("Dialogue", "Parenthetical"):
            with self.subTest(role=role):
                self.assertEqual(before[role], "0")

    def test_fdx_source_page_header_uses_contiguous_printed_numbering(self):
        xml = ET.fromstring(engine.to_fdx(self.packet))
        header = xml.find("HeaderAndFooter")
        self.assertIsNotNone(header)
        self.assertEqual({key: header.get(key) for key in
                          ("StartingPage", "HeaderFirstPage", "HeaderVisible", "FooterVisible")},
                         dict(StartingPage="2", HeaderFirstPage="Yes", HeaderVisible="Yes", FooterVisible="No"))
        paragraph = header.find("./Header/Paragraph")
        self.assertIsNotNone(paragraph.find("DynamicLabel[@Type='Page #']"))
        self.assertTrue(any(text.text == "." for text in paragraph.findall("Text")))
        self.assertIsNotNone(paragraph.find("./Tabstops/Tabstop[@Type='Right']"))
        offset_packet = engine.parse_pdf(make_fixture(first_body_number=7))
        offset = ET.fromstring(engine.to_fdx(offset_packet))
        self.assertEqual(offset.find("HeaderAndFooter").get("StartingPage"), "7")

    def test_fdx_disables_automatic_words_absent_from_the_source(self):
        xml = ET.fromstring(engine.to_fdx(self.packet))
        dialogue = xml.find("./MoresAndContinueds/DialogueBreaks")
        scenes = xml.find("./MoresAndContinueds/SceneBreaks")
        self.assertIsNotNone(dialogue)
        self.assertIsNotNone(scenes)
        for key in ("AutomaticCharacterContinueds", "BottomOfPage", "TopOfNext"):
            self.assertEqual(dialogue.get(key), "No")
        for key in ("ContinuedNumber", "SceneBottomOfPage", "SceneTopOfNext"):
            self.assertEqual(scenes.get(key), "No")

    def test_fdx_behavior_uses_supported_vendor_keyboard_attributes(self):
        xml = ET.fromstring(engine.to_fdx(self.packet))
        expected = {"Scene Heading": ("Action", "Action"), "Action": ("Action", "Character"),
                    "Character": ("Dialogue", "Transition"), "Parenthetical": ("Dialogue", "Dialogue"),
                    "Dialogue": ("Action", "Parenthetical"), "Transition": ("Scene Heading", "Scene Heading")}
        for setting in xml.findall("ElementSettings"):
            with self.subTest(role=setting.get("Type")):
                behavior = setting.find("Behavior")
                self.assertEqual((behavior.get("ReturnKey"), behavior.get("TabKey")), expected[setting.get("Type")])
                self.assertNotIn("ReturnCreates", behavior.attrib)
                self.assertNotIn("TabCreates", behavior.attrib)

    def test_regenerated_vector_pdf_has_matching_tokens_geometry_and_pixels(self):
        generated = engine.to_preserved_pdf(self.packet)
        self.assertEqual(generated, engine.to_preserved_pdf(self.packet), "Stable packets need idempotent export bytes")
        self.assertNotEqual(generated, self.source)
        recovered = engine.parse_pdf(generated)
        self.assertEqual(recovered["full_token_sha256"], self.packet["full_token_sha256"])
        self.assertEqual(recovered["page_count"], 3)
        with fitz.open(stream=generated, filetype="pdf") as document:
            self.assertTrue(all(not page.get_images(full=True) for page in document))
        self.assertTrue(all(row["changed_pixels"] == 0 for row in pixel_differences(self.source, generated)))

    def test_changed_rag_fountain_text_or_geometry_is_rejected_before_rendering(self):
        for field in ("rag_text", "fountain_text", "body_token_sha256"):
            changed = copy.deepcopy(self.packet)
            changed[field] += " changed"
            with self.subTest(field=field), patch.object(engine, "Canvas", side_effect=AssertionError("Must reject before PDF authoring")), self.assertRaises(ValueError):
                engine.to_preserved_pdf(changed)
        changed = copy.deepcopy(self.packet)
        changed["pages"][1]["lines"][0]["runs"][0]["x"] = 700
        with self.assertRaises(ValueError):
            engine.to_fdx(changed)

    def test_wrong_font_drawings_and_nonpdf_are_explicitly_unsupported(self):
        for data in (b"not a PDF", make_fixture(font="Helvetica"), make_fixture(drawings=True)):
            with self.subTest(source_bytes=len(data)), self.assertRaises(ValueError):
                engine.parse_pdf(data)

    def test_even_resealed_unsupported_glyph_control_and_overflow_packets_are_rejected(self):
        for text in ("unsupported Ω", "invalid\x00control"):
            changed = copy.deepcopy(self.packet)
            line = changed["pages"][0]["lines"][0]
            line["text"] = line["runs"][0]["text"] = text
            changed["layout_sha256"] = engine._seal(changed)
            with self.subTest(kind="glyph/control"), self.assertRaises(ValueError):
                engine.to_preserved_pdf(changed)
        changed = copy.deepcopy(self.packet)
        line = changed["pages"][0]["lines"][0]
        line["x"] = line["runs"][0]["x"] = 700
        changed["layout_sha256"] = engine._seal(changed)
        with self.assertRaises(ValueError):
            engine.to_preserved_pdf(changed)

    def test_resealed_derived_title_and_page_label_corruption_are_not_trusted(self):
        changes = [lambda packet: packet.__setitem__("title_page_count", 2),
                   lambda packet: packet["pages"][1].__setitem__("printed_label", "99."),
                   lambda packet: packet["rag_lines"][0].__setitem__("byte_start", 1),
                   lambda packet: packet.__setitem__("fountain_text", packet["fountain_text"] + "changed")]
        for change in changes:
            packet = copy.deepcopy(self.packet)
            change(packet)
            packet["layout_sha256"] = engine._seal(packet)
            with self.assertRaises(ValueError):
                engine.validate_packet(packet)

    def test_edited_canonical_text_cannot_claim_source_layout_fidelity(self):
        engine.validate_unchanged_fountain(self.packet, self.packet["fountain_text"])
        for changed in (self.packet["fountain_text"] + "\n", self.packet["fountain_text"].replace("cup", "bowl"), None):
            with self.subTest(kind=type(changed).__name__), self.assertRaises(ValueError):
                engine.validate_unchanged_fountain(self.packet, changed)


@unittest.skipUnless(os.environ.get("AIBS_SCREENPLAY_PDF_SOURCE"), "Private source qualification is explicitly selected")
class ActualSourceQualification(unittest.TestCase):
    def test_actual_source_fdx_and_regenerated_pdf_preserve_all_86_pages(self):
        source_path = Path(os.environ["AIBS_SCREENPLAY_PDF_SOURCE"])
        original = source_path.read_bytes()
        expected = "de381ec7053c00dcbf6ac025e0f234cea0466e026f45158edf8544b4f6badb4d"
        self.assertEqual(hashlib.sha256(original).hexdigest(), expected)
        packet = engine.parse_pdf(original)
        self.assertEqual((packet["page_count"], packet["title_page_count"], packet["body_page_count"]), (86, 1, 85))
        self.assertEqual(packet["body_word_count"], 15582)
        self.assertEqual(packet["body_token_sha256"], "f9865d30005925ddc9025ed35d59c6a78330df9075e9c44af121c61e01f57269")
        self.assertEqual([page["printed_label"] for page in packet["pages"]], [""] + [f"{number}." for number in range(2,87)])
        fdx = engine.to_fdx(packet)
        xml = ET.fromstring(fdx)
        body = xml.findall("./Content/Paragraph")
        self.assertEqual(sum(p.get("StartsNewPage") == "Yes" for p in body), 84)
        self.assertEqual(len(xml.findall("./TitlePage/Content/Paragraph")), 3)
        self.assertEqual(engine._token_hash("".join(p.itertext()) for p in body), packet["body_token_sha256"])
        regenerated = engine.to_preserved_pdf(packet)
        recovered = engine.parse_pdf(regenerated)
        self.assertEqual(recovered["full_token_sha256"], packet["full_token_sha256"])
        page_readbacks = []
        for before, after in zip(packet["pages"], recovered["pages"]):
            old_text = [line["text"] for line in before["lines"] if not line["is_page_number"]]
            new_text = [line["text"] for line in after["lines"] if not line["is_page_number"]]
            self.assertEqual(engine._token_hash(old_text), engine._token_hash(new_text))
            self.assertEqual(len(before["lines"]), len(after["lines"]))
            max_delta = 0
            for old_line, new_line in zip(before["lines"], after["lines"]):
                self.assertEqual(len(old_line["runs"]), len(new_line["runs"]))
                for old_run, new_run in zip(old_line["runs"], new_line["runs"]):
                    max_delta = max(max_delta, abs(old_run["x"] - new_run["x"]), abs(old_run["y"] - new_run["y"]),
                                    *(abs(a-b) for a,b in zip(old_run["bbox"],new_run["bbox"])))
            self.assertLessEqual(max_delta, .001)
            page_readbacks.append(dict(page=before["number"],text_tokens_match=True,
                token_sha256=engine._token_hash(old_text),max_geometry_delta_pt=max_delta))
        differences = pixel_differences(original, regenerated)
        self.assertTrue(all(row["changed_pixels"] == 0 for row in differences), "Regenerated page pixels differ; inspect private output")
        output = Path(os.environ["AIBS_SCREENPLAY_PDF_OUTPUT"])
        output.mkdir(parents=True, exist_ok=True)
        (output/"preserved.pdf").write_bytes(regenerated)
        (output/"screenplay.fdx").write_bytes(fdx)
        # Source-derived layout sidecar is local/private; never printed to chat logs.
        (output/"layout.json").write_text(json.dumps(packet,ensure_ascii=False),encoding="utf-8")
        with fitz.open(stream=regenerated,filetype="pdf") as document:
            for number in (1,2,12,39,43,86):
                document[number-1].get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False).save(output/f"page_{number:03d}.png")
        (output/"qualification.json").write_text(json.dumps(dict(source_sha256=expected,
            regenerated_sha256=hashlib.sha256(regenerated).hexdigest(),regenerated_bytes=len(regenerated),
            source_unchanged=hashlib.sha256(source_path.read_bytes()).hexdigest()==expected,
            physical_pages=86,title_pages=1,body_pages=85,body_words=15582,
            body_token_sha256=packet["body_token_sha256"],full_token_sha256=packet["full_token_sha256"],
            fdx_sha256=hashlib.sha256(fdx).hexdigest(),layout_sha256=packet["layout_sha256"],
            fdx_forced_body_page_breaks=84,render_differences=differences,
            page_readbacks=page_readbacks,max_geometry_delta_pt=max(row["max_geometry_delta_pt"] for row in page_readbacks),
            external_final_draft_pagination_verified=False,model_calls=False,ocr_used=False),indent=2),encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
