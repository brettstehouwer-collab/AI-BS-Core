"""Actual project-RAG source with synthetic Chroma/projects and mocked local HTTP."""
import asyncio
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import httpx
from fastapi import HTTPException

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from core import project_rag as rag
from core import adaptation_store,fdx_source_documents
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from chromadb.errors import NotFoundError
OWNER='firebase:project-rag-fixture:A'
OTHER='firebase:project-rag-fixture:B'
sha=lambda text:hashlib.sha256(text.encode('utf-8')).hexdigest()

class Collection:
    def __init__(self,name):self.name=name;self.rows={};self.empty_query=False;self.corrupt=False;self.after_upsert=None
    def count(self):return len(self.rows)
    def upsert(self,ids,documents,metadatas,embeddings):
        for key,doc,meta,emb in zip(ids,documents,metadatas,embeddings):self.rows[key]=(doc,dict(meta),list(emb))
        if self.after_upsert:self.after_upsert()
    def get(self,ids=None,include=None,limit=None,**kw):
        keys=[key for key in (ids if ids is not None else self.rows) if key in self.rows]
        if limit is not None:keys=keys[:limit]
        return dict(ids=keys,documents=[self.rows[key][0]+('CORRUPT' if self.corrupt else '') for key in keys],
                    metadatas=[self.rows[key][1] for key in keys],embeddings=[self.rows[key][2] for key in keys])
    def query(self,query_embeddings,n_results,where=None,**kw):
        def matches(meta,expr):
            if not expr:return True
            if '$and' in expr:return all(matches(meta,item) for item in expr['$and'])
            return all(meta.get(key)==value for key,value in expr.items())
        keys=[] if self.empty_query else [key for key,row in self.rows.items() if matches(row[1],where)][:n_results]
        result=self.get(ids=keys)
        return dict(ids=[result['ids']],documents=[result['documents']],metadatas=[result['metadatas']],distances=[[.1]*len(keys)])

class Store:
    def __init__(self):self.collections={}
    def get_or_create_collection(self,name,**kw):return self.collections.setdefault(name,Collection(name))
    def get_collection(self,name):
        if name not in self.collections:raise NotFoundError('synthetic missing collection')
        return self.collections[name]

class ModelClient:
    def __init__(self,calls,fail=False):self.calls=calls;self.fail=fail
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def post(self,url,**kw):
        self.calls.append((url,kw))
        return httpx.Response(503 if self.fail else 200,json={'done':True,'done_reason':'stop','model':kw['json']['model'],'response':'Synthetic grounded answer.','message':{'content':'Synthetic grounded answer.'}},request=httpx.Request('POST',url))

class ProjectRagTakeoverTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='project-rag-',dir=ROOT/'t');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.project=self.root/'A-B';self.project.mkdir()
        (self.project/'screenplay.fountain').write_text('INT. STALE LEGACY ROOM - DAY\nSTALE_LEGACY_TEXT',encoding='utf-8')
        (self.project/'old.fdx').write_text('<FinalDraft><Content><Paragraph Type="Action"><Text>STALE_FDX_TEXT</Text></Paragraph></Content></FinalDraft>',encoding='utf-8')
        self.rich=dict(project='A-B',content='Title: Current\n\nCURRENT_RICH_BODY alpha',body_text='CURRENT_RICH_BODY alpha',
            body_blocks=[dict(id='block1',type='Action',text='CURRENT_RICH_BODY alpha')],revision=sha('xml v1'),
            source='rich_fdx',origin_sha256=sha('original rich xml'),owner_checked=True)
        self.rich.update(body_extraction_complete=True,body_extraction_warnings=[])
        self.store=Store();self.calls=[]
        from scripts.tests.test_local_chat_inference import Admission
        import importlib
        self.admission=Admission()
        shared=importlib.import_module('core.local_chat_inference')
        async def embedding(text,client=None,*,receipt_sink=None):return [.1,.2,.3]
        for setting in (patch.object(rag,'get_dispatcher',return_value=self.admission),patch.object(shared,'get_dispatcher',return_value=self.admission),patch.object(rag,'SCREENPLAY_ROOT',self.root),patch.object(rag,'get_chroma_client',return_value=self.store),
            patch.object(rag,'get_embedding_async',side_effect=embedding),
            patch.object(rag.httpx,'AsyncClient',side_effect=lambda **kw:ModelClient(self.calls)),
            patch.object(rag,'read_canonical_snapshot',side_effect=lambda directory,owner=None:self.rich),
            patch.multiple(adaptation_store,_root_provider=lambda:self.root,_store_mutex=threading.RLock(),_parser_factory=None)):
            setting.start();self.addCleanup(setting.stop)
        self.token=bind_memory_principal(OWNER);self.addCleanup(reset_memory_principal,self.token)

    def test_owner_and_exact_project_names_never_share_a_collection(self):
        first=rag.get_project_collection_name('A-B')
        self.assertNotEqual(first,rag.get_project_collection_name('AB'))
        token=bind_memory_principal(OTHER)
        try:self.assertNotEqual(first,rag.get_project_collection_name('A-B'))
        finally:reset_memory_principal(token)

    def test_fdx_parser_reads_current_body_only_not_title_or_script_notes(self):
        xml='<FinalDraft><Content><Paragraph Type="Action"><Text>BODY_ALPHA</Text></Paragraph></Content><TitlePage><Content><Paragraph><Text>TITLE_SECRET</Text></Paragraph></Content></TitlePage><ScriptNotes><Paragraph><Text>NOTE_SECRET</Text></Paragraph></ScriptNotes></FinalDraft>'
        text='\n'.join(row['text'] for row in rag.parse_fdx_content(xml))
        self.assertIn('BODY_ALPHA',text);self.assertNotIn('TITLE_SECRET',text);self.assertNotIn('NOTE_SECRET',text)

    async def test_rich_sync_uses_canonical_body_and_provenance_not_stale_projection(self):
        receipt=await rag.sync_project_screenplay('A-B')
        docs='\n'.join(row[0] for col in self.store.collections.values() for row in col.rows.values() if row[1].get('kind')=='source_chunk')
        self.assertIn('CURRENT_RICH_BODY',docs);self.assertNotIn('STALE',docs);self.assertNotIn('Title:',docs)
        self.assertTrue(receipt['receipt']['sources'][0]['revision']==self.rich['revision'])
        self.assertTrue(receipt['receipt']['complete'])

    async def test_foreign_project_is_denied_before_collection_or_embedding_access(self):
        (self.project/'source_pdf.json').write_text(json.dumps({'contract':'owned-pdf-source-v1','owner':OTHER}),encoding='utf-8')
        with self.assertRaises(HTTPException) as caught:await rag.sync_project_screenplay('A-B')
        self.assertEqual(caught.exception.status_code,403);self.assertEqual(self.store.collections,{})

    async def test_stale_revision_never_queries_old_context_or_generates_an_answer(self):
        await rag.sync_project_screenplay('A-B')
        self.rich={**self.rich,'revision':sha('xml v2'),'body_text':'NEW_CURRENT_CONTENT',
            'body_blocks':[dict(id='block1',type='Action',text='NEW_CURRENT_CONTENT')]}
        result=await rag.query_project_rag_assistant('A-B','alpha')
        self.assertEqual(result['status'],'stale_index');self.assertEqual(result['sources'],[]);self.assertEqual(self.calls,[])

    async def test_unsaved_projection_is_rejected_and_book_source_is_explicit(self):
        with self.assertRaises(HTTPException):await rag.sync_project_screenplay('A-B','UNSAVED_WRONG_DRAFT')
        (self.project/'chunks.json').write_text(json.dumps([{'text':'BOOK_ORIGINAL_BETA','chapter':'One'}]),encoding='utf-8')
        receipt=await rag.sync_project_screenplay('A-B')
        self.assertEqual({item['type'] for item in receipt['receipt']['sources']},{'rich_fdx','book_chunk'})

    async def test_empty_retrieval_and_model_errors_are_not_successful_answers(self):
        await rag.sync_project_screenplay('A-B')
        next(iter(self.store.collections.values())).empty_query=True
        result=await rag.query_project_rag_assistant('A-B','unmatched')
        self.assertEqual(result['status'],'no_matching_passages');self.assertEqual(self.calls,[])
        next(iter(self.store.collections.values())).empty_query=False
        with patch.object(rag.httpx,'AsyncClient',side_effect=lambda **kw:ModelClient(self.calls,fail=True)):
            with self.assertRaises(HTTPException):await rag.query_project_rag_assistant('A-B','alpha')

    async def test_embedding_failure_never_becomes_a_zero_vector(self):
        # Execute the actual embedding helper, not the setup fixture replacement.
        with patch.object(rag,'get_embedding_async',self.original_embedding):
            with self.assertRaises(HTTPException):await rag.get_embedding_async('alpha',ModelClient([],fail=True))

    async def test_source_change_during_indexing_publishes_no_complete_receipt(self):
        collection=self.store.get_or_create_collection(rag.get_project_collection_name('A-B'))
        collection.after_upsert=lambda:setattr(self,'rich',{**self.rich,'revision':sha('changed while indexing')})
        with self.assertRaises(HTTPException):await rag.sync_project_screenplay('A-B')
        self.assertFalse(any(row[1].get('kind')=='index_receipt' for row in collection.rows.values()))

    async def test_current_query_returns_checked_source_hashes_in_bounded_untrusted_context(self):
        await rag.sync_project_screenplay('A-B')
        result=await rag.query_project_rag_assistant('A-B','alpha')
        self.assertEqual(result['status'],'success')
        self.assertEqual(result['receipt']['sources'][0]['revision'],self.rich['revision'])
        self.assertTrue(result['sources'][0]['chunk_sha256'])
        payload=next(options['json'] for url,options in self.calls if url.endswith('/api/generate'))
        self.assertIn('Untrusted',payload['system'])
        self.assertIn('CURRENT_RICH_BODY',payload['system'])
        self.assertLessEqual(len(payload['system']),8000)

    def test_legacy_fdx_dual_dialogue_keeps_both_speakers_without_notes(self):
        from scripts.tests.test_fdx_source_documents import XML
        text='\n'.join(row['text'] for row in rag.parse_fdx_content(XML.decode('utf8')))
        for phrase in ('Bold & literal *stars*','Left','First voice.','Right','Second voice.'):
            self.assertIn(phrase,text)
        for phrase in ('NOTE ONLY','Literal *title*','HEADER'):self.assertNotIn(phrase,text)

    async def test_generation_completing_after_a_source_change_is_not_current_success(self):
        await rag.sync_project_screenplay('A-B')
        outer=self
        class ChangingModel(ModelClient):
            async def post(self,url,**kw):
                outer.rich={**outer.rich,'revision':sha('revision while generating')}
                return await super().post(url,**kw)
        with patch.object(rag.httpx,'AsyncClient',side_effect=lambda **kw:ChangingModel(self.calls)):
            with self.assertRaises(HTTPException) as error:await rag.query_project_rag_assistant('A-B','alpha')
        self.assertEqual(error.exception.status_code,409)

    async def test_retrieval_only_helper_has_current_evidence_and_never_generates(self):
        await rag.sync_project_screenplay('A-B')
        result=await rag.retrieve_project_context('A-B','alpha')
        self.assertEqual(result['status'],'success');self.assertEqual(self.calls,[])
        self.assertIn('CURRENT_RICH_BODY',result['context']);self.assertLessEqual(len(result['context']),6000)
        self.assertEqual(result['sources'][0]['source_index'],0)
        self.assertEqual(result['retrieval']['missing_source_indices'],[])

    async def test_actual_rich_owner_helper_and_current_xml_are_used(self):
        from scripts.tests.test_fdx_source_documents import XML
        project=self.root/'Actual Rich'
        fdx_source_documents.import_project(project,XML,OWNER,'1'*32)
        (project/'screenplay.fountain').write_text('STALE_RICH_PROJECTION',encoding='utf8')
        with patch.object(rag,'read_canonical_snapshot',fdx_source_documents.read_canonical_snapshot):
            result=await rag.sync_project_screenplay('Actual Rich')
            result=await rag.retrieve_project_context('Actual Rich','voice')
            self.assertIn('First voice.',result['context']);self.assertNotIn('NOTE ONLY',result['context'])
            self.assertNotIn('STALE_RICH',result['context']);self.assertNotIn('Literal *title*',result['context'])
            self.assertEqual(result['receipt']['sources'][0]['revision'],hashlib.sha256(XML).hexdigest())
            with self.assertRaises(HTTPException) as error:await rag.retrieve_project_context('Actual Rich','voice',owner=OTHER)
            self.assertEqual(error.exception.status_code,403)

    async def test_unknown_retained_rich_body_is_not_published_as_complete_index(self):
        from scripts.tests.test_fdx_source_documents import XML
        xml=XML.replace(b'</DualDialogue>',b'</DualDialogue><UnknownSection><Paragraph Type="Action"><Text>UNMAPPED BODY</Text></Paragraph></UnknownSection>')
        project=self.root/'Unknown Rich';fdx_source_documents.import_project(project,xml,OWNER,'2'*32)
        with patch.object(rag,'read_canonical_snapshot',fdx_source_documents.read_canonical_snapshot):
            with self.assertRaises(HTTPException) as error:await rag.sync_project_screenplay('Unknown Rich')
        self.assertEqual(error.exception.status_code,409);self.assertEqual(self.store.collections,{})

    async def test_saved_audio_transcript_has_explicit_hash_and_stale_detection(self):
        (self.project/'transcripts').mkdir();path=self.project/'transcripts'/'audio_transcript.txt'
        path.write_text('AUDIO_ORIGINAL gamma',encoding='utf8')
        result=await rag.sync_project_screenplay('A-B')
        audio=next(row for row in result['receipt']['sources'] if row['type']=='audio_transcript')
        self.assertEqual(audio['content_sha256'],sha('AUDIO_ORIGINAL gamma'))
        self.assertEqual(audio['source_file'],'transcripts/audio_transcript.txt')
        path.write_text('UPDATED_AUDIO gamma',encoding='utf8')
        result=await rag.query_project_rag_assistant('A-B','gamma')
        self.assertEqual(result['status'],'stale_index');self.assertEqual(self.calls,[])

    async def test_corrupt_index_and_foreign_query_rows_are_not_evidence(self):
        await rag.sync_project_screenplay('A-B');collection=next(iter(self.store.collections.values()))
        collection.corrupt=True
        with self.assertRaises(HTTPException):await rag.query_project_rag_assistant('A-B','alpha')
        self.assertEqual(self.calls,[]);collection.corrupt=False
        original=collection.query
        def foreign_rows(**kw):
            result=original(**kw);result['metadatas'][0][0]={**result['metadatas'][0][0],'owner_hash':sha(OTHER)}
            return result
        with patch.object(collection,'query',side_effect=foreign_rows):
            with self.assertRaises(HTTPException):await rag.query_project_rag_assistant('A-B','alpha')
        self.assertEqual(self.calls,[])

    async def test_cancellation_and_bad_embeddings_publish_no_complete_receipt(self):
        for vector in ([0.,0.,0.],[float('nan'),1.],[True,1.]):
            with patch.object(rag,'get_embedding_async',return_value=vector):
                with self.assertRaises(HTTPException):await rag.sync_project_screenplay('A-B')
        with patch.object(rag,'get_embedding_async',side_effect=asyncio.CancelledError):
            with self.assertRaises(asyncio.CancelledError):await rag.sync_project_screenplay('A-B')
        self.assertFalse(any(row[1].get('kind')=='index_receipt' for col in self.store.collections.values() for row in col.rows.values()))

    async def test_unicode_query_and_passages_have_conservative_input_and_output_budgets(self):
        self.rich={**self.rich,'body_text':'漢字'*600}
        await rag.sync_project_screenplay('A-B')
        result=await rag.query_project_rag_assistant('A-B','漢字')
        payload=self.calls[-1][1]['json']
        self.assertLessEqual(sum(len(item.encode('utf8')) for item in (payload['system'],payload['prompt'])),6000)
        self.assertEqual(payload['options']['num_predict'],1024)
        self.assertEqual(result['retrieval']['context_bytes'],len((await rag.retrieve_project_context('A-B','漢字'))['context'].encode('utf8')))
        self.calls.clear()
        result=await rag.query_project_rag_assistant('A-B','q'*4000)
        self.assertEqual(result['status'],'context_budget_exceeded');self.assertEqual(self.calls,[])
        self.assertEqual(result['retrieval']['candidate_passages'],1)
        with self.assertRaises(HTTPException) as error:await rag.query_project_rag_assistant('A-B','漢字'*2000)
        self.assertEqual(error.exception.status_code,422)

    original_embedding=staticmethod(rag.get_embedding_async)

if __name__=='__main__':unittest.main()
