"""Real extraction functions on generated source documents; no adaptation jobs."""
import ast
import asyncio
import hashlib
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
import fitz
import docx
from fastapi import File, HTTPException, UploadFile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))


def extractor(path=ROOT/'backend/core/ai_adapter.py'):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_extract_text_from_file')
    scope = dict(Path=Path, fitz=fitz, re=re, ET=ET, zipfile=zipfile)
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<actual-extractor>', 'exec'), scope)
    return scope[node.name]


class CreationImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.extract = extractor()

    def test_docx_includes_table_text_in_document_order(self):
        path = self.root/'fixture.docx'; d = docx.Document()
        d.add_paragraph('BEFORE'); table = d.add_table(rows=1, cols=1)
        table.cell(0, 0).text = 'TABLE EVIDENCE'; d.add_paragraph('AFTER'); d.save(path)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        text = self.extract(path)
        self.assertIn('TABLE EVIDENCE', text)
        self.assertLess(text.index('BEFORE'), text.index('TABLE EVIDENCE'))
        self.assertLess(text.index('TABLE EVIDENCE'), text.index('AFTER'))
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    def test_pdf_extracts_text_without_rewriting_source(self):
        path=self.root/'fixture.pdf'; d=fitz.open(); p=d.new_page()
        p.insert_text((50,50),'PDF fixture evidence'); d.save(path); d.close()
        before=path.read_bytes()
        self.assertIn('PDF fixture evidence',self.extract(path))
        self.assertEqual(path.read_bytes(),before)

    def test_document_editor_docx_import_uses_same_ordered_table_text(self):
        document=docx.Document();document.add_heading('Fixture heading',level=1)
        document.add_paragraph('BEFORE');document.add_table(rows=1,cols=1).cell(0,0).text='TABLE EVIDENCE'
        document.add_paragraph('AFTER');stream=io.BytesIO();document.save(stream)
        tree=ast.parse((ROOT/'backend/routers/document_converter_router.py').read_text(encoding='utf-8'))
        node=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='import_word_document')
        node.decorator_list=[]
        scope=dict(io=io,docx=docx,HTTPException=HTTPException,UploadFile=UploadFile,File=File)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-docx-import>', 'exec'),scope)
        async def read():return stream.getvalue()
        result=asyncio.run(scope[node.name](SimpleNamespace(read=read,filename='fixture.docx')))
        self.assertIn('# Fixture heading',result['content'])
        self.assertLess(result['content'].index('BEFORE'),result['content'].index('TABLE EVIDENCE'))
        self.assertLess(result['content'].index('TABLE EVIDENCE'),result['content'].index('AFTER'))

    def test_epub_extracts_spine_text(self):
        path=self.root/'fixture.epub'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
            z.writestr('META-INF/container.xml','<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
            z.writestr('book.opf','<package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Fixture</dc:title><dc:identifier id="id">fixture</dc:identifier><dc:language>en</dc:language></metadata><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="chapter"/></spine></package>')
            z.writestr('chapter.xhtml','<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Fixture</title></head><body><p>EPUB fixture evidence</p></body></html>')
        before=path.read_bytes()
        self.assertIn('EPUB fixture evidence',self.extract(path))
        self.assertEqual(path.read_bytes(),before)

    def test_markdown_and_fountain_remain_source_data(self):
        for suffix in ['.md','.fountain']:
            path=self.root/('fixture'+suffix); raw=b'Title: Fixture\r\n\r\nINT. ROOM - DAY\r\n\r\nA cup.\r\n'
            path.write_bytes(raw)
            self.assertIn('A cup.',self.extract(path)); self.assertEqual(path.read_bytes(),raw)

    def test_unreadable_binary_is_not_imported_as_gibberish(self):
        for suffix in ['.pdf','.epub','.docx']:
            path=self.root/('bad'+suffix);path.write_bytes(b'not a document')
            with self.assertRaises(ValueError):self.extract(path)


if __name__=='__main__': unittest.main()
