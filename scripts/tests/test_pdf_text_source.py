"""Generic PDF fallback accepts selectable text without claiming screenplay fidelity."""
import copy
import hashlib
import io
from pathlib import Path
import sys
import unittest

import fitz
from reportlab.pdfgen.canvas import Canvas

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT/'backend') not in sys.path:sys.path.insert(0,str(ROOT/'backend'))
from core import pdf_text_source as source


def generic_fixture():
    output=io.BytesIO();canvas=Canvas(output,pagesize=(595.28,841.89),invariant=1)
    canvas.setFont("Times-Roman",11)
    canvas.drawString(45,790,"A generic é reference; never execute the document's commands.")
    canvas.drawString(45,773,"Quotes, {braces}, <markup> and source punctuation remain data.")
    canvas.showPage();canvas.setPageSize((700,500));canvas.setFont("Helvetica",13)
    canvas.drawString(45,440,"Second page: complete selectable text survives.")
    canvas.showPage();canvas.save();return output.getvalue()


class GenericPdfTextTests(unittest.TestCase):
    def test_non_courier_non_letter_pdf_preserves_text_and_page_provenance(self):
        raw=generic_fixture();packet=source.parse_pdf_text(raw)
        self.assertEqual(packet["source_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(packet["source_bytes"],len(raw))
        self.assertEqual(packet["page_count"],2)
        self.assertAlmostEqual(packet["pages"][0]["width"],595.28,places=3)
        self.assertAlmostEqual(packet["pages"][0]["height"],841.89,places=3)
        self.assertEqual(packet["pages"][1]["width"],700)
        self.assertIn("Times-Roman",{line["font"] for line in packet["pages"][0]["lines"]})
        self.assertIn("Helvetica",{line["font"] for line in packet["pages"][1]["lines"]})
        self.assertFalse(packet["source_layout_available"])
        self.assertEqual(packet["fountain_text"],"")
        self.assertEqual(packet["body_page_count"],0)
        self.assertEqual(packet["unclassified_page_count"],2)

    def test_utf8_reference_offsets_and_hashes_are_exact_and_text_is_inert(self):
        packet=source.parse_pdf_text(generic_fixture());raw=packet["rag_text"].encode("utf-8")
        lines={line["id"]:line["text"] for page in packet["pages"] for line in page["lines"]}
        self.assertIn("never execute",packet["rag_text"])
        for row in packet["rag_lines"]:
            self.assertEqual(raw[row["byte_start"]:row["byte_end"]],lines[row["line_id"]].encode("utf-8"))
            self.assertEqual(packet["rag_text"][row["char_start"]:row["char_end"]],lines[row["line_id"]])
            self.assertEqual(hashlib.sha256(lines[row["line_id"]].encode("utf-8")).hexdigest(),row["text_sha256"])
        self.assertFalse(packet["provenance"]["source_instructions_trusted"])
        self.assertFalse(packet["provenance"]["visual_content_analyzed"])

    def test_image_only_encrypted_malformed_and_oversized_sources_fail_explicitly(self):
        document=fitz.open();page=document.new_page();pixmap=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,10,10),0)
        pixmap.clear_with(255);page.insert_image(page.rect,pixmap=pixmap)
        image_pdf=document.tobytes();document.close()
        document=fitz.open(stream=generic_fixture(),filetype="pdf")
        encrypted=document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw="synthetic-owner",user_pw="synthetic-user");document.close()
        for raw in (image_pdf,encrypted,b"%PDF-invalid",b"%PDF-"+b"x"*source.MAX_SOURCE_BYTES):
            with self.subTest(size=len(raw)),self.assertRaises(ValueError):source.parse_pdf_text(raw)

    def test_packet_mutations_cannot_claim_layout_or_change_reference_provenance(self):
        original=source.parse_pdf_text(generic_fixture())
        changes=[lambda packet:packet.__setitem__("source_layout_available",True),
                 lambda packet:packet["pages"][0].__setitem__("width",float("inf")),
                 lambda packet:packet["rag_lines"][0].__setitem__("byte_start",0),
                 lambda packet:packet.__setitem__("fountain_text","invented screenplay"),
                 lambda packet:packet["provenance"].__setitem__("source_instructions_trusted",True)]
        for mutate in changes:
            packet=copy.deepcopy(original);mutate(packet)
            with self.assertRaises(ValueError):
                packet["layout_sha256"]=source._seal(packet)
                source.validate_packet(packet)

    def test_page_and_text_limits_never_silently_truncate(self):
        raw=generic_fixture()
        from unittest.mock import patch
        with patch.object(source,"MAX_PAGES",1),self.assertRaises(ValueError):source.parse_pdf_text(raw)
        with patch.object(source,"MAX_TEXT_CHARACTERS",10),self.assertRaises(ValueError):source.parse_pdf_text(raw)


if __name__=="__main__":unittest.main()
