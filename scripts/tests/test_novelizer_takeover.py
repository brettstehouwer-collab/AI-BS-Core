"""Actual novelizer router with synthetic projects and offline mocked models only."""
import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError
import core.adaptation_store as adaptation_store
from routers.conversation_router import require_conversation_owner
from security.screenwriting_access import require_screenwriting_access


def invoke(function, *args, owner='owner-a', **kwargs):
    if 'owner' in inspect.signature(function).parameters: kwargs['owner'] = owner
    result = function(*args, **kwargs)
    return asyncio.run(result) if inspect.isawaitable(result) else result


class NovelizerTakeoverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.outer = Path(self.temp.name); self.root = self.outer/'projects'; self.root.mkdir()
        self.module = importlib.import_module('routers.novelizer_router')
        provider_patch=patch.object(self.module,'_provider_config',return_value={'providers':{'local':{'host':'http://127.0.0.1:11434','model':'fixture-model:small'}}},create=True)
        provider_patch.start();self.addCleanup(provider_patch.stop)
        class Admitted:
            enabled=True
            num_ctx=8192
            @asynccontextmanager
            async def lease(self,*args,**kwargs):
                if not self.enabled:yield {'gpu_admitted':False,'execution':'controller_disabled','keep_alive_s':300}
                else:yield {'gpu_admitted':True,'keep_alive_s':1,'num_ctx':self.num_ctx,'num_batch':64}
        self.dispatcher=Admitted();dispatcher_patch=patch.object(self.module,'get_dispatcher',return_value=self.dispatcher,create=True)
        dispatcher_patch.start();self.addCleanup(dispatcher_patch.stop)
        self.patch = patch.object(self.module, 'SCREENPLAY_ROOT', self.root); self.patch.start(); self.addCleanup(self.patch.stop)
        self.store_lock=threading.RLock()
        store_patch=patch.multiple(adaptation_store,_root_provider=lambda:self.root,
                                   _store_mutex=self.store_lock,_parser_factory=None)
        store_patch.start();self.addCleanup(store_patch.stop)
        self.project = self.root/'A project'; self.project.mkdir()
        (self.project/'screenplay.fountain').write_text('INT. CANONICAL ROOM - DAY\nA real fixture scene.', encoding='utf-8')

    def request(self, text='A retained draft.', **extra):
        return self.module.SaveDraftRequest(project_name='A project',chapter_number=1,
            chapter_title='Chapter One',prose_content=text,word_count=999999,**extra)

    def save(self, req): return invoke(self.module.save_novel_chapter_draft, req)

    def test_router_has_real_access_dependencies_and_anonymous_http_is_denied(self):
        app=FastAPI();app.include_router(self.module.router)
        async def denied(request:Request): raise HTTPException(403,'fixture denied')
        app.dependency_overrides[require_screenwriting_access]=denied
        app.dependency_overrides[require_conversation_owner]=denied
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://fixture') as client:
                return await client.get('/api/novelizer/styles')
        self.assertEqual(asyncio.run(run()).status_code,403)

    def test_all_local_model_failures_are_503_without_synthetic_prose(self):
        class Offline:
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            async def post(self,*args,**kwargs): raise httpx.ConnectError('offline fixture')
        with patch.object(self.module.httpx,'AsyncClient',return_value=Offline()):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(self.module._query_llm('synthetic scene','synthetic directive'))
        self.assertEqual(caught.exception.status_code,503)

    def test_memoir_directive_prohibits_invented_sensory_or_memories(self):
        directive=self.module.STYLE_PROFILES['memoir_first_person']['directive'].lower()
        self.assertIn('do not invent',directive)
        self.assertNotIn('smell of stale court coffee',directive)

    def test_canonical_source_precedes_main_and_missing_source_is_not_fabricated(self):
        (self.project/'main.fountain').write_text('INT. WRONG ROOM - DAY\nWrong draft.',encoding='utf-8')
        result=invoke(self.module.group_script_into_chapters,project_name='A project',script_content=None)
        self.assertIn('CANONICAL',result['chapters'][0]['combined_script'])
        for name in ('screenplay.fountain','main.fountain'): (self.project/name).unlink()
        with self.assertRaises(HTTPException) as caught:
            invoke(self.module.group_script_into_chapters,project_name='A project',script_content=None)
        self.assertEqual(caught.exception.status_code,404)

    def test_foreign_fenced_project_is_never_listed_grouped_or_saved(self):
        (self.project/'source_pdf.json').write_text(json.dumps(dict(contract='owned-pdf-source-v1',owner='owner-b')))
        self.assertEqual(invoke(self.module.get_novelizer_projects)['projects'],[])
        for fn,args in [(self.module.group_script_into_chapters,dict(project_name='A project',script_content=None)),
                        (self.module.get_project_novel_drafts,dict(project_name='A project'))]:
            with self.assertRaises(HTTPException) as caught: invoke(fn,**args)
            self.assertEqual(caught.exception.status_code,403)
        with self.assertRaises(HTTPException):self.save(self.request())
        self.assertFalse((self.project/'novel_adaptation').exists())

    def test_traversal_and_negative_chapter_are_rejected_before_writes(self):
        with self.assertRaises((HTTPException,ValidationError)):
            req=self.module.SaveDraftRequest(project_name='../escape',chapter_number=1,chapter_title='bad',prose_content='bad')
            self.save(req)
        self.assertFalse((self.outer/'escape').exists())
        with self.assertRaises(ValidationError):
            self.module.SaveDraftRequest(project_name='A project',chapter_number=-1,chapter_title='bad',prose_content='bad')

    def test_measured_word_count_revisions_and_exact_prior_raw_json_survive_updates(self):
        first=self.save(self.request());target=self.project/'novel_adaptation/chapter_01.json';raw=target.read_bytes()
        drafts=invoke(self.module.get_project_novel_drafts,project_name='A project')
        self.assertEqual(drafts['total_words'],3)
        self.assertEqual(drafts['chapters'][0]['revision'],first['revision'])
        self.save(self.request('A newer preserved draft.',expected_revision=first['revision']))
        saved=list((target.parent/'.versions/chapter_01').glob('*.json'))
        self.assertTrue(any(p.read_bytes()==raw for p in saved))
        self.assertNotEqual(target.read_bytes(),raw)

    def test_existing_chapter_requires_cas_and_concurrent_updates_have_one_winner(self):
        first=self.save(self.request())
        with self.assertRaises(HTTPException) as caught:self.save(self.request('Unsafely stale.'))
        self.assertEqual(caught.exception.status_code,428)
        def attempt(text):
            try:return self.save(self.request(text,expected_revision=first['revision']))['status']
            except HTTPException as error:return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,['Candidate A.','Candidate B.']))
        self.assertEqual(sorted(map(str,results)),['409','saved'])

    def test_retry_identifier_is_idempotent_and_cannot_be_reused_for_other_content(self):
        identifier='a'*32
        first=self.save(self.request(request_id=identifier));raw=(self.project/'novel_adaptation/chapter_01.json').read_bytes()
        second=self.save(self.request(request_id=identifier))
        self.assertEqual(first['revision'],second['revision'])
        self.assertEqual((self.project/'novel_adaptation/chapter_01.json').read_bytes(),raw)
        with self.assertRaises(HTTPException) as caught:self.save(self.request('Conflicting content.',request_id=identifier))
        self.assertEqual(caught.exception.status_code,409)

    def test_interrupted_atomic_update_keeps_original_and_retry_finishes(self):
        first=self.save(self.request());target=self.project/'novel_adaptation/chapter_01.json';raw=target.read_bytes()
        req=self.request('Interrupted but recoverable.',expected_revision=first['revision'],request_id='b'*32)
        with patch.object(self.module.os,'replace',side_effect=OSError('fixture replacement failure')):
            with self.assertRaises(HTTPException) as caught:self.save(req)
        self.assertEqual(caught.exception.status_code,503);self.assertEqual(target.read_bytes(),raw)
        self.assertTrue(list(target.parent.glob('.novel-*.tmp')))
        self.assertEqual(self.save(req)['status'],'saved')

    def test_corrupt_chapters_block_both_read_and_export_instead_of_disappearing(self):
        self.save(self.request());(self.project/'novel_adaptation/chapter_02.json').write_bytes(b'{broken')
        for fn,args in [(self.module.get_project_novel_drafts,dict(project_name='A project')),
            (self.module.export_full_book,dict(project_name='A project',book_title='Fixture',author_name='Author',format_type='markdown'))]:
            with self.assertRaises(HTTPException) as caught:invoke(fn,**args)
            self.assertEqual(caught.exception.status_code,409)

    def test_html_escapes_all_manuscript_and_title_fields(self):
        self.save(self.request('<script>inert prose</script> & words.'))
        response=invoke(self.module.export_full_book,project_name='A project',book_title='<img src=x>',author_name='<b>Author</b>',format_type='html_print')
        body=response.body.decode('utf-8')
        self.assertNotIn('<script>',body);self.assertNotIn('<img src=x>',body)
        self.assertIn('&lt;script&gt;',body);self.assertIn('&lt;b&gt;Author',body)

    def test_total_book_size_is_checked_before_a_new_chapter_can_make_it_unreadable(self):
        self.save(self.request());target=self.project/'novel_adaptation/chapter_01.json'
        with patch.object(self.module,'MAX_BOOK_BYTES',target.stat().st_size+100):
            req=self.module.SaveDraftRequest(project_name='A project',chapter_number=2,chapter_title='Two',prose_content='x'*500)
            with self.assertRaises(HTTPException) as caught:self.save(req)
            self.assertEqual(caught.exception.status_code,413)
            self.assertEqual(len(invoke(self.module.get_project_novel_drafts,project_name='A project')['chapters']),1)

    def test_legacy_numeric_filename_is_updated_in_place_instead_of_duplicated(self):
        first=self.save(self.request());target=self.project/'novel_adaptation/chapter_01.json'
        legacy=target.with_name('chapter_1.json');target.rename(legacy)
        with self.assertRaises(HTTPException):self.save(self.request('Do not create a duplicate.',expected_revision='missing'))
        self.save(self.request('A legacy chapter update.',expected_revision=first['revision']))
        self.assertFalse(target.exists());self.assertTrue(legacy.exists())
        self.assertEqual(len(invoke(self.module.get_project_novel_drafts,project_name='A project')['chapters']),1)

    def test_noop_request_identity_is_bound_and_cannot_later_write_other_content(self):
        first=self.save(self.request());self.save(self.request(request_id='c'*32))
        with self.assertRaises(HTTPException) as caught:
            self.save(self.request('A different payload.',request_id='c'*32,expected_revision=first['revision']))
        self.assertEqual(caught.exception.status_code,409)

    def test_owner_check_and_source_capture_share_the_store_lock(self):
        original=self.module._source
        def checked(*args,**kwargs):
            self.assertTrue(self.store_lock._is_owned(),'Source can be replaced between ownership validation and reading')
            return original(*args,**kwargs)
        with patch.object(self.module,'_source',side_effect=checked):
            invoke(self.module.group_script_into_chapters,project_name='A project',script_content=None)

    def test_lone_surrogate_in_legacy_json_is_a_corrupt_chapter_not_an_export_crash(self):
        self.save(self.request());target=self.project/'novel_adaptation/chapter_01.json'
        record=json.loads(target.read_bytes());record['prose_content']='\ud800'
        target.write_text(json.dumps(record,ensure_ascii=True),encoding='utf-8')
        with self.assertRaises(HTTPException) as caught:
            invoke(self.module.get_project_novel_drafts,project_name='A project')
        self.assertEqual(caught.exception.status_code,409)

    def test_configured_local_endpoint_and_selected_model_replace_shadow_port_default(self):
        with patch.dict(os.environ,{},clear=True):
            configuration=self.module._local_configuration()
        self.assertEqual(configuration['host'],'http://127.0.0.1:11434')
        self.assertEqual(configuration['model'],'fixture-model:small')
        self.assertEqual(configuration['fallback_policy'],'selected_local_model_only')

    def test_explicit_offline_shadow_override_is_preserved_without_host_fallback(self):
        with patch.dict(os.environ,{'OLLAMA_HOST_EDRIVE':'http://127.0.0.1:11435'},clear=True):
            configuration=self.module._local_configuration()
        self.assertEqual(configuration['host'],'http://127.0.0.1:11435')
        self.assertEqual(configuration['host_source'],'environment:OLLAMA_HOST_EDRIVE')

    def test_only_selected_model_runs_under_admission_and_receipt_reports_actual_model(self):
        self.dispatcher.num_ctx=2048
        calls=[]
        class Online:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def post(self,url,**kwargs):
                calls.append((url,kwargs['json']))
                return httpx.Response(200,json={'model':'fixture-model:small','response':'Synthetic prose only, produced by a mocked local model for this test.'})
        with patch.dict(os.environ,{},clear=True),patch.object(self.module.httpx,'AsyncClient',return_value=Online()):
            result=asyncio.run(self.module._query_llm('fixture source','fixture directive',max_output_tokens=16))
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][0],'http://127.0.0.1:11434/api/generate')
        self.assertEqual(calls[0][1]['model'],'fixture-model:small');self.assertEqual(calls[0][1]['options']['num_ctx'],2048)
        self.assertEqual(result['model'],'fixture-model:small');self.assertTrue(result['generation_verified'])

    def test_disabled_adaptive_controller_preserves_selected_model_call_without_false_admission(self):
        self.dispatcher.enabled=False
        calls=[]
        class Online:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def post(self,url,**kwargs):
                calls.append(kwargs['json'])
                return httpx.Response(200,json={'model':'fixture-model:small','response':'Synthetic controller-disabled fixture prose.','done':True,'done_reason':'stop'})
        with patch.dict(os.environ,{},clear=True),patch.object(self.module.httpx,'AsyncClient',return_value=Online()):
            result=asyncio.run(self.module._query_llm('fixture source','fixture directive',max_output_tokens=16))
        self.assertEqual(len(calls),1);self.assertEqual(calls[0]['model'],'fixture-model:small')
        self.assertEqual(calls[0]['options']['num_predict'],16)
        self.assertFalse(result['admission']['gpu_admitted']);self.assertEqual(result['admission']['execution'],'controller_disabled')

    def test_rich_source_uses_latest_typed_canonical_body_and_its_owner_fence(self):
        from core import fdx_source_documents as fdx
        path=self.root/'Rich project'
        raw=b'<FinalDraft Version="3"><Content><Paragraph Type="Scene Heading"><Text>UNUSUAL RICH HEADING</Text></Paragraph><Paragraph Type="Action"><Text>Original action.</Text><ScriptNote><Paragraph><Text>PRIVATE NOTE ONLY</Text></Paragraph></ScriptNote></Paragraph></Content><TitlePage><Content><Paragraph Type="Title"><Text>TITLE ONLY</Text></Paragraph></Content></TitlePage></FinalDraft>'
        first=fdx.import_project(path,raw,'owner-a','d'*32);document=first['fdx_document'];block=document['blocks'][1]
        old=block['text'];block['text']=old+' NEW';block['edit_operations']=[dict(id='e'*32,before_text=old,start=len(old),end=len(old),text=' NEW')]
        updated=fdx.write_project(path,fdx.projection(document),first['revision'],document,owner='owner-a')
        (path/'screenplay.fountain').write_text('STALE LEGACY MIRROR',encoding='utf-8')
        result=invoke(self.module.group_script_into_chapters,project_name='Rich project',script_content=None)
        self.assertEqual(result['source_revision'],updated['revision']);self.assertEqual(result['total_scenes'],1)
        self.assertEqual(result['chapters'][0]['scenes'][0]['heading'],'UNUSUAL RICH HEADING')
        self.assertIn('NEW',result['chapters'][0]['combined_script']);self.assertNotIn('STALE',result['chapters'][0]['combined_script'])
        self.assertNotIn('PRIVATE NOTE',result['chapters'][0]['combined_script']);self.assertNotIn('TITLE ONLY',result['chapters'][0]['combined_script'])
        self.assertFalse(any(p['name']=='Rich project' for p in invoke(self.module.get_novelizer_projects,owner='owner-b')['projects']))
        with self.assertRaises(HTTPException) as caught:invoke(self.module.get_project_novel_drafts,project_name='Rich project',owner='owner-b')
        self.assertEqual(caught.exception.status_code,403)

    def test_explicit_empty_model_override_is_not_silently_replaced(self):
        with patch.dict(os.environ,{'NOVELIZER_MODEL':''},clear=True):
            with self.assertRaises(HTTPException):self.module._local_configuration()

    def test_unknown_legacy_metadata_survives_a_revisioned_update(self):
        self.save(self.request());target=self.project/'novel_adaptation/chapter_01.json'
        record=json.loads(target.read_bytes());record['author_notes']={'fixture':'retain exactly'}
        target.write_text(json.dumps(record),encoding='utf-8');revision=hashlib.sha256(target.read_bytes()).hexdigest()
        self.save(self.request('An edited manuscript.',expected_revision=revision))
        self.assertEqual(json.loads(target.read_bytes())['author_notes'],record['author_notes'])

    def test_duplicate_json_keys_are_corrupt_instead_of_silently_choosing_prose(self):
        self.save(self.request());target=self.project/'novel_adaptation/chapter_01.json'
        target.write_text('{"chapter_number":1,"chapter_title":"One","prose_content":"Keep first","prose_content":"Drop first"}')
        with self.assertRaises(HTTPException) as caught:invoke(self.module.get_project_novel_drafts,project_name='A project')
        self.assertEqual(caught.exception.status_code,409)

    def test_linked_novel_storage_is_rejected_without_touching_the_destination(self):
        destination=self.outer/'outside';destination.mkdir()
        link=self.project/'novel_adaptation';link.symlink_to(destination,target_is_directory=True)
        with self.assertRaises(HTTPException):self.save(self.request())
        self.assertEqual(list(destination.iterdir()),[])

    def test_supplied_editor_script_must_match_the_selected_project(self):
        with self.assertRaises(HTTPException) as caught:
            invoke(self.module.group_script_into_chapters,project_name='A project',script_content='INT. WRONG - DAY',script_project_name='Different project')
        self.assertEqual(caught.exception.status_code,422)

    def test_http_owner_binding_revision_conflict_and_measured_count(self):
        (self.project/'source_pdf.json').write_text(json.dumps(dict(contract='owned-pdf-source-v1',owner='owner-a')))
        app=FastAPI();app.include_router(self.module.router)
        async def access(request:Request):
            if request.headers.get('x-fixture-admin')!='yes':raise HTTPException(403,'fixture denied')
        async def owner(request:Request):return request.headers.get('x-fixture-owner','')
        app.dependency_overrides[require_screenwriting_access]=access;app.dependency_overrides[require_conversation_owner]=owner
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://fixture') as client:
                own={'x-fixture-admin':'yes','x-fixture-owner':'owner-a'}
                payload=dict(project_name='A project',chapter_number=1,chapter_title='One',prose_content='Three fixture words.',word_count=900)
                saved=await client.post('/api/novelizer/save_draft',json=payload,headers=own)
                self.assertEqual(saved.status_code,200);self.assertEqual(saved.json()['word_count'],3)
                conflict=await client.post('/api/novelizer/save_draft',json={**payload,'prose_content':'Changed','expected_revision':'0'*64},headers=own)
                self.assertEqual(conflict.status_code,409)
                denied=await client.get('/api/novelizer/get_drafts/A%20project',headers={**own,'x-fixture-owner':'owner-b'})
                self.assertEqual(denied.status_code,403)
                listed=await client.get('/api/novelizer/get_drafts/A%20project',headers=own)
                self.assertEqual(listed.json()['chapters'][0]['revision'],saved.json()['revision'])
        asyncio.run(run())

    def test_enabled_adaptive_admission_failure_is_truthful_and_never_starts_generation(self):
        from gpu.compute_scheduler import GPUAdmissionError
        class Denied:
            enabled=True
            @asynccontextmanager
            async def lease(self,*args,**kwargs):
                raise GPUAdmissionError('fixture_capacity_unavailable',retryable=True)
                yield
        with patch.object(self.module,'get_dispatcher',return_value=Denied()),patch.object(self.module.httpx,'AsyncClient') as client:
            with self.assertRaises(HTTPException) as caught:asyncio.run(self.module._query_llm('fixture','directive'))
        self.assertEqual(caught.exception.status_code,503);client.assert_not_called()
        self.assertEqual(caught.exception.detail['attempts'][0]['error'],'fixture_capacity_unavailable')

    def test_incomplete_rich_body_is_not_silently_grouped_as_a_complete_source(self):
        from core import fdx_source_documents as fdx
        path=self.root/'Incomplete rich source'
        raw=b'<FinalDraft><Content><Paragraph Type="Action"><Text>Known fixture text.</Text></Paragraph><UnknownSection><Paragraph Type="Action"><Text>Omitted fixture body.</Text></Paragraph></UnknownSection></Content></FinalDraft>'
        fdx.import_project(path,raw,'owner-a','f'*32)
        with self.assertRaises(HTTPException) as caught:
            invoke(self.module.group_script_into_chapters,project_name=path.name,script_content=None)
        self.assertEqual(caught.exception.status_code,409)
        self.assertEqual((path/'original.fdx').read_bytes(),raw)


if __name__=='__main__':unittest.main()
