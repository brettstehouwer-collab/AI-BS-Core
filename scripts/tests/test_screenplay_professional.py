"""Separate professional reflow: authored semantics, natural layout, safe provenance."""
import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import fitz
from reportlab.pdfgen.canvas import Canvas
from core.screenplay_pdf import parse_pdf


def engine():
    return importlib.import_module("core.screenplay_professional")


def packet_from_pages(pages):
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(612, 792), invariant=1)
    canvas.setFont("Courier", 12)
    canvas.drawString(252, 510, "Synthetic Title")
    canvas.drawString(264, 414, "Written by:")
    canvas.drawString(252, 400, "Fixture Author")
    canvas.showPage()
    x_by_role = {"Action": 114, "Scene Heading": 114, "Character": 270.24,
                 "Dialogue": 186, "Parenthetical": 229.2, "Transition": 430}
    for number, rows in enumerate(pages, 2):
        canvas.setFont("Courier", 12)
        canvas.drawString(525.6, 756, str(number) + ".")
        for role, text, y in rows:
            canvas.drawString(x_by_role[role], 792-y, text)
        canvas.showPage()
    canvas.save()
    return parse_pdf(output.getvalue())


def token_hash(texts):
    return hashlib.sha256("\n".join(word for text in texts for word in text.split()).encode("utf-8")).hexdigest()


def authored_pdf_tokens(raw, receipt):
    """Remove only exact known generated spans at their measured page/origin/hash."""
    annotations = receipt["generated_annotations"]
    result = []
    with fitz.open(stream=raw, filetype="pdf") as pdf:
        for number, page in enumerate(pdf, 1):
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        text = span["text"]
                        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
                        if any(row["page"] == number and row["text_sha256"] == digest
                               and abs(row["x"]-span["origin"][0]) < .1
                               and abs(row["y"]-span["origin"][1]) < .1 for row in annotations):
                            continue
                        result.extend(text.split())
    return result


