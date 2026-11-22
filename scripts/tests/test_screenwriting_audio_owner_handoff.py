"""Request/background owner capture only: no audio engine/model/service execution."""
import ast,sys,unittest,uuid
from types import ModuleType
from unittest.mock import patch
from fastapi import BackgroundTasks,HTTPException
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from scripts.tests import test_chat_pdf_workflow as fixture
from scripts.tests.test_fdx_source_documents import XML,OWNER,OTHER

class AudioOwnerHandoffTests(unittest.TestCase):
    def setUp(self):
        self.base=fixture.PdfWorkflowFixture();self.base.setUp();self.addCleanup(self.base.doCleanups)
        self.scope=self.base.router_scope();self.scope['BackgroundTasks']=BackgroundTasks
        self.calls=[];self.scope['_project_audio_file']=lambda name:self.calls.append(('audio',name))
        source=fixture.ROOT/'backend/routers/screenwriting_router.py';names={'start_audio_transcription','get_audio_transcription_status','get_project_audio_transcript'}
        nodes=[n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body if getattr(n,'name','') in names]
        for node in nodes:node.decorator_list=[]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),self.scope)
        self.audio=ModuleType('core.audio_transcriber')
        self.audio.run_transcription_sync=lambda *args,**kwargs:None
        self.audio.get_transcription_status=lambda name,owner=None:self.calls.append(('status',name,owner)) or {'status':'idle'}
        self.audio.get_project_transcription=lambda name,owner=None:self.calls.append(('transcript',name,owner)) or {'status':'success','has_transcript':False}
        setting=patch.dict(sys.modules,{'core.audio_transcriber':self.audio});setting.start();self.addCleanup(setting.stop)
        from core.fdx_source_documents import import_project
        import_project(self.base.projects/'Owned Rich',XML,OWNER,uuid.uuid4().hex)
    def test_background_and_getters_capture_verified_owner_not_project_only(self):
        token=bind_memory_principal(OWNER)
        try:
            tasks=BackgroundTasks();self.scope['start_audio_transcription']('Owned Rich',tasks)
            self.assertEqual(len(tasks.tasks),1);self.assertEqual(tasks.tasks[0].kwargs,{'owner':OWNER});self.assertEqual(tasks.tasks[0].args,('Owned Rich','base'))
            self.scope['get_audio_transcription_status']('Owned Rich');self.scope['get_project_audio_transcript']('Owned Rich')
            self.assertEqual(self.calls[-2:],[('status','Owned Rich',OWNER),('transcript','Owned Rich',OWNER)])
        finally:reset_memory_principal(token)
    def test_foreign_and_missing_identity_never_reach_task_status_or_transcript(self):
        for owner in (OTHER,None):
            token=bind_memory_principal(owner) if owner else None
            try:
                for name,args in [('start_audio_transcription',('Owned Rich',BackgroundTasks())),('get_audio_transcription_status',('Owned Rich',)),('get_project_audio_transcript',('Owned Rich',))]:
                    with self.assertRaises(HTTPException) as error:self.scope[name](*args)
                    self.assertEqual(error.exception.status_code,403)
                self.assertEqual(self.calls,[])
            finally:
                if token:reset_memory_principal(token)

if __name__=='__main__':unittest.main()
