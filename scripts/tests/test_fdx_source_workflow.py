"""Real ASGI route contracts using synthetic original FDX and isolated projects."""
import ast, hashlib, json, unittest, uuid
from pathlib import Path
from unittest.mock import patch
from fastapi import APIRouter, Depends, FastAPI, File, Form, UploadFile
from fastapi.testclient import TestClient
from pydantic import BaseModel, StrictInt
from scripts.tests import test_chat_pdf_workflow as fixture
from scripts.tests.test_fdx_source_documents import XML, OWNER, OTHER

class FDXWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base=fixture.PdfWorkflowFixture();self.base.setUp();self.addCleanup(self.base.doCleanups)
        self.scope=self.base.router_scope();source=fixture.ROOT/'backend/routers/screenwriting_router.py'
        self.scope.update(BaseModel=BaseModel,StrictInt=StrictInt,Form=Form,File=File,UploadFile=UploadFile)
        names={'WriteScreenplayPayload','FDXWorkingCopyPayload','import_fdx_source_project','create_fdx_working_copy'}
        nodes=[n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body if getattr(n,'name','') in names]
        for n in nodes:
            if hasattr(n,'decorator_list'):n.decorator_list=[]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),self.scope)
        # The write route was compiled against the fixture's placeholder model.
        self.scope['write_screenplay'].__annotations__['payload']=self.scope['WriteScreenplayPayload']
        app=FastAPI();router=APIRouter(dependencies=[Depends(self.scope['_screenwriting_owner_scope'])])
        for path,name,method in [('/import','import_fdx_source_project','POST'),('/working','create_fdx_working_copy','POST'),('/read','read_screenplay','GET'),('/write','write_screenplay','POST'),('/fdx','export_fdx','GET'),('/pdf','export_pdf','GET')]:
            router.add_api_route(path,self.scope[name],methods=[method])
        app.include_router(router)
        from security import firebase_auth
        from routers.conversation_router import require_conversation_owner
        from fastapi import Request, HTTPException
        async def owner(request:Request):
            value=verified('',request.headers.get('authorization',''))
            if not value:raise HTTPException(403,'Synthetic account denied')
            return value
        def verified(key,authorization):return OWNER if authorization=='Bearer own' else OTHER if authorization=='Bearer other' else None
        app.dependency_overrides[require_conversation_owner]=owner
        setting=patch.object(firebase_auth,'get_admin_principal',verified);setting.start();self.addCleanup(setting.stop)
        self.client=TestClient(app);self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
        self.headers={'Authorization':'Bearer own'}
    def imported(self,name='Rich FDX',raw=XML):
        response=self.client.post('/import',data={'project_name':name,'request_id':uuid.uuid4().hex,'source_sha256':hashlib.sha256(raw).hexdigest()},files={'file':('original.fdx',raw,'application/xml')},headers=self.headers)
        self.assertEqual(response.status_code,200,response.text);return response.json()
    def files(self,name):return {p.relative_to(self.base.projects/name).as_posix():p.read_bytes() for p in (self.base.projects/name).rglob('*') if p.is_file()}
    def test_http_original_noop_edit_reopen_export_and_full_ack(self):
        raw=b'\xef\xbb\xbf'+XML;read=self.imported(raw=raw);name=read['project'];before=self.files(name)
        self.assertEqual(read['source']['sha256'],hashlib.sha256(raw).hexdigest())
        query={'project_name':name,'expected_revision':read['revision']}
        self.assertEqual(self.client.get('/fdx',params=query,headers=self.headers).content,raw)
        saved=self.client.post('/write',json={'project_name':name,'content':read['content'],'expected_revision':read['revision'],'expected_workflow_revision':0,'fdx_document':read['fdx_document']},headers=self.headers)
        self.assertEqual(saved.status_code,200,saved.text);self.assertTrue(saved.json()['unchanged']);self.assertEqual(before,self.files(name))
        document=json.loads(json.dumps(read['fdx_document']));block=document['blocks'][2];old=block['text'];block['text']='First revised voice.';block['edit_operations']=[{'id':'1'*32,'before_text':old,'start':6,'end':6,'text':'revised '}]
        from core.fdx_source_documents import projection
        saved=self.client.post('/write',json={'project_name':name,'content':projection(document),'expected_revision':read['revision'],'expected_workflow_revision':0,'fdx_document':document},headers=self.headers)
        self.assertEqual(saved.status_code,200,saved.text);ack=saved.json()
        self.assertEqual(ack['fdx_document']['blocks'][2]['text'],block['text']);self.assertEqual(ack['fdx_document']['applied_operation_ids'],['1'*32])
        self.assertTrue(ack['projection_spans']);self.assertNotEqual(ack['revision'],read['revision'])
        reopened=self.client.get('/read',params={'project_name':name},headers=self.headers).json()
        self.assertEqual(reopened['fdx_document'],ack['fdx_document']);self.assertEqual(reopened['content'],ack['content'])
        current=self.client.get('/fdx',params={**query,'expected_revision':ack['revision']},headers=self.headers)
        from core.fdx_source_documents import parse_fdx
        self.assertEqual(parse_fdx(current.content)['blocks'][2]['text'],'First revised voice.');self.assertIn(b'NOTE ONLY',current.content);self.assertIn(b'<DualDialogue>',current.content)
        original=self.client.get('/fdx',params={**query,'expected_revision':ack['revision'],'layout':'original'},headers=self.headers)
        self.assertEqual(original.content,raw);self.assertEqual(before['original.fdx'],raw)
    def test_http_foreign_stale_plaintext_and_metadata_mutations_preserve_source(self):
        read=self.imported();name=read['project'];before=self.files(name);query={'project_name':name,'expected_revision':read['revision']}
        for path in ('/read','/fdx'):
            self.assertEqual(self.client.get(path,params=query,headers={'Authorization':'Bearer other'}).status_code,403)
            self.assertEqual(self.client.get(path,params=query).status_code,403)
        self.assertEqual(self.client.get('/fdx',params={**query,'expected_revision':'stale'},headers=self.headers).status_code,409)
        self.assertEqual(self.client.get('/fdx',params={'project_name':name},headers=self.headers).status_code,428)
        payload={'project_name':name,'content':'Changed plain text','expected_revision':read['revision'],'expected_workflow_revision':0}
        self.assertEqual(self.client.post('/write',json=payload,headers=self.headers).status_code,428)
        document=read['fdx_document'];document['blocks'][0]['notes'][0]['text']='Changed note'
        self.assertEqual(self.client.post('/write',json={**payload,'content':read['content'],'fdx_document':document},headers=self.headers).status_code,422)
        self.assertEqual(self.client.get('/pdf',params=query,headers=self.headers).status_code,422)
        self.assertEqual(before,self.files(name))
    def test_http_explicit_working_copy_is_separate_and_owner_fenced(self):
        read=self.imported();before=self.files(read['project'])
        result=self.client.post('/working',json={'project_name':read['project'],'new_project_name':'Explicit Plain Copy','content':'INT. COPY - DAY\n\nNew structure.','expected_revision':read['revision'],'request_id':uuid.uuid4().hex},headers=self.headers)
        self.assertEqual(result.status_code,200,result.text);self.assertIn('warning',result.json())
        own=self.client.get('/read',params={'project_name':'Explicit Plain Copy'},headers=self.headers)
        self.assertEqual(own.status_code,200,own.text);self.assertIn('New structure.',own.json()['content'])
        self.assertEqual(self.client.get('/read',params={'project_name':'Explicit Plain Copy'},headers={'Authorization':'Bearer other'}).status_code,403)
        self.assertEqual(before,self.files(read['project']))
    def test_http_unicode_styled_range_and_paragraph_type_survive_save_reopen(self):
        raw=XML.decode().replace('Bold &amp; ','aa😀').replace('literal *stars*','aa &amp; *stars*').encode()
        read=self.imported(raw=raw);document=json.loads(json.dumps(read['fdx_document']));block=document['blocks'][0]
        block['text']='aa😀a! & *stars*';block['type']='General';block['edit_operations']=[{'id':'2'*32,'before_text':'aa😀aa & *stars*','start':4,'end':5,'text':'!'}]
        from core.fdx_source_documents import projection,parse_fdx
        response=self.client.post('/write',json={'project_name':read['project'],'content':projection(document),'expected_revision':read['revision'],'fdx_document':document},headers=self.headers)
        self.assertEqual(response.status_code,200,response.text);ack=response.json()
        reopened=self.client.get('/read',params={'project_name':read['project']},headers=self.headers).json()
        changed=reopened['fdx_document']['blocks'][0];self.assertEqual(changed['text'],block['text']);self.assertEqual(changed['type'],'General')
        self.assertEqual(changed['runs'][0]['attributes'],{'Style':'Bold','RevisionID':'5'});self.assertEqual(changed['runs'][0]['text'],'aa😀')
        self.assertTrue(all(run['attributes'].get('Style')=='Italic' for run in changed['runs'][1:]));self.assertEqual(changed['notes'],read['fdx_document']['blocks'][0]['notes'])
        exported=self.client.get('/fdx',params={'project_name':read['project'],'expected_revision':ack['revision']},headers=self.headers)
        output=parse_fdx(exported.content);self.assertEqual(output['title_page'],read['fdx_document']['title_page']);self.assertEqual(output['blocks'][1:],read['fdx_document']['blocks'][1:])

if __name__=='__main__':unittest.main()
