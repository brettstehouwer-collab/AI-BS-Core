"""Synthetic local-session fixtures; never access real vaults or backend records."""
import asyncio
import ast
from contextlib import asynccontextmanager, redirect_stdout
import importlib
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))


class MemoryVault:
    def __init__(self):self.blob=None;self.writes=[]
    def read(self):return self.blob
    def write(self,blob,owner):self.blob=blob;self.writes.append((blob,owner))


class LocalConnectionTests(unittest.TestCase):
    def setUp(self):
        self.environment=patch.dict(os.environ,{},clear=True)
        self.environment.start();self.addCleanup(self.environment.stop)
        self.m=importlib.import_module('native_studio.local_connection')
        self.vault=MemoryVault()
        self.server=self.m.ServiceIdentity(1122,1234.5,r'C:\Fixture\python.exe','S-1-5-21-100')
        self.desktop=self.m.ServiceIdentity(3344,5678.5,r'C:\Fixture\studio.exe','S-1-5-21-100')
        self.live=self.server
        self.publisher=self.m.LocalConnection(vault=self.vault,current_identity=lambda:self.server,listener_identity=lambda:self.live)
        self.client=self.m.LocalConnection(vault=self.vault,current_identity=lambda:self.desktop,listener_identity=lambda:self.live)
        self.secret='fixture-only-not-a-real-key'

    def publish(self):self.assertTrue(self.publisher.publish_if_owned(self.secret))

    def test_startup_peer_observation_failure_waits_without_writing_until_owner_proved(self):
        with patch.object(self.publisher,'listener_identity',side_effect=[self.m.LocalConnectionError('transient fixture'),self.server]):
            self.assertTrue(asyncio.run(self.m.publish_when_listening(self.secret,connection=self.publisher,attempts=2,interval=0)))
        self.assertEqual(len(self.vault.writes),1)
        self.assertEqual(self.client.headers(),{'X-Admin-Key':self.secret})

    def test_same_user_machine_connection_needs_no_env_key(self):
        self.publish()
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(self.m.local_service_headers(connection=self.client),{'X-Admin-Key':self.secret})
        self.assertEqual(len(self.vault.writes),1)

    def test_no_listener_never_writes_or_overwrites_existing_profile(self):
        self.publish();previous=self.vault.blob;self.live=None
        self.assertFalse(self.publisher.publish_if_owned('second-fixture'))
        self.assertEqual(self.vault.blob,previous)
        with self.assertRaises(self.m.LocalConnectionError):self.client.headers()

    def test_non_owning_service_cannot_publish(self):
        self.assertFalse(self.client.publish_if_owned(self.secret))
        self.assertEqual(self.vault.writes,[])

    def test_changed_pid_creation_executable_or_owner_rejects_without_secret_error(self):
        self.publish()
        for field,value in [('pid',1123),('created',1235.5),('exe',r'C:\Other\python.exe'),('owner_sid','S-1-5-21-999')]:
            values={k:getattr(self.server,k) for k in ['pid','created','exe','owner_sid']};values[field]=value
            self.live=self.m.ServiceIdentity(**values)
            with self.subTest(field=field),self.assertRaises(self.m.LocalConnectionError) as caught:self.client.headers()
            self.assertNotIn(self.secret,str(caught.exception))

    def test_other_windows_user_cannot_use_profile(self):
        self.publish()
        foreign=self.m.LocalConnection(vault=self.vault,current_identity=lambda:self.m.ServiceIdentity(7,8,r'C:\x.exe','S-1-5-21-999'),listener_identity=lambda:self.live)
        with self.assertRaises(self.m.LocalConnectionError):foreign.headers()

    def test_malformed_and_wrong_origin_profiles_rejected(self):
        self.publish();good=self.vault.blob
        for mutate in [lambda v:v.update(origin='https://api.brettstehouwer.live'),lambda v:v.update(schema=2),lambda v:v.update(secret=''),lambda v:v['service'].update(created=float('nan')),lambda v:v['service'].update(pid=True)]:
            value=json.loads(good);mutate(value);self.vault.blob=json.dumps(value).encode()
            with self.assertRaises(self.m.LocalConnectionError):self.client.headers()
        for blob in [b'bad-json',b'[]',b'X'*3000]:
            self.vault.blob=blob
            with self.assertRaises(self.m.LocalConnectionError):self.client.headers()

    def test_missing_profile_is_not_a_request_for_manual_key(self):
        self.assertEqual(self.m.local_service_headers(connection=self.client),{})

    def test_never_attaches_local_credentials_to_other_origins(self):
        self.publish()
        for url in ['https://api.brettstehouwer.live','http://127.0.0.1:8000','http://localhost:8080','http://127.0.0.1:8080.evil.test']:
            with patch.dict(os.environ,{'AI_BS_ADMIN_KEY':self.secret}):
                self.assertEqual(self.m.local_service_headers(url,connection=self.client),{})

    def test_explicit_development_override_retained_only_for_exact_loopback(self):
        with patch.dict(os.environ,{'AI_BS_ADMIN_KEY':self.secret}):
            self.assertEqual(self.m.local_service_headers(),{'X-Admin-Key':self.secret})

    def test_expired_profile_never_reaches_screenplay_transport(self):
        self.publish();self.live=None;requests=[]
        from native_studio.screenplay_client import ScreenplayClient,ScreenplayError
        def provider():return self.m.local_service_headers(connection=self.client)
        with patch.dict(os.environ,{},clear=True),patch('native_studio.screenplay_client.local_service_headers',side_effect=provider):
            with self.assertRaises(ScreenplayError):ScreenplayClient(transport=httpx.MockTransport(lambda r:requests.append(r))).projects()
        self.assertEqual(requests,[])

    def test_screenplay_auto_connects_and_retains_revision_and_denial_contracts(self):
        self.publish();requests=[]
        from native_studio.screenplay_client import ScreenplayClient,ScreenplayError
        def handler(request):
            requests.append(request)
            if request.method=='POST':return httpx.Response(409)
            return httpx.Response(200,json={'projects':['Fixture'],'current':'Fixture'})
        def provider():return self.m.local_service_headers(connection=self.client)
        with patch.dict(os.environ,{},clear=True),patch('native_studio.screenplay_client.local_service_headers',side_effect=provider):
            client=ScreenplayClient(transport=httpx.MockTransport(handler))
            self.assertEqual(client.projects()['projects'],['Fixture'])
            with self.assertRaisesRegex(ScreenplayError,'changed'):client.save('Fixture','new','rev-original')
        self.assertTrue(all(r.headers['X-Admin-Key']==self.secret for r in requests))
        self.assertEqual(json.loads(requests[1].content)['expected_revision'],'rev-original')

    def test_fe_uses_auto_headers_only_for_local_origin(self):
        from native_studio.fe_express_service import FEExpressClient
        requests=[]
        with patch('native_studio.fe_express_service.local_service_headers',return_value={'X-Admin-Key':self.secret}) as provider:
            client=FEExpressClient(transport=httpx.MockTransport(lambda r:(requests.append(r),httpx.Response(200,json={'success':True,'drivers':[]}))[1]))
            self.assertEqual(client.get_contractor_drivers(),[])
        provider.assert_called_once_with('http://127.0.0.1:8080')
        self.assertEqual(requests[0].headers['X-Admin-Key'],self.secret)

    def test_bounded_startup_waits_for_own_listener_then_publishes_once(self):
        seen=[]
        def listener():
            seen.append(1);return self.server if len(seen)>1 else None
        self.publisher.listener_identity=listener
        self.assertTrue(asyncio.run(self.m.publish_when_listening(self.secret,connection=self.publisher,attempts=3,interval=0)))
        self.assertEqual(len(self.vault.writes),1)

    def test_startup_missing_key_or_listener_is_bounded_without_write(self):
        self.live=None
        self.assertFalse(asyncio.run(self.m.publish_when_listening(self.secret,connection=self.publisher,attempts=2,interval=0)))
        self.assertFalse(asyncio.run(self.m.publish_when_listening('',connection=self.publisher,attempts=2,interval=0)))
        self.assertEqual(self.vault.writes,[])

    def test_startup_cancellation_and_vault_error_do_not_log_secret(self):
        async def run():
            task=asyncio.create_task(self.m.publish_when_listening(self.secret,connection=self.publisher,attempts=2,interval=5))
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
        asyncio.run(run())
        with patch.object(self.vault,'write',side_effect=OSError(self.secret)):
            with self.assertRaises(self.m.LocalConnectionError) as caught:self.publisher.publish_if_owned(self.secret)
        self.assertNotIn(self.secret,str(caught.exception))


