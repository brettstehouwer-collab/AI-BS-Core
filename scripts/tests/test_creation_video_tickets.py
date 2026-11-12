"""Actual scoped-video route/security functions; no backend startup or real stores."""
import ast,base64,hashlib,hmac,json,os,secrets,sys,tempfile,time,types,unittest
from pathlib import Path
from urllib.parse import quote,urlencode,urlsplit,parse_qs
from unittest.mock import patch
from fastapi import APIRouter,Depends,FastAPI,HTTPException,Query,Request
from fastapi.testclient import TestClient
from fastapi.responses import FileResponse
from pydantic import BaseModel
ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'backups/creation_suite_deploy_20261025_record98/backend'

class VideoTicketTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.directory=Path(temp.name)
        self.file=self.directory/'fixture clip.webm';self.file.write_bytes(bytes(range(128)))
        self.other=self.directory/'different.mp4';self.other.write_bytes(b'other media')
        self.nonvideo=self.directory/'private.db';self.nonvideo.write_bytes(b'synthetic database')
        (self.directory/'folder').mkdir()
        self.admin={'Authorization':'Bearer fixture-only'}
        def admin_allowed(request):return request.headers.get('authorization')=='Bearer fixture-only'
        def require_admin(request:Request):
            if not admin_allowed(request):raise HTTPException(403,'Fixture admin required')
        scope=dict(Path=Path,os=os,time=time,json=json,secrets=secrets,base64=base64,hashlib=hashlib,hmac=hmac,
            HTTPException=HTTPException,Request=Request,APIRouter=APIRouter,Depends=Depends,Query=Query,
            BaseModel=BaseModel,FileResponse=FileResponse,quote=quote,urlencode=urlencode,
            MEDIA_TICKET_TTL=3600,_MEDIA_KEY=secrets.token_bytes(32),SCREEN_RECORDINGS_DIR=self.directory,
            document_request_allowed=admin_allowed,require_document_access=require_admin)
        source_override=os.environ.get('AIBS_VIDEO_TICKET_BEFORE')=='1'
        security=FIXTURE/'backend__security__document_access.py.before_ticket_fix' if source_override else ROOT/'backend/security/document_access.py'
        tree=ast.parse(security.read_text(encoding='utf-8'))
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('_canonical_path','issue_media_ticket','_valid_media_ticket','video_request_allowed','require_video_access')]
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'<actual-ticket-security>','exec'),scope)
        scope.setdefault('require_video_access',require_admin)
        video=FIXTURE/'backend__routers__video_router.py.before_ticket_fix' if source_override else ROOT/'backend/routers/video_router.py'
        tree=ast.parse(video.read_text(encoding='utf-8'))
        chosen=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='StreamRequest'
                or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VIDEO_MIME_TYPES' for t in n.targets)
                or isinstance(n,ast.FunctionDef) and n.name in ('resolve_video_path','create_video_media_ticket','stream_video_file','start_video_stream','get_script_content')]
        scope['router']=APIRouter(prefix='/api/video')
        exec(compile(ast.Module(body=chosen,type_ignores=[]),'<actual-video-ticket-routes>','exec'),scope)
        fake=types.ModuleType('routers.video_router');fake.resolve_video_path=scope.get('resolve_video_path')
        package=types.ModuleType('routers');package.__path__=[]
        module_patch=patch.dict(sys.modules,{'routers':package,'routers.video_router':fake})
        module_patch.start();self.addCleanup(module_patch.stop)
        app=FastAPI();app.include_router(scope['router'])
        self.client=TestClient(app,raise_server_exceptions=False);self.addCleanup(self.client.close)
        self.scope=scope

    def ticket(self,path=None):
        response=self.client.post('/api/video/media-ticket',json={'video_path':str(path or self.file)},headers=self.admin)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['cache-control'],'no-store')
        return response.json()['url']

    def test_admin_issues_scoped_range_and_head_link_without_auth_headers(self):
        url=self.ticket()
        response=self.client.get(url,headers={'Range':'bytes=16-31'})
        self.assertEqual(response.status_code,206)
        self.assertEqual(response.content,bytes(range(16,32)))
        self.assertEqual(response.headers['content-type'],'video/webm')
        self.assertEqual(response.headers['content-range'],'bytes 16-31/128')
        self.assertEqual(response.headers['cache-control'],'private, no-store')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        head=self.client.head(url)
        self.assertEqual(head.status_code,200);self.assertEqual(head.content,b'')

    def test_anonymous_and_ticket_bearing_admin_operations_are_denied(self):
        self.assertEqual(self.client.post('/api/video/media-ticket',json={'video_path':str(self.file)}).status_code,403)
        self.assertEqual(self.client.get('/api/video/stream',params={'path':str(self.file)}).status_code,403)
        url=self.ticket();ticket=parse_qs(urlsplit(url).query)['ticket'][0]
        self.assertEqual(self.client.post('/api/video/media-ticket',params={'ticket':ticket},json={'video_path':str(self.file)}).status_code,403)
        self.assertEqual(self.client.post('/api/video/start_stream',params={'ticket':ticket},json={'video_path':str(self.file)}).status_code,403)
        self.assertEqual(self.client.get('/api/video/script',params={'path':str(self.file),'ticket':ticket}).status_code,403)
        self.assertEqual(self.client.post(url).status_code,405)

    def test_wrong_file_tampered_expired_and_wrong_action_links_are_denied(self):
        url=self.ticket();claims=parse_qs(urlsplit(url).query);token=claims['ticket'][0]
        for file,changed in [(self.other,token),(self.file,token[:-1]+('0' if token[-1]!='0' else '1'))]:
            self.assertEqual(self.client.get('/api/video/stream',params={'path':str(file),'ticket':changed}).status_code,403)
        self.scope['time']=types.SimpleNamespace(time=lambda:time.time()+7200)
        self.assertEqual(self.client.get(url).status_code,403)
        self.scope['time']=time
        for action in ('preview','download'):
            wrong=self.scope['issue_media_ticket'](self.file,action)
            self.assertEqual(self.client.get('/api/video/stream',params={'path':str(self.file),'ticket':wrong}).status_code,403)
        self.assertFalse(self.scope['_valid_media_ticket'](token,self.file,'preview'))
        self.assertFalse(self.scope['_valid_media_ticket'](token,self.file,'download'))

    def test_canonical_alias_matches_same_video_and_direct_admin_stream_remains_supported(self):
        url=self.ticket(self.directory/'folder'/'..'/self.file.name)
        self.assertEqual(parse_qs(urlsplit(url).query)['path'][0],str(self.file.resolve()))
        self.assertEqual(self.client.get(url).content,self.file.read_bytes())
        direct=self.client.get('/api/video/stream',params={'path':str(self.file)},headers=self.admin)
        self.assertEqual(direct.status_code,200)
        start=self.client.post('/api/video/start_stream',json={'video_path':str(self.file)},headers=self.admin)
        self.assertEqual(start.status_code,200)
        self.assertEqual(parse_qs(urlsplit(start.json()['stream_url']).query)['path'][0],str(self.file.resolve()))

    def test_unsupported_nonvideo_missing_and_directory_targets_never_receive_grants(self):
        for path,status in ((self.nonvideo,415),(self.directory/'missing.mp4',404),(self.directory,404)):
            response=self.client.post('/api/video/media-ticket',json={'video_path':str(path)},headers=self.admin)
            self.assertEqual(response.status_code,status)
        self.assertEqual(self.client.get('/api/video/stream',params={'path':str(self.nonvideo)},headers=self.admin).status_code,415)

if __name__=='__main__':unittest.main()