class ProfessionalScreenplayTests(unittest.TestCase):
    def simple(self):
        return packet_from_pages([[('Scene Heading', 'INT. TEST ROOM - DAY', 61.2),
            ('Action', 'A <blue> & gold cup keeps its curly ’ punctuation.', 87.2),
            ('Character', 'MIRA', 113.2), ('Parenthetical', '(quietly)', 127.2),
            ('Dialogue', 'Keep every well-known word intact.', 141.2),
            ('Transition', 'CUT TO:', 167.2)], [('Action', 'The second source page stays editable.', 61.2)]])

    def test_distinct_profile_uses_template_positions_without_source_hard_breaks(self):
        packet = self.simple(); before = copy.deepcopy(packet)
        xml = ET.fromstring(engine().to_professional_fdx(packet))
        self.assertEqual(packet, before)
        self.assertFalse(any(p.get('StartsNewPage') == 'Yes' for p in xml.findall('./Content/Paragraph')))
        self.assertEqual(xml.find('HeaderAndFooter').get('StartingPage'), '1')
        self.assertEqual(xml.find('HeaderAndFooter').get('HeaderFirstPage'), 'No')
        self.assertEqual(xml.find('PageLayout').get('DocumentLeading'), 'Normal')
        settings = {row.get('Type'): row for row in xml.findall('ElementSettings')}
        self.assertEqual(settings['Dialogue'].find('ParagraphSpec').get('RightIndent'), '6.00')
        self.assertEqual(settings['Parenthetical'].find('ParagraphSpec').get('FirstIndent'), '-0.10')
        self.assertEqual(settings['Scene Heading'].find('ParagraphSpec').get('SpaceBefore'), '24')
        self.assertEqual(len(xml.findall('./TitlePage/Content/Paragraph')), 3)

    def test_words_punctuation_roles_and_literal_markup_survive_fdx(self):
        packet = self.simple(); xml = ET.fromstring(engine().to_professional_fdx(packet))
        actual = xml.findall('./Content/Paragraph')
        self.assertEqual([(p.get('Type'), ''.join(p.itertext())) for p in actual],
                         [(p['type'], p['text']) for p in packet['paragraphs']])
        self.assertEqual(token_hash(''.join(p.itertext()) for p in actual), packet['body_token_sha256'])
        self.assertEqual(xml.find('./MoresAndContinueds/DialogueBreaks').get('AutomaticCharacterContinueds'), 'No')
        self.assertEqual(xml.find('./MoresAndContinueds/DialogueBreaks').get('BottomOfPage'), 'Yes')

    def test_evidenced_action_boundary_wrap_joins_without_changing_role_tokens(self):
        packet = packet_from_pages([[('Action', 'The crew follows the long warehouse wall', 691.2),
            ('Action', 'carrying the recovered crate toward the entrance', 705.2)],
            [('Action', 'where the waiting truck remains unseen.', 61.2)]])
        xml = ET.fromstring(engine().to_professional_fdx(packet))
        self.assertEqual(len(xml.findall('./Content/Paragraph')), 1)
        receipt = engine().professional_profile_receipt(packet)
        self.assertEqual(receipt['merged_pdf_boundary_count'], 1)
        self.assertTrue(any(row['kind'] == 'pdf_boundary_join_inferred' for row in receipt['diagnostics']))
        self.assertEqual(token_hash(''.join(p.itertext()) for p in xml.findall('./Content/Paragraph')),
                         packet['body_token_sha256'])

    def test_ambiguous_boundary_and_unattributed_dialogue_are_retained(self):
        packet = packet_from_pages([[('Dialogue', 'This speech has no evidenced character', 705.2)],
            [('Dialogue', 'and must not receive an invented speaker.', 61.2)]])
        xml = ET.fromstring(engine().to_professional_fdx(packet))
        self.assertEqual(len(xml.findall('./Content/Paragraph')), 2)
        receipt = engine().professional_profile_receipt(packet)
        kinds = {row['kind'] for row in receipt['diagnostics']}
        self.assertIn('dialogue_speaker_unresolved', kinds)
        self.assertIn('ambiguous_pdf_boundary_retained', kinds)
        self.assertEqual(receipt['merged_pdf_boundary_count'], 0)
        self.assertNotIn('invented speaker', json.dumps(receipt))

    def test_character_context_never_jumps_across_action(self):
        packet = packet_from_pages([[('Character', 'MIRA', 600), ('Dialogue', 'A short speech.', 614),
            ('Action', 'The lights fail.', 640), ('Dialogue', 'this attribution is uncertain', 705.2)],
            [('Dialogue', 'and must remain unresolved.', 61.2)]])
        receipt = engine().professional_profile_receipt(packet)
        self.assertEqual(receipt['merged_pdf_boundary_count'], 0)
        self.assertTrue(any(row['kind'] == 'dialogue_speaker_unresolved' for row in receipt['diagnostics']))

    def test_sentence_end_boundary_is_not_silently_merged(self):
        packet = packet_from_pages([[('Action', 'A complete action ends here.', 705.2)],
                                   [('Action', 'another independent beat may start here.', 61.2)]])
        self.assertEqual(len(ET.fromstring(engine().to_professional_fdx(packet)).findall('./Content/Paragraph')), 2)
        self.assertEqual(engine().professional_profile_receipt(packet)['merged_pdf_boundary_count'], 0)

    def test_natural_pdf_reflows_and_does_not_restore_physical_breaks(self):
        packet = self.simple(); raw = engine().to_professional_pdf(packet)
        receipt = engine().professional_profile_receipt(packet)
        with fitz.open(stream=raw, filetype='pdf') as pdf:
            self.assertEqual(pdf.page_count, 2)  # Title plus naturally flowing one-page body.
            self.assertTrue(all((p.rect.width, p.rect.height) == (612, 792) for p in pdf))
            self.assertFalse(any(span['text'] == '1.' for block in pdf[1].get_text('dict')['blocks']
                                 for line in block.get('lines', []) for span in line['spans']))
        expected = [word for p in packet['title_paragraphs']+packet['paragraphs'] for word in p['text'].split()]
        self.assertEqual(authored_pdf_tokens(raw, receipt), expected)
        self.assertEqual(raw, engine().to_professional_pdf(packet))

    def test_long_dialogue_continuations_are_generated_and_authored_words_match(self):
        pages = [[('Character', 'MIRA', 61.2)] + [('Dialogue', 'the waiting workers carry crates toward the lobby', 87.2+14*i)
                 for i in range(44)], [('Dialogue', 'the waiting workers carry crates toward the lobby', 61.2+14*i)
                 for i in range(46)]]
        packet = packet_from_pages(pages); receipt = engine().professional_profile_receipt(packet)
        raw = engine().to_professional_pdf(packet)
        self.assertTrue(any(row['kind'] == 'dialogue_more' for row in receipt['generated_annotations']))
        self.assertTrue(any(row['kind'] == 'dialogue_continued' for row in receipt['generated_annotations']))
        self.assertGreater(receipt['internal_pdf_planned_body_page_count'], 1)
        expected = [word for p in packet['title_paragraphs']+packet['paragraphs'] for word in p['text'].split()]
        self.assertEqual(authored_pdf_tokens(raw, receipt), expected)
        with fitz.open(stream=raw, filetype='pdf') as pdf:
            self.assertEqual(pdf.page_count, receipt['internal_pdf_planned_page_count'])
            for page in pdf:
                for block in page.get_text('dict')['blocks']:
                    for line in block.get('lines', []):
                        for span in line['spans']:
                            self.assertGreaterEqual(span['bbox'][0], 0)
                            self.assertLessEqual(span['bbox'][2], 612)
                            self.assertLessEqual(span['bbox'][3], 792)

    def test_unbreakable_overflow_rejects_instead_of_clipping_or_rewriting(self):
        packet = packet_from_pages([[('Action', 'x'*65, 61.2)]])
        with self.assertRaises(ValueError): engine().to_professional_pdf(packet)

    def test_malformed_or_resealed_inconsistent_packets_are_rejected(self):
        packet = self.simple(); packet['paragraphs'][0]['text'] = 'changed'
        for function in ('to_professional_pdf', 'to_professional_fdx', 'professional_profile_receipt'):
            with self.subTest(function=function), self.assertRaises(ValueError):
                getattr(engine(), function)(packet)
        with self.assertRaises(ValueError): engine().to_professional_fdx({})

    def test_receipt_is_private_metadata_and_honest_about_pagination(self):
        packet = self.simple(); receipt = engine().professional_profile_receipt(packet)
        self.assertEqual(receipt['profile_id'], 'us-spec-courier12-v1')
        self.assertFalse(receipt['source_layout_preserved'])
        self.assertFalse(receipt['external_final_draft_verified'])
        self.assertFalse(receipt['vendor_certified'])
        self.assertIsNone(receipt['fdx_page_count'])
        self.assertEqual(receipt['authored_body_token_sha256'], packet['body_token_sha256'])
        serialized = json.dumps(receipt, allow_nan=False)
        self.assertNotIn('MIRA', serialized)
        self.assertNotIn('blue', serialized)