class WindowsBoundaryTests(unittest.TestCase):
    def setUp(self):self.m=importlib.import_module('native_studio.local_connection')

    def test_vault_uses_exact_generic_target_current_machine_and_never_enumerates(self):
        writes=[];reads=[]
        api=SimpleNamespace(CRED_TYPE_GENERIC=1,CRED_PERSIST_LOCAL_MACHINE=2,
            CredWrite=lambda value,flags:writes.append((value,flags)),
            CredRead=lambda target,kind:(reads.append((target,kind)),{'CredentialBlob':'fixture-bytes'.encode('utf-16-le')})[1])
        with patch.dict(sys.modules,{'win32cred':api}):
            vault=self.m.WindowsCredentialVault();vault.write(b'fixture-bytes','S-1-5-21-100')
            self.assertEqual(vault.read(),b'fixture-bytes')
        self.assertEqual(reads,[(self.m.TARGET,1)])
        self.assertEqual(writes[0][0]['TargetName'],self.m.TARGET)
        self.assertEqual(writes[0][0]['Persist'],2)
        self.assertEqual(writes[0][0]['CredentialBlob'],'fixture-bytes')
        self.assertEqual(writes[0][1],0)

    @unittest.skipUnless(os.name=='nt','Windows API binding check')
    def test_real_credential_binding_uses_unicode_with_invalid_type_no_write(self):
        import win32cred
        import pywintypes
        # Type0 is invalid: the OS cannot create/update a credential. Reaching
        # ERROR_INVALID_PARAMETER proves Python accepted the Unicode arguments.
        with patch.object(win32cred,'CRED_TYPE_GENERIC',0),patch.object(self.m,'TARGET','AI-BS-invalid-type-no-write-probe'):
            with self.assertRaises(pywintypes.error) as caught:self.m.WindowsCredentialVault().write(b'fixture-only','S-1-5-21-100')
        self.assertEqual(caught.exception.winerror,87)

    def test_listener_refuses_wildcard_ipv6_duplicate_and_unowned_ports(self):
        import psutil
        def entry(ip,pid=1122):return SimpleNamespace(status=psutil.CONN_LISTEN,laddr=SimpleNamespace(port=8080,ip=ip),pid=pid)
        for rows in [[entry('0.0.0.0')],[entry('::')],[entry('127.0.0.1'),entry('127.0.0.1')],[entry('127.0.0.1',None)]]:
            with patch.object(psutil,'net_connections',return_value=rows),patch.object(self.m,'_process_identity') as identity:
                with self.assertRaises(self.m.LocalConnectionError):self.m._listener_identity()
                identity.assert_not_called()

    def test_listener_observes_exact_owned_pid_and_no_listener_is_waitable(self):
        import psutil
        row=SimpleNamespace(status=psutil.CONN_LISTEN,laddr=SimpleNamespace(port=8080,ip='127.0.0.1'),pid=1122)
        identity=self.m.ServiceIdentity(1122,1234.5,r'C:\Fixture\python.exe','S-1-5-21-100')
        with patch.object(psutil,'net_connections',return_value=[row]),patch.object(self.m,'_process_identity',return_value=identity) as provider:
            self.assertEqual(self.m._listener_identity(),identity);provider.assert_called_once_with(1122)
        with patch.object(psutil,'net_connections',return_value=[]):self.assertIsNone(self.m._listener_identity())
        ipv6=SimpleNamespace(status=psutil.CONN_LISTEN,laddr=SimpleNamespace(port=8080,ip='::1'),pid=9999)
        with patch.object(psutil,'net_connections',return_value=[row,ipv6]),patch.object(self.m,'_process_identity',return_value=identity) as provider:
            self.assertEqual(self.m._listener_identity(),identity);provider.assert_called_once_with(1122)
        with patch.object(psutil,'net_connections',return_value=[ipv6]),patch.object(self.m,'_process_identity') as provider:
            self.assertIsNone(self.m._listener_identity());provider.assert_not_called()

    def test_actual_backend_lifespan_owns_and_cancels_connection_setup_without_fleet_start(self):
        source=(Path(__file__).resolve().parents[2]/'backend/AI_BS_Backend.py').read_text(encoding='utf-8')
        function=next(node for node in ast.parse(source).body if isinstance(node,ast.AsyncFunctionDef) and node.name=='lifespan')
        events=[]
        async def publisher(secret):
            self.assertEqual(secret,'fixture-local');events.append('started')
            try:await asyncio.Event().wait()
            finally:events.append('cancelled')
        scope={'asynccontextmanager':asynccontextmanager,'os':SimpleNamespace(name='nt',environ={'AI_BS_ADMIN_KEY':'fixture-local'}),
               'asyncio':asyncio,'sys':sys,'time':SimpleNamespace(time=lambda:0),
               'daemon_supervisor':SimpleNamespace(start_all=lambda:events.append('FLEET_STARTED'),stop_all=lambda:events.append('FLEET_STOPPED')),
               'telemetry_hub':SimpleNamespace(active_connections=[]),'FastAPI':object}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<actual-backend-lifespan>','exec'),scope)
        async def run():
            async with scope['lifespan'](object()):
                await asyncio.sleep(0);await asyncio.sleep(0)
                self.assertEqual(events,['started'])
        with patch.dict(sys.modules,{'core.ai_adapter':SimpleNamespace(load_all_states=lambda:None)}),patch.object(self.m,'publish_when_listening',publisher),redirect_stdout(io.StringIO()):
            asyncio.run(run())
        self.assertEqual(events,['started','cancelled'])


