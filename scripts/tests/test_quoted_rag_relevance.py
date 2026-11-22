"""Actual retrieval over synthetic owned text/page mappings; no real PDF/model."""
from contextlib import closing, contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

ROOT=next(parent for parent in Path(__file__).resolve().parents if (parent/'backend/core/owned_vault.py').is_file())
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'backend'))
STAGE=Path(os.environ['AIBS_QUOTED_RAG_STAGE_ROOT']) if os.environ.get('AIBS_QUOTED_RAG_STAGE_ROOT') else ROOT
from core import personal_memory_scope as scope
from core import chat_pdf_sources as pdf
from core.pdf_text_source import _derived
import core
OWNER='firebase:quoted-rag-fixture:owner'
OTHER='firebase:quoted-rag-fixture:other'
HEADING='INT. COPPER GATE - RIVER PORT'
QUESTION='Locate “INT. COPPER GATE - RIVER PORT” in the attached PDF; quote the exact heading and report its physical PDF page.'


def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,STAGE/'backend/core'/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class QuotedRagRelevanceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='qr_',dir=ROOT/'t')
        self.directory=Path(temporary.name)
        assert self.directory.resolve().is_relative_to((ROOT/'t').resolve())
        self.addCleanup(temporary.cleanup);self.db=self.directory/'fixture.sqlite'
        with closing(sqlite3.connect(self.db)) as connection,connection:
            connection.execute('CREATE TABLE vault_items(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,content TEXT,collection TEXT,tags TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,item_hash TEXT)')
        self.rag=load('core.quoted_rag_fixture','owned_rag_sources.py')
        self.attached=load('core.quoted_attached_fixture','attached_source_context.py');self.sources={}
        for guard in (patch.object(pdf,'VAULT_DB_PATH',self.db),patch.object(pdf,'read_source',side_effect=self.read_source)):
            guard.start();self.addCleanup(guard.stop)

    @contextmanager
    def dependency(self):
        with patch.dict(sys.modules,{'core.owned_rag_sources':self.rag}),patch.object(core,'owned_rag_sources',self.rag,create=True):yield

    def read_source(self,owner,source_id,digest):
        value=self.sources.get((owner,source_id))
        if value is None or value[0]['source_sha256']!=digest:raise pdf.PDFSourceError('Synthetic owner/source mismatch',409)
        return value

    def source(self,pages,owner=OWNER):
        source_id=uuid.uuid4().hex;original=hashlib.sha256(('synthetic '+source_id).encode()).hexdigest()
        packet={'source_sha256':original,'pages':[{'number':i+1,'lines':[{'id':f'p{i+1}-l{n}','text':text} for n,text in enumerate(lines)]} for i,lines in enumerate(pages)]}
        content,mappings,_=_derived(packet);packet.update(rag_text=content,rag_lines=mappings)
        receipt=self.rag.ingest_source(self.db,owner,content,source_name='context_'+source_id+'.txt')
        manifest={'source_sha256':original,'derived_sha256':receipt['source_sha256'],'rag_receipt':receipt}
        self.sources[(owner,source_id)]=(manifest,packet,b'SYNTHETIC_NOT_A_PARSED_PDF')
        return {'source_id':source_id,'source_sha256':original},packet

    def crowded(self):
        pages=[['Synthetic title. '+'paper '*130],['At the copper gate the river approaches the port. '+'padding '*100],[HEADING,'Neutral '*85]]
        pages += [['Locate delegate riverside report point attached PDF. '*20] for _ in range(83)]
        return self.source(pages)

    def bundle(self,query,reference,max_chars=3500):
        token=scope.bind_memory_principal(OWNER)
        try:
            with self.dependency():return self.attached.attached_source_bundle(query,[reference],max_chars=max_chars)
        finally:scope.reset_memory_principal(token)

    def test_quoted_heading_beats_generic_instructions_and_substrings(self):
        reference,_=self.crowded();bundle=self.bundle(QUESTION,reference)
        self.assertIn(HEADING,bundle['context'])
        self.assertEqual(bundle['receipt']['passages'][0]['matched_pdf_pages'],[3])
        self.assertLess(bundle['receipt']['source_coverage'][0]['matching_passages'],5)
        self.assertLessEqual(len(bundle['context']),3500)

    def test_punctuation_match_retains_original_range_and_exact_page(self):
        reference,packet=self.crowded();bundle=self.bundle('Where is “COPPER GATE RIVER PORT”?',reference)
        passage=bundle['receipt']['passages'][0]
        self.assertEqual(passage['matched_pdf_pages'],[3]);self.assertIn(2,passage['pdf_pages'])
        raw=packet['rag_text'].encode('utf8')
        for match in passage['matched_ranges']:
            original=packet['rag_text'][match['char_start']:match['char_end']]
            self.assertIn('COPPER GATE - RIVER PORT',original)
            self.assertEqual(raw[match['byte_start']:match['byte_end']],original.encode('utf8'))
            self.assertEqual(hashlib.sha256(original.encode('utf8')).hexdigest(),match['sha256'])
        self.assertNotIn(HEADING,json.dumps(bundle['receipt']))

    def test_absent_quoted_phrase_does_not_fall_back_to_instructions(self):
        reference,_=self.crowded();bundle=self.bundle('Locate “ABSENT SILVER TOWER” in attached PDF; quote the page.',reference)
        self.assertEqual(bundle['receipt']['status'],'no_matching_passages')
        self.assertEqual(bundle['receipt']['returned_passages'],0)

    def test_whole_words_exclude_act_action_and_int_point(self):
        self.rag.ingest_source(self.db,OWNER,'Only action and point are present.',source_name='synthetic.txt')
        for query in ('act','int','"ACT"','“INT”'):self.assertEqual(self.rag.retrieve_source_chunks(self.db,OWNER,query),[])

    def test_owned_query_uses_same_quoted_focus(self):
        self.crowded();result=self.rag.retrieve_source_chunks(self.db,OWNER,QUESTION,limit=2,with_scope=True)
        self.assertIn(HEADING,result['results'][0]['content'])
        self.assertEqual(result['query_match']['mode'],'quoted_word_sequence')

    def test_named_source_does_not_override_missing_quoted_phrase(self):
        reference,_=self.crowded();name='context_'+reference['source_id']+'.txt'
        result=self.rag.retrieve_source_chunks(self.db,OWNER,name+' “ABSENT SILVER TOWER”',with_scope=True)
        self.assertEqual(result['results'],[]);self.assertEqual(result['search_scope'],'exact_named_owner_source')

    def test_unicode_casefold_retains_original_utf8_range(self):
        reference,packet=self.source([['Synthetic title'],['Straße – HAFEN']])
        bundle=self.bundle('Find "STRASSE HAFEN".',reference)
        match=bundle['receipt']['passages'][0]['matched_ranges'][0]
        self.assertEqual(packet['rag_text'][match['char_start']:match['char_end']],'Straße – HAFEN')
        self.assertEqual(hashlib.sha256(packet['rag_text'].encode()[match['byte_start']:match['byte_end']]).hexdigest(),match['sha256'])
        self.assertEqual(match['pdf_pages'],[2])

    def test_generated_page_markers_are_not_original_quoted_evidence(self):
        reference,_=self.source([['Only authored alpha']])
        self.assertEqual(self.bundle('Locate “PDF page” in the PDF.',reference)['receipt']['status'],'no_matching_passages')

    def test_foreign_and_stale_sources_are_not_substituted(self):
        foreign,_=self.source([[HEADING]],OTHER)
        with self.assertRaises(self.attached.AttachedSourceError):self.bundle(QUESTION,foreign)
        own,_=self.source([[HEADING]])
        with self.assertRaises(self.attached.AttachedSourceError):self.bundle(QUESTION,{**own,'source_sha256':'0'*64})

    def edge_source(self,word,start):
        prototype={'source_sha256':'0'*64,'pages':[{'number':1,'lines':[{'id':'synthetic-line','text':''}]}]}
        offset=_derived(prototype)[1][0]['char_start']
        return self.source([[' '*(start-offset)+word+' neutral '*200]])

    def test_action_cut_at_chunk_end_is_not_whole_act(self):
        reference,_=self.edge_source('action',1197)
        for query in ('act','“ACT”'):
            self.assertEqual(self.rag.retrieve_source_chunks(self.db,OWNER,query),[])
            self.assertEqual(self.bundle(query,reference)['receipt']['status'],'no_matching_passages')

    def test_point_cut_at_next_chunk_start_is_not_whole_int(self):
        reference,_=self.edge_source('point',1048)
        for query in ('int','“INT”'):
            self.assertEqual(self.rag.retrieve_source_chunks(self.db,OWNER,query),[])
            self.assertEqual(self.bundle(query,reference)['receipt']['status'],'no_matching_passages')

    def test_page_mapping_scans_full_line_table_once_per_matching_chunk(self):
        reference,packet=self.source([['alpha '*150]])
        class CountedLines(list):
            scans=0
            def __iter__(self):
                self.scans+=1
                return super().__iter__()
        lines=CountedLines(packet['rag_lines']);packet['rag_lines']=lines
        bundle=self.bundle('Find “alpha”.',reference)
        self.assertEqual(bundle['receipt']['status'],'retrieved')
        chunk_count=bundle['receipt']['sources'][0]['indexed_chunks']
        self.assertLessEqual(lines.scans,chunk_count)

    async def test_actual_local_helper_preserves_match_receipt_without_source_text(self):
        import httpx
        from scripts.tests.test_local_chat_inference import Admission
        reference,_=self.crowded();bundle=self.bundle(QUESTION,reference)
        helper=load('core.quoted_local_helper_fixture','local_chat_inference.py')
        calls=[];actual=httpx.AsyncClient;admission=Admission()
        def handler(request):
            calls.append(json.loads(request.content))
            return httpx.Response(200,json={'model':'fixture:latest','response':'Synthetic reply','done':True,'done_reason':'stop'})
        def client(**kwargs):return actual(transport=httpx.MockTransport(handler),**kwargs)
        with patch.object(helper,'get_dispatcher',return_value=admission),patch.object(helper.httpx,'AsyncClient',side_effect=client):
            result=await helper.complete_local(model='fixture:latest',prompt='Synthetic question',system='Synthetic system',
                endpoints=['http://127.0.0.1:11434/api/generate'],role='primary',source_context_bundle=bundle)
        receipt=result['receipt']['source_retrieval']
        self.assertEqual(receipt['passages'][0]['matched_pdf_pages'],[3])
        self.assertTrue(receipt['passages'][0]['matched_ranges'])
        self.assertEqual(receipt['query_match']['mode'],'quoted_word_sequence')
        self.assertNotIn(HEADING,json.dumps(result['receipt']))
        self.assertIn(HEADING,calls[0]['system']);self.assertEqual(len(calls),1);self.assertEqual(admission.released,1)


if __name__=='__main__':unittest.main(verbosity=2)