@unittest.skipUnless(os.environ.get('AIBS_SCREENPLAY_PDF_SOURCE'), 'Private source requires explicit opt-in path')
class ProvidedSourceProfessionalTests(unittest.TestCase):
    def test_actual_source_preserves_authored_content_without_page_count_claim(self):
        source_path = Path(os.environ['AIBS_SCREENPLAY_PDF_SOURCE']); original = source_path.read_bytes()
        packet = parse_pdf(original); before = copy.deepcopy(packet)
        fdx = engine().to_professional_fdx(packet); pdf = engine().to_professional_pdf(packet)
        receipt = engine().professional_profile_receipt(packet); xml = ET.fromstring(fdx)
        self.assertTrue(packet == before, 'Source packet changed during professional export')
        self.assertTrue(source_path.read_bytes() == original, 'Original source file changed')
        self.assertEqual(token_hash(''.join(p.itertext()) for p in xml.findall('./Content/Paragraph')), packet['body_token_sha256'])
        expected = [word for p in packet['title_paragraphs']+packet['paragraphs'] for word in p['text'].split()]
        self.assertTrue(authored_pdf_tokens(pdf, receipt) == expected,
                        'Professional PDF authored token readback changed; manuscript text is omitted from this log')
        self.assertEqual(receipt['source_page_count'], 86)
        self.assertEqual(receipt['authored_body_token_sha256'], 'f9865d30005925ddc9025ed35d59c6a78330df9075e9c44af121c61e01f57269')
        output = Path(os.environ['AIBS_SCREENPLAY_PROFESSIONAL_OUTPUT']); output.mkdir(parents=True, exist_ok=True)
        for name, data in [('professional.fdx', fdx), ('professional.pdf', pdf),
                           ('receipt.json', (json.dumps(receipt, indent=2)+'\n').encode('utf-8'))]:
            with (output/name).open('xb') as stream: stream.write(data)
        with fitz.open(stream=pdf, filetype='pdf') as document:
            for index in sorted({0, 1, len(document)//2, len(document)-1}):
                document[index].get_pixmap(matrix=fitz.Matrix(1.25, 1.25), alpha=False).save(str(output/f'page-{index+1:03}.png'))


if __name__ == '__main__': unittest.main()
