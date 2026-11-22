"""Actual export parser on synthetic text, without importing backend startup."""
import ast
from dataclasses import dataclass
import html
from io import BytesIO
from pathlib import Path
import re
import typing
import unittest
import xml.etree.ElementTree as ET

from pypdf import PdfReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

ROOT = Path(__file__).resolve().parents[2]
tree = ast.parse((ROOT / 'backend/core/matrix_docs.py').read_text(encoding='utf-8'))
scope = dict(globals(), Optional=typing.Optional, List=typing.List, Dict=typing.Dict,
             Any=typing.Any, WEASYPRINT_AVAILABLE=False, REPORTLAB_AVAILABLE=True)
classes = [n for n in tree.body if isinstance(n, ast.ClassDef)
           and n.name in ('FountainElement', 'FountainParser')]
exec(compile(ast.Module(body=classes, type_ignores=[]), '<actual-fountain-parser>', 'exec'), scope)
Parser = scope['FountainParser']


class FountainExportTests(unittest.TestCase):
    def test_title_page_is_separate_from_body_preserving_source_and_line_numbers(self):
        text = ('Title: Blue & <Gold>\nCredit: Written by\nAuthors:\n'
                '    Mira\n\tEli\nSource: A notebook\nDraft date: 2026-10-25\n'
                'Contact:\n    Fictional Studio\nCustom field: Retained metadata\n\n'
                'INT. WORKSHOP - DAY\n\nA cup waits.\n')
        parser = Parser(text)
        self.assertEqual(parser.content, text)
        self.assertEqual(parser.title_page['authors'], 'Mira\nEli')
        self.assertEqual(parser.title_page['custom field'], 'Retained metadata')
        self.assertEqual(parser.elements[0].element_type, 'Scene Heading')
        self.assertEqual(parser.elements[0].line_number, 11)
        before = [(e.element_type, e.element_text, e.line_number) for e in parser.elements]
        parser.parse()
        self.assertEqual(before, [(e.element_type, e.element_text, e.line_number) for e in parser.elements])

    def test_dialogue_or_action_colons_do_not_start_a_title_page(self):
        for text in ('FADE IN:\n\nINT. ROOM - DAY\n', 'Warning: the cup is hot.\n\nMIRA\nReady.\n'):
            parser = Parser(text)
            self.assertEqual(parser.title_page, {})
            self.assertEqual(parser.elements[0].element_text, text.splitlines()[0])

    def test_pdf_uses_metadata_and_literal_body_not_markup(self):
        parser = Parser('Title: Blue & <Gold>\nAuthor: Mira & Eli\nContact: Fictional Studio\n\n'
                        'INT. ROOM - DAY\n\nA <b>literal</b> & blue cup.\n\nMIRA\n(quietly)\nCafé — ready.\n')
        pdf = PdfReader(BytesIO(parser.to_pdf('WRONG PROJECT FOLDER', 'Unknown')))
        self.assertEqual(len(pdf.pages), 2)
        title = pdf.pages[0].extract_text()
        body = pdf.pages[1].extract_text()
        self.assertIn('Blue & <Gold>', title)
        self.assertIn('Mira & Eli', title)
        self.assertIn('Fictional Studio', title)
        self.assertNotIn('WRONG PROJECT FOLDER', title)
        self.assertNotIn('Title:', body)
        self.assertNotIn('Author:', body)
        self.assertIn('A <b>literal</b> & blue cup.', body)
        self.assertIn('(quietly)', body)

    def test_long_pdf_title_lines_have_nonoverlapping_baselines(self):
        title = ' '.join(['LONG TITLE'] * 9)
        parser = Parser('INT. ROOM - DAY\n\nA cup.\n')
        pdf = PdfReader(BytesIO(parser.to_pdf(title, 'Fixture author')))
        state = {'size': 0, 'leading': 0}
        title_advances = []
        def visit(op, args, cm, tm):
            if op == b'Tf':
                state['size'] = float(args[1])
            elif op == b'TL':
                state['leading'] = float(args[0])
            elif op == b'T*' and state['size'] >= 23:
                title_advances.append(state['leading'])
        pdf.pages[0].extract_text(visitor_operand_before=visit)
        self.assertGreaterEqual(len(title_advances), 2)
        self.assertTrue(all(d >= 24 for d in title_advances), title_advances)

    def test_html_escapes_body_and_fdx_retains_title_and_parentheses(self):
        parser = Parser('Title: Blue & <Gold>\nAuthor: Mira\n\nINT. ROOM - DAY\n\n'
                        'A <img src="https://invalid.example/x"> & cup.\n\nMIRA\n(quietly)\nReady.\n')
        rendered = parser.to_html()
        self.assertNotIn('<img ', rendered)
        self.assertIn('&lt;img ', rendered)
        root = ET.fromstring(parser.to_fdx('WRONG', 'Unknown'))
        title = ' '.join(root.find('TitlePage').itertext())
        self.assertIn('Blue & <Gold>', title)
        self.assertIn('Mira', title)
        paragraphs = root.findall('./Content/Paragraph')
        self.assertFalse(any('Title:' in ''.join(p.itertext()) for p in paragraphs))
        parenthetical = next(p for p in paragraphs if p.get('Type') == 'Parenthetical')
        self.assertEqual(''.join(parenthetical.itertext()).strip(), '(quietly)')


if __name__ == '__main__':
    unittest.main()
