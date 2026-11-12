"""Real in-process pipe framing and existing client; not owned GUI qualification."""
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from security.native_creative_channel import CreativePipes
from native_studio.creative_pipe_io import PipeEndpoint, PipeIOError
from native_studio.creative_session import CreativeSession, CreativeSessionError, decode_bootstrap
from native_studio.screenplay_client import ScreenplayClient, ScreenplayError


@unittest.skipUnless(os.name=='nt','Windows pipe transport')
class PipeSessionTests(unittest.TestCase):
    @contextmanager
    def server(self, alter=None):
        with CreativePipes() as resources:
            parent=PipeEndpoint(*resources.parent_fds)
            child=PipeEndpoint(resources._child_read,resources._child_write)
            raw={'version':1,'grant':'nch_g_'+'a'*43,'project':'fixture','revision':'r',
                 'source_sha256':'a'*64,'candidate_sha256':'b'*64}
            packet=decode_bootstrap(json.dumps(raw).encode())
            self.now=100
            self.messages=[]
            stop=threading.Event();errors=[]
            revision=['r'];content=['Synthetic text']
            def serve():
                try:
                    while not stop.is_set():
                        request=parent.receive(timeout=10)
                        self.messages.append(request)
                        op=request['operation'];p=request['payload']
                        response={'version':1,'id':request['id'],'status':200}
                        if op=='redeem':response['body']={'lease':'nch_l_'+'b'*43,
                            'project':'fixture','revision':'r','source_sha256':'a'*64,'expires_in':60}
                        elif op=='read':response['body']={'project':'fixture','revision':revision[0],'content':content[0]}
                        elif op=='save':
                            if p['expected_revision']!=revision[0]:
                                response.update(status=409,body={'detail':'Conflict'})
                            else:
                                content[0]=p['content'];revision[0]='r2'
                                response['body']={'project':'fixture','status':'success','revision':'r2'}
                        else:
                            binary=b'%PDF-1.4\nSynthetic test only' if op=='export_pdf' else b'<FinalDraft/>'
                            response.update(body_base64=base64.b64encode(binary).decode(),
                                headers={'x-ai-bs-artifact-sha256':hashlib.sha256(binary).hexdigest()})
                        parent.send(alter(response,request) if alter else response,timeout=5)
                except PipeIOError:
                    if not stop.is_set():errors.append('Unexpected pipe failure')
                except Exception as error:
                    errors.append(type(error).__name__)
            worker=threading.Thread(target=serve,name='synthetic creative service')
            worker.start()
            session=CreativeSession(endpoint=child,headers_provider=lambda:(_ for _ in ()).throw(AssertionError('No credentials')),
                                    clock=lambda:self.now)
            try:
                with patch('native_studio.screenplay_client.httpx.Client',side_effect=AssertionError('No HTTP')):
                    yield session,packet
            finally:
                stop.set()
                self.assertTrue(session.close())
                self.assertTrue(parent.close())
                worker.join(timeout=3)
                self.assertFalse(worker.is_alive())
                self.assertFalse(errors,errors)

    def test_existing_client_read_save_reopen_and_binary_exports_over_actual_pipes(self):
        with self.server() as (session,packet):
            session.redeem(packet)
            client=ScreenplayClient(creative_session=session)
            self.assertEqual(client.read('fixture')['content'],'Synthetic text')
            self.assertEqual(client.save('fixture','Edited Unicode é','r')['revision'],'r2')
            self.assertEqual(client.read('fixture')['content'],'Edited Unicode é')
            self.assertTrue(client.export('fixture','pdf','r2').startswith(b'%PDF-'))
            self.assertEqual(client.export('fixture','fdx','r2'),b'<FinalDraft/>')
            self.assertEqual([m['id'] for m in self.messages],list(range(1,len(self.messages)+1)))
            with self.assertRaises(CreativeSessionError):session.headers(project='fixture',operation='read')

    def test_expiry_and_wrong_scope_issue_no_request_or_fallback(self):
        with self.server() as (session,packet):
            session.redeem(packet)
            client=ScreenplayClient(creative_session=session)
            with self.assertRaises(ScreenplayError):client.read('foreign')
            self.now=160
            with self.assertRaises(ScreenplayError):client.read('fixture')
            self.assertEqual(len(self.messages),1)

    def test_wrong_response_id_is_terminal_without_replay(self):
        def wrong(response,request):
            if request['operation']=='read':response['id']+=1
            return response
        with self.server(wrong) as (session,packet):
            session.redeem(packet);client=ScreenplayClient(creative_session=session)
            with self.assertRaises(ScreenplayError):client.read('fixture')
            with self.assertRaises(ScreenplayError):client.read('fixture')
            self.assertEqual(len(self.messages),2)

    def test_bad_binary_hash_is_refused_without_alternate_export(self):
        def wrong(response,request):
            if request['operation']=='export_pdf':response['headers']['x-ai-bs-artifact-sha256']='0'*64
            return response
        with self.server(wrong) as (session,packet):
            session.redeem(packet);client=ScreenplayClient(creative_session=session)
            with self.assertRaises(ScreenplayError):client.export('fixture','pdf','r')
            self.assertEqual([m['operation'] for m in self.messages],['redeem','read','export_pdf'])

    def test_revision_conflict_is_reported_and_does_not_replay_save(self):
        with self.server() as (session,packet):
            session.redeem(packet);client=ScreenplayClient(creative_session=session)
            with self.assertRaises(ScreenplayError):client.save('fixture','Retained draft','old')
            self.assertEqual(len([m for m in self.messages if m['operation']=='save']),1)
            self.assertEqual(client.read('fixture')['revision'],'r')

    def test_authority_refusal_is_terminal_not_reusable(self):
        def refused(response,request):
            if request['operation']=='read':return {'version':1,'id':request['id'],'status':403,'body':{'detail':'Denied'}}
            return response
        with self.server(refused) as (session,packet):
            session.redeem(packet);client=ScreenplayClient(creative_session=session)
            for _ in range(2):
                with self.assertRaises(ScreenplayError):client.read('fixture')
            self.assertEqual(len(self.messages),2)

    def test_interruption_after_response_prevents_later_io(self):
        with self.server() as (session,packet):
            session.redeem(packet)
            endpoint=session._channel._endpoint
            original=endpoint.exchange
            def interrupted(*args,**kwargs):
                original(*args,**kwargs)
                raise KeyboardInterrupt()
            with patch.object(endpoint,'exchange',side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    session.channel_request('GET','/api/screenwriting/read',{'project_name':'fixture'})
            with self.assertRaises(ScreenplayError):ScreenplayClient(creative_session=session).read('fixture')
            self.assertEqual(len(self.messages),2)

    def test_wrong_redemption_scope_closes_channel_before_client_can_use_it(self):
        def wrong(response,request):
            if request['operation']=='redeem':response['body']['source_sha256']='c'*64
            return response
        with self.server(wrong) as (session,packet):
            with self.assertRaises(CreativeSessionError):session.redeem(packet)
            self.assertIsNone(session._lease)
            with self.assertRaises(ScreenplayError):ScreenplayClient(creative_session=session).read('fixture')
            self.assertEqual(len(self.messages),1)

    def test_incomplete_close_preserves_endpoint_for_later_drain(self):
        with self.server() as (session,packet):
            session.redeem(packet)
            retained=session._channel._endpoint
            with patch.object(retained,'close',return_value=False):
                self.assertFalse(session.close())
            self.assertIs(session._channel._endpoint,retained)
            self.assertTrue(session.close())
            with self.assertRaises(ScreenplayError):ScreenplayClient(creative_session=session).read('fixture')


if __name__=='__main__':unittest.main(verbosity=2)
