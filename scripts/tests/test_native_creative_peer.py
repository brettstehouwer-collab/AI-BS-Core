"""Real Windows TCP/owned-job identity checks; no GUI, secrets or original data."""
import os
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from core.opencode_worker import _WinProcess
from security.native_creative_peer import OwnedInvocation, NativePeerResolver
from security.native_creative_handoff import HandoffDenied


@unittest.skipUnless(os.name=='nt','Windows process handle and TCP ownership')
class PeerTests(unittest.TestCase):
    def setUp(self):
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen()
        self.listener.settimeout(5);self.addCleanup(self.listener.close)
        self.port=self.listener.getsockname()[1]
        code="import socket; s=socket.create_connection(('127.0.0.1',int(__import__('sys').argv[1])));s.sendall(b'R');s.recv(1);s.close()"
        # The venv python.exe redirects through a second process on this host.
        # Match the actual root executable; never broaden identity to children.
        self.process=_WinProcess([sys._base_executable,'-I','-c',code,str(self.port)],Path.cwd(),dict(os.environ))
        self.addCleanup(lambda:self.assertTrue(self.process.close(),'Owned fixture job did not drain'))
        self.connection,self.address=self.listener.accept();self.connection.settimeout(5)
        self.addCleanup(self.connection.close);self.assertEqual(self.connection.recv(1),b'R')
        self.invocation=OwnedInvocation(self.process,candidate_sha256='a'*64)
        self.resolver=NativePeerResolver(endpoint=('127.0.0.1',self.port))
        self.scope={'type':'http','client':self.address,'server':('127.0.0.1',self.port),'headers':[]}

    def test_live_owned_connection_is_resolved_from_os(self):
        self.assertIs(self.resolver.resolve(self.scope,[self.invocation]),self.invocation)

    def test_forwarded_identity_headers_fail_before_os_lookup(self):
        for name in (b'forwarded',b'x-forwarded-for',b'X-Forwarded-For',b'x-forwarded-proto',b'x-forwarded-port'):
            scope={**self.scope,'headers':[(name,b'127.0.0.1:12345')]}
            with patch('security.native_creative_peer.psutil.net_connections') as reader:
                with self.assertRaises(HandoffDenied):self.resolver.resolve(scope,[self.invocation])
                reader.assert_not_called()

    def test_other_process_connection_is_not_owned(self):
        other=socket.create_connection(('127.0.0.1',self.port));self.addCleanup(other.close)
        accepted,address=self.listener.accept();self.addCleanup(accepted.close)
        with self.assertRaises(HandoffDenied):self.resolver.resolve({**self.scope,'client':address},[self.invocation])

    def test_closed_owned_handle_is_denied(self):
        self.assertTrue(self.process.close())
        self.assertFalse(self.invocation.alive())
        with self.assertRaises(HandoffDenied):self.resolver.resolve(self.scope,[self.invocation])

    def test_scope_mismatch_and_unknown_connection_are_denied(self):
        for change in ({'client':('192.0.2.1',123)}, {'client':('127.0.0.1',True)},
                       {'server':('127.0.0.1',1)}, {'type':'websocket'},
                       {'client':('127.0.0.1',1)}):
            with self.assertRaises(HandoffDenied):self.resolver.resolve({**self.scope,**change},[self.invocation])

    def test_no_pid_attach_and_bounded_registry(self):
        with self.assertRaises(HandoffDenied):OwnedInvocation(self.process.pid,candidate_sha256='a'*64)
        with self.assertRaises(HandoffDenied):OwnedInvocation(self.process,candidate_sha256='bad')
        for entries in ([],[self.invocation]*65,[self.invocation,self.invocation],[object()]):
            with self.assertRaises(HandoffDenied):self.resolver.resolve(self.scope,entries)

    def test_unavailable_os_table_is_denied(self):
        import psutil
        with patch('security.native_creative_peer.psutil.net_connections',side_effect=psutil.AccessDenied()):
            with self.assertRaises(HandoffDenied):self.resolver.resolve(self.scope,[self.invocation])

    def test_connection_disappearing_during_resolution_is_denied(self):
        import psutil
        rows=psutil.net_connections(kind='tcp4')
        with patch('security.native_creative_peer.psutil.net_connections',side_effect=[rows,[]]):
            with self.assertRaises(HandoffDenied):self.resolver.resolve(self.scope,[self.invocation])


@unittest.skipUnless(os.name=='nt','Windows actual ASGI direct transport')
class ASGIPeerTests(unittest.TestCase):
    def check_request(self, forwarded):
        import uvicorn
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
        self.addCleanup(listener.close)
        port=listener.getsockname()[1];resolver=NativePeerResolver(endpoint=('127.0.0.1',port))
        invocations=[];observed=[]
        async def app(scope,receive,send):
            observed.append(scope['client'])
            try:resolver.resolve(scope,invocations);status=200
            except HandoffDenied:status=403
            await send({'type':'http.response.start','status':status,'headers':[]})
            await send({'type':'http.response.body','body':b'fixture'})
        server=uvicorn.Server(uvicorn.Config(app,log_level='critical',lifespan='off',
            proxy_headers=True,forwarded_allow_ips='127.0.0.1'))
        thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True)
        def stop_server():
            server.should_exit=True;thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.addCleanup(stop_server);thread.start()
        deadline=time.monotonic()+5
        while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue(server.started)
        extra='X-Forwarded-For: 127.0.0.1:1111\r\n' if forwarded else ''
        request=f'GET /native-fixture HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n{extra}Connection: close\r\n\r\n'
        code="import socket,sys;sys.stdin.buffer.read(1);s=socket.create_connection(('127.0.0.1',int(sys.argv[1])));s.sendall(bytes.fromhex(sys.argv[2]));print(s.recv(4096).split(b' ')[1].decode(),flush=True);s.close()"
        process=_WinProcess([sys._base_executable,'-I','-c',code,str(port),request.encode().hex()],Path.cwd(),dict(os.environ))
        self.addCleanup(lambda:self.assertTrue(process.close(),'Owned ASGI fixture job did not drain'))
        invocations.append(OwnedInvocation(process,candidate_sha256='b'*64))
        process.stdin.write(b'R');process.stdin.close()
        deadline=time.monotonic()+5
        while process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(process.poll(),0)
        self.assertEqual(process.stdout.read(32).strip(),b'403' if forwarded else b'200')
        self.assertEqual(len(observed),1)

    def test_real_http_owned_peer_passes(self):self.check_request(False)
    def test_real_http_forwarded_peer_is_denied(self):self.check_request(True)


if __name__=='__main__':unittest.main()