class PeerOwnershipProofTests(unittest.TestCase):
    """Kernel-tuple fixtures only: no real vault, HTTP or credential access."""
    def setUp(self):
        import psutil
        self.psutil=psutil
        self.m=importlib.import_module('native_studio.local_connection')
        self.identity=self.m.ServiceIdentity(1122,1234.5,r'C:\Fixture\python.exe','S-1-5-21-100')

    def row(self,status=None,ip='127.0.0.1',pid=1122,remote=None,port=8080):
        return SimpleNamespace(status=status or self.psutil.CONN_NONE,
            laddr=SimpleNamespace(ip=ip,port=port),
            raddr=SimpleNamespace(ip=remote[0],port=remote[1]) if remote else (),pid=pid)

    def probe(self, *, connect_error=None, peer=('127.0.0.1',8080)):
        class Probe:
            closed=False
            calls=[]
            def __enter__(self):return self
            def __exit__(self,*_):self.closed=True
            def settimeout(self,value):self.timeout=value
            def connect(self,target):
                self.calls.append(target)
                if connect_error:raise connect_error
            def getsockname(self):return ('127.0.0.1',54321)
            def getpeername(self):return peer
            def send(self,*_):raise AssertionError('Probe must send no application bytes')
            sendall=send
        return Probe()

    def test_unique_none_candidate_requires_exact_established_peer_and_stable_identity(self):
        probe=self.probe()
        rows=[[self.row()], [self.row(self.psutil.CONN_ESTABLISHED,remote=('127.0.0.1',54321))]]
        with patch.object(self.psutil,'net_connections',side_effect=rows),\
             patch.object(self.m.socket,'socket',return_value=probe),\
             patch.object(self.m,'_process_identity',return_value=self.identity) as identity:
            self.assertEqual(self.m._listener_identity(),self.identity)
        self.assertEqual(probe.calls,[('127.0.0.1',8080)])
        self.assertEqual(probe.timeout,1.0)
        self.assertTrue(probe.closed)
        self.assertEqual(identity.call_args_list,[unittest.mock.call(1122),unittest.mock.call(1122)])

    def test_wildcard_duplicate_zero_or_bool_candidate_never_connects(self):
        cases=[[self.row(ip='0.0.0.0')],[self.row(ip='::')],
               [self.row(),self.row()], [self.row(pid=0)], [self.row(pid=None)], [self.row(pid=True)]]
        for rows in cases:
            with self.subTest(rows=rows),patch.object(self.psutil,'net_connections',return_value=rows),\
                 patch.object(self.m.socket,'socket') as factory:
                with self.assertRaises(self.m.LocalConnectionError):self.m._listener_identity()
                factory.assert_not_called()

    def test_absent_and_ipv6_only_candidates_never_connect(self):
        for rows in ([],[self.row(ip='::1')],[self.row(remote=('127.0.0.1',12345))]):
            with patch.object(self.psutil,'net_connections',return_value=rows),\
                 patch.object(self.m.socket,'socket') as factory:
                self.assertIsNone(self.m._listener_identity())
                factory.assert_not_called()

    def test_wrong_owner_duplicate_peer_and_nonestablished_proof_reject(self):
        correct=self.row(self.psutil.CONN_ESTABLISHED,remote=('127.0.0.1',54321))
        cases=[[self.row(self.psutil.CONN_ESTABLISHED,pid=1123,remote=('127.0.0.1',54321))],
               [correct,correct], [self.row(remote=('127.0.0.1',54321))],
               [self.row(self.psutil.CONN_ESTABLISHED,pid=0,remote=('127.0.0.1',54321))]]
        for peers in cases:
            probe=self.probe()
            with self.subTest(peers=peers),patch.object(self.psutil,'net_connections',side_effect=[[self.row()],peers]),\
                 patch.object(self.m.socket,'socket',return_value=probe),\
                 patch.object(self.m,'_process_identity',return_value=self.identity):
                with self.assertRaises(self.m.LocalConnectionError):self.m._listener_identity()
                self.assertTrue(probe.closed)

    def test_wrong_remote_tuple_or_peerless_row_times_out_without_adoption(self):
        cases=[[self.row(self.psutil.CONN_ESTABLISHED,remote=('127.0.0.1',54322))],
               [self.row(self.psutil.CONN_ESTABLISHED,remote=('127.0.0.2',54321))],
               [self.row(self.psutil.CONN_ESTABLISHED)]]
        for peers in cases:
            probe=self.probe()
            with patch.object(self.psutil,'net_connections',side_effect=[[self.row()],peers]),\
                 patch.object(self.m.socket,'socket',return_value=probe),\
                 patch.object(self.m,'_process_identity',return_value=self.identity),\
                 patch.object(self.m.time,'monotonic',side_effect=[0.0,2.0]):
                with self.assertRaises(self.m.LocalConnectionError):self.m._listener_identity()
                self.assertTrue(probe.closed)

    def test_connect_timeout_or_wrong_connected_endpoint_rejects(self):
        for probe in (self.probe(connect_error=TimeoutError()),self.probe(peer=('127.0.0.2',8080))):
            with patch.object(self.psutil,'net_connections',return_value=[self.row()]),\
                 patch.object(self.m.socket,'socket',return_value=probe),\
                 patch.object(self.m,'_process_identity',return_value=self.identity):
                with self.assertRaises(self.m.LocalConnectionError):self.m._listener_identity()
                self.assertTrue(probe.closed)

    def test_pid_reuse_creation_change_during_probe_rejects(self):
        replacement=self.m.ServiceIdentity(1122,1235.5,self.identity.exe,self.identity.owner_sid)
        probe=self.probe()
        with patch.object(self.psutil,'net_connections',side_effect=[[self.row()],
                [self.row(self.psutil.CONN_ESTABLISHED,remote=('127.0.0.1',54321))]]),\
             patch.object(self.m.socket,'socket',return_value=probe),\
             patch.object(self.m,'_process_identity',side_effect=[self.identity,replacement]):
            with self.assertRaises(self.m.LocalConnectionError):self.m._listener_identity()
        self.assertTrue(probe.closed)

    def test_same_owner_handshake_waits_for_established_before_authorizing(self):
        for status in (self.psutil.CONN_SYN_SENT,self.psutil.CONN_SYN_RECV):
            probe=self.probe()
            sequence=[[self.row()],
                [self.row(status,remote=('127.0.0.1',54321))],
                [self.row(self.psutil.CONN_ESTABLISHED,remote=('127.0.0.1',54321))]]
            with self.subTest(status=status),patch.object(self.psutil,'net_connections',side_effect=sequence),\
                 patch.object(self.m.socket,'socket',return_value=probe),\
                 patch.object(self.m.time,'sleep'),\
                 patch.object(self.m,'_process_identity',return_value=self.identity) as identity:
                self.assertEqual(self.m._listener_identity(),self.identity)
                self.assertEqual(identity.call_count,2)
            self.assertTrue(probe.closed)

    def test_stuck_handshake_expires_and_closing_states_are_not_authority(self):
        for status in (self.psutil.CONN_SYN_RECV,self.psutil.CONN_NONE,self.psutil.CONN_CLOSE_WAIT,self.psutil.CONN_FIN_WAIT1):
            probe=self.probe()
            with self.subTest(status=status),patch.object(self.psutil,'net_connections',side_effect=[
                    [self.row()],[self.row(status,remote=('127.0.0.1',54321))]]),\
                 patch.object(self.m.socket,'socket',return_value=probe),\
                 patch.object(self.m.time,'monotonic',side_effect=[0.0,2.0]),\
                 patch.object(self.m,'_process_identity',return_value=self.identity):
                with self.assertRaises(self.m.LocalConnectionError):self.m._listener_identity()
            self.assertTrue(probe.closed)

    def test_diagnostics_distinguishes_tcp_probe_from_http_or_secret_bytes(self):
        original=LocalConnectionTests()
        # Pure injected connection simulates observation counters; no real vault.
        owner=self.identity
        blob=json.dumps({'schema':1,'origin':self.m.ORIGIN,'service':owner.__dict__,'secret':'fixture-only'}).encode()
        def listener():
            self.m._probe_activity.attempts=self.m._probe_counts()[0]+1
            self.m._probe_activity.connected=self.m._probe_counts()[1]+1
            return owner
        connection=self.m.LocalConnection(vault=SimpleNamespace(read=lambda:blob),
            current_identity=lambda:owner,listener_identity=listener)
        report=self.m.connection_diagnostics(connection=connection)
        self.assertTrue(report['available'])
        self.assertTrue(report['networkRequestsSent'])
        self.assertEqual(report['tcpProbeAttempts'],2)
        self.assertEqual(report['tcpConnectionsOpened'],2)
        self.assertFalse(report['httpRequestsSent'])
        self.assertEqual(report['credentialBytesSent'],0)


if __name__=='__main__':unittest.main()
