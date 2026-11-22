"""Known synthetic backend process; never a production service or port."""
from pathlib import Path
import ctypes,hashlib,json,os,socket,sys,sysconfig,time
from ctypes import wintypes
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'backend'),sys.argv[2]]
from scripts.tests import test_native_creative_pipe_controller as fixture
from security.native_creative_controller import NativeCreativeController,ReviewedCandidate,PIPE_BOOTSTRAP_CONTRACT
from security.firebase_auth import VerifiedFirebaseContext
def birth(handle):
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
    fields=[wintypes.FILETIME() for _ in range(4)]
    if not api.GetProcessTimes(handle,*[ctypes.byref(f) for f in fields]):raise OSError()
    return fields[0].dwHighDateTime<<32|fields[0].dwLowDateTime
def main():
    host=fixture.PipeControllerTests();host.setUp();connection=None
    try:
        directory=host.fixture.root/'loss-gui';directory.mkdir()
        child=ROOT/'scripts/tests/fixtures/native_creative_backend_loss_gui.py'
        paths=[child,*[ROOT/'native_studio'/n for n in ('creative_session.py','creative_pipe_bootstrap.py',
            'creative_pipe_transport.py','creative_pipe_io.py','creative_wire.py','screenplay_client.py',
            'native_creative_entry.py','screenwriting_view.py','engine.py','rich_screenplay_draft.py','theme.py')]]
        qt=ROOT/'runtime/qt-layout-check-20261111/Lib/site-packages/PyQt6/Qt6/bin'
        spec=ReviewedCandidate(fixture.pin(sys._base_executable),
            ('-I','-B',str(child),sys.argv[1],str(directory),sys.argv[2],'--native-creative-pipe-bootstrap'),str(ROOT),
            (('SYSTEMROOT',os.environ['SYSTEMROOT']),('PYTHONUTF8','1'),('PATH',str(qt)+';'+str(Path(os.environ['SYSTEMROOT'])/'System32'))),
            tuple(fixture.pin(p)for p in paths),PIPE_BOOTSTRAP_CONTRACT)
        host.controller=NativeCreativeController.create(spec,host.grants,host.ns['_issue_native_creative_grant'],services=host.services)
        record=host.record=host.controller.launch(VerifiedFirebaseContext(fixture.pdf.OWNER,time.monotonic()+120),
            project='Pipe Project',revision=host.opening['revision'],source_sha256=host.source['source_sha256'])
        if not record._acked.wait(15) or not record.acknowledged:raise AssertionError()
        hashes={n:hashlib.sha256((host.directory/n).read_bytes()).hexdigest()for n in
            ('original.pdf','source_packet.json','source_exports/layout.fdx','source_exports/layout.pdf','screenplay.fountain')}
        connection=socket.create_connection(('127.0.0.1',int(sys.argv[1])),timeout=10)
        value={'kind':'host_ready','pid':os.getpid(),'gui_pid':record.pid,'gui_handle':int(record._lifetime.process.hp),
            'gui_birth':birth(record._lifetime.process.hp),'acknowledged':True,'project':str(host.directory),
            'fixture_root':str(host.fixture.root),'hashes':hashes,'candidate_sha256':spec.sha256,
            'source_pins':[{'path':p.path,'sha256':p.sha256}for p in spec.files]}
        connection.sendall(json.dumps(value).encode()+b'\n')
        time.sleep(45);return 3
    finally:
        if connection is not None:connection.close()
        host.doCleanups()
if __name__=='__main__':raise SystemExit(main())
