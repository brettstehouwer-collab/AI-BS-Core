"""Replacement synthetic host opens retained project bytes; never a live API."""
from pathlib import Path
import ast, ctypes, hashlib, json, os, socket, sys, time
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'backend'),sys.argv[4]]
from scripts.tests import test_native_creative_pipe_controller as fixture
from scripts.tests.fixtures.native_creative_backend_loss_host import birth
from security.native_creative_controller import NativeCreativeController,ReviewedCandidate,PIPE_BOOTSTRAP_CONTRACT
from security.native_creative_handoff import CreativeHandoffs
from security.firebase_auth import VerifiedFirebaseContext
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from core.chat_pdf_sources import require_project_owner
from pydantic import BaseModel,StrictInt

def send(s,value):s.sendall(json.dumps(value).encode()+b'\n')

def main():
    import _winapi
    root=Path(sys.argv[2]).resolve();recovery=Path(sys.argv[3]).resolve()
    if root.parent!=(ROOT/'t').resolve() or not recovery.is_relative_to(root):raise ValueError()
    retained=fixture.pdf.PdfWorkflowFixture();retained.root=root;retained.projects=root/'projects'
    namespace=retained.router_scope();namespace.update(BaseModel=BaseModel,StrictInt=StrictInt)
    tree=ast.parse((ROOT/'backend/routers/screenwriting_router.py').read_text(encoding='utf-8-sig'))
    nodes=[n for n in tree.body if getattr(n,'name','')in {'WriteScreenplayPayload','_issue_native_creative_grant'}]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual retained-project grant/write model>','exec'),namespace)
    services=SimpleNamespace(**namespace);writes=[]
    def forbidden_write(*args,**kwargs):writes.append(True);raise AssertionError('Restore must not save')
    services.write_screenplay=forbidden_write
    token=bind_memory_principal(fixture.pdf.OWNER)
    try:
        opening=services.read_screenplay(project_name='Pipe Project')
        fence=require_project_owner(retained.projects/'Pipe Project')
    finally:reset_memory_principal(token)
    child=ROOT/'scripts/tests/fixtures/native_creative_crash_restore_gui.py'
    paths=[child,*[ROOT/'native_studio'/n for n in ('creative_session.py','creative_pipe_bootstrap.py',
        'creative_pipe_transport.py','creative_pipe_io.py','creative_wire.py','screenplay_client.py',
        'native_creative_entry.py','screenwriting_view.py','engine.py','rich_screenplay_draft.py','theme.py')]]
    qt=ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/Qt6/bin'
    spec=ReviewedCandidate(fixture.pin(sys._base_executable),
        ('-I','-B',str(child),sys.argv[1],str(recovery),sys.argv[4],'--native-creative-pipe-bootstrap'),str(ROOT),
        (('SYSTEMROOT',os.environ['SYSTEMROOT']),('PYTHONUTF8','1'),('PATH',str(qt)+';'+str(Path(os.environ['SYSTEMROOT'])/'System32'))),
        tuple(fixture.pin(p)for p in paths),PIPE_BOOTSTRAP_CONTRACT)
    controller=NativeCreativeController.create(spec,CreativeHandoffs(),namespace['_issue_native_creative_grant'],services=services)
    retained_handle=None
    deliver=controller._deliver
    def retain_before_delivery(owned,packet):
        nonlocal retained_handle
        current=_winapi.GetCurrentProcess()
        retained_handle=_winapi.DuplicateHandle(current,owned._lifetime.process.hp,current,0,False,_winapi.DUPLICATE_SAME_ACCESS)
        return deliver(owned,packet)
    with patch.object(controller,'_deliver',side_effect=retain_before_delivery):
        record=controller.launch(VerifiedFirebaseContext(fixture.pdf.OWNER,time.monotonic()+120),
            project='Pipe Project',revision=opening['revision'],source_sha256=fence['source_sha256'])
    connection=socket.create_connection(('127.0.0.1',int(sys.argv[1])),timeout=10)
    try:
        if not record._acked.wait(15)or not record.acknowledged:raise AssertionError('No GUI acknowledgment')
        send(connection,{'kind':'replacement_host','pid':os.getpid(),'gui_pid':record.pid,
            'gui_handle':int(retained_handle),'gui_birth':birth(retained_handle),
            'revision':opening['revision'],'source_sha256':fence['source_sha256'],'candidate_sha256':spec.sha256,
            'source_pins':[{'path':p.path,'sha256':p.sha256}for p in spec.files]})
        if _winapi.WaitForSingleObject(retained_handle,20000)!=0:raise TimeoutError('GUI exit')
        code=_winapi.GetExitCodeProcess(retained_handle)
        result=controller.close(record)
        if record._cleanup_worker is not None:record._cleanup_worker.join(timeout=3)
        send(connection,{'kind':'host_complete','gui_exit_code':code,'writes':len(writes),
            'acknowledged':result.acknowledged,'termination_requested':result.termination_requested,
            'pipes_closed':not record._pipes._fds,'cleanup_failed':controller.cleanup_failed})
        return 0 if code==0 and not writes and not result.termination_requested and not controller.cleanup_failed else 4
    finally:
        connection.close();controller.close(record)
        if retained_handle is not None:_winapi.CloseHandle(retained_handle)
if __name__=='__main__':raise SystemExit(main())
