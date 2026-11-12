"""Native shared-chat admission and UI dispatch, without live models or commands."""
import copy,json,os,time,unittest
from unittest.mock import patch
import httpx
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

class NativeChatServiceTests(unittest.TestCase):
    def service(self,handler,headers=None):
        from native_studio.chat_service import NativeChatService
        return NativeChatService(headers_provider=headers or (lambda:{'Authorization':'Bearer fixture-only'}),transport=httpx.MockTransport(handler))

    def test_shared_route_preserves_unicode_history_and_explicit_search_only(self):
        requests=[]
        def handler(req):
            requests.append(req);return httpx.Response(200,text='Hello café\n```powershell\nWrite-Output fixture\n```',headers={'content-type':'text/event-stream'})
        s=self.service(handler);parts=[]
        reply=s.stream('Explain a file',history=[['prior','reply']],on_text=parts.append)
        self.assertEqual(reply,''.join(parts));self.assertIn('café',reply)
        self.assertEqual(str(requests[0].url),'http://127.0.0.1:8080/api/v1/hybrid-chat/stream')
        body=json.loads(requests[0].content);self.assertEqual(body['messages'],[{'role':'user','content':'prior'},{'role':'assistant','content':'reply'}])
        self.assertFalse(body['use_web_search']);self.assertEqual(body['web_search_query'],'')
        s.stream('current query',history=[['private older','private reply']],use_web_search=True)
        self.assertEqual(json.loads(requests[-1].content)['web_search_query'],'current query')
        self.assertEqual(len(requests),2)

    def test_authentication_redirect_failure_and_transport_error_never_retry(self):
        from native_studio.chat_service import NativeChatError
        for status in [401,403,302,500]:
            seen=[]
            def handler(req):seen.append(req);return httpx.Response(status,text='private-server-detail',headers={'location':'https://untrusted.invalid/'})
            with self.assertRaises(NativeChatError)as error:self.service(handler).stream('fixture')
            self.assertEqual(len(seen),1);self.assertNotIn('private-server-detail',str(error.exception))
        seen=[]
        def handler(req):seen.append(req);raise httpx.ReadTimeout('private transport detail')
        with self.assertRaises(NativeChatError):self.service(handler).stream('fixture')
        self.assertEqual(len(seen),1)

    def test_metadata_is_not_rendered_and_empty_reply_is_not_success(self):
        s=self.service(lambda req:httpx.Response(200,text='<!--AI-BS-METADATA:{"private":"fixture"}-->\nVisible response'))
        chunks=[];self.assertEqual(s.stream('fixture',on_text=chunks.append),'\nVisible response')
        self.assertEqual(''.join(chunks),'\nVisible response')
        from native_studio.chat_service import NativeChatError
        with self.assertRaises(NativeChatError):self.service(lambda req:httpx.Response(200,text='')).stream('fixture')

    def test_backend_failure_under_http200_does_not_confirm_a_reply(self):
        from native_studio.chat_service import NativeChatError, safe_chat_failure_notice
        service=self.service(lambda req:httpx.Response(200,text='Error in sovereign reasoning matrix: private-provider-fixture'))
        with self.assertRaises(NativeChatError) as error:service.stream('fixture')
        notice=safe_chat_failure_notice('NativeChatError: '+str(error.exception))
        self.assertIn('could not complete',notice)
        self.assertNotIn('private-provider-fixture',str(error.exception))

    def test_local_budget_failure_under_http200_retains_failure_semantics(self):
        from native_studio.chat_service import NativeChatError
        text='\n\n\nLocal inference did not complete (context_budget_exceeded). No answer is claimed.\n'
        with self.assertRaises(NativeChatError) as error:
            self.service(lambda req:httpx.Response(200,text=text)).stream('fixture')
        self.assertIn('context limit',str(error.exception))

    def test_partial_reply_and_context_notice_cannot_hide_failed_primary_receipt(self):
        from native_studio.chat_service import NativeChatError
        text='> Context note: optional background omitted.\nPartial text\n<!--AI-BS-METADATA:'+json.dumps({'role':'primary','status':'error','generation_verified':False,'completion_verified':False,'error_code':'provider_http_404'})+'-->\nLocal inference did not complete (provider_http_404). No answer is claimed.\n'
        with self.assertRaises(NativeChatError) as error:
            self.service(lambda req:httpx.Response(200,text=text)).stream('fixture')
        self.assertIn('unavailable in the local service',str(error.exception))

    def test_split_primary_metadata_requires_verified_terminal_completion(self):
        from native_studio.chat_service import _VisibleStream
        for status,generation,completion in [('requesting',False,False),('completed',True,False),('completed',True,True)]:
            parser=_VisibleStream();text='Reply<!--AI-BS-METADATA:'+json.dumps({'role':'primary','status':status,'generation_verified':generation,'completion_verified':completion})+'-->'
            result=''.join(parser.feed(c) for c in text)+parser.feed('',final=True)
            self.assertEqual(result,'Reply')
            self.assertEqual(parser.latest_primary,{'status':status,'generation_verified':generation,'completion_verified':completion,'error_code':None})
            self.assertFalse(parser.invalid_metadata)
        broken=_VisibleStream();broken.feed('partial<!--AI-BS-METADATA:{');broken.feed('',final=True)
        self.assertTrue(broken.invalid_metadata)

    def test_private_connection_is_required_before_any_request(self):
        from native_studio.chat_service import NativeChatError
        seen=[]
        with self.assertRaises(NativeChatError):self.service(lambda req:seen.append(req),headers=lambda:{}).stream('fixture')
        self.assertEqual(seen,[])

    def test_connection_identity_failure_is_classified_without_transport_or_private_detail(self):
        from native_studio.chat_service import NativeChatError, safe_chat_failure_notice
        from native_studio.local_connection import LocalConnectionError
        seen=[]
        def unavailable():raise LocalConnectionError('private-vault-fixture')
        with self.assertRaises(NativeChatError) as error:
            self.service(lambda req:seen.append(req),headers=unavailable).stream('fixture')
        notice=safe_chat_failure_notice('NativeChatError: '+str(error.exception))
        self.assertIn('private local connection',notice)
        self.assertNotIn('private-vault-fixture',notice)
        self.assertEqual(seen,[])

    def test_failure_notice_allows_only_curated_messages_and_http_status(self):
        from native_studio.chat_service import safe_chat_failure_notice
        self.assertIn('HTTP503',safe_chat_failure_notice('NativeChatError: The chat service returned HTTP503; no complete response was confirmed.'))
        for message in ['private-token-fixture', 'NativeChatError: private-token-fixture',
                        'NativeChatError: The chat service returned HTTP503; secret-fixture', None]:
            notice=safe_chat_failure_notice(message)
            self.assertNotIn('fixture',notice)
            self.assertIn('not confirmed',notice)

    def test_explicit_runtime_request_uses_one_authenticated_service_call(self):
        seen=[]
        def handler(req):
            seen.append(req);return httpx.Response(200,json={'status':'success','returncode':0,'stdout':'fixture output','stderr':''})
        result=self.service(handler).execute_once('Write-Output fixture',runtime='powershell')
        self.assertEqual(result['returncode'],0);self.assertEqual(len(seen),1)
        self.assertEqual(seen[0].url.path,'/api/executive/run')
        self.assertEqual(json.loads(seen[0].content)['command_type'],'powershell')

class NativeChatDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app=QApplication.instance()or QApplication([])
    def setUp(self):
        from scripts.tests.test_native_executive_view import Bus,Store
        from native_studio.bs_chat_ide_full import BsChatIdeFullView
        self.bus=Bus();self.service=type('Service',(),{})();self.calls=[]
        def stream(prompt,**kwargs):
            self.calls.append((prompt,kwargs));kwargs['on_text']('Service fixture reply');return 'Service fixture reply'
        self.service.stream=stream
        self.view=BsChatIdeFullView(self.bus,session_store=Store())
        guard=patch.object(self.view,'_execute_host_intent_standalone',side_effect=AssertionError('Legacy local dispatch is forbidden in this fixture'))
        guard.start();self.addCleanup(guard.stop)
        self.view.chat_service=self.service;self.bus.drain();self.addCleanup(self.view.shutdown);self.addCleanup(self.view.deleteLater)
    def test_normal_command_like_text_uses_service_and_keeps_draft_until_ack(self):
        prompt='Get-Content is a command; explain what it does'
        self.view.input_edit.setText(prompt)
        with patch.object(self.view,'_run_powershell_task',side_effect=AssertionError('No local host dispatch')):
            self.view._send();self.assertEqual(self.view.input_edit.text(),prompt)
            self.assertFalse(self.view.send_btn.isEnabled());self.bus.drain()
        self.assertEqual([x[0]for x in self.calls],[prompt]);self.assertEqual(self.view.input_edit.text(),'')
        self.assertEqual(self.view._conversation_history[-1],(prompt,'Service fixture reply'))
    def test_failure_retains_draft_and_newer_edit_is_not_cleared_by_success(self):
        def failed(*args,**kwargs):raise RuntimeError('private-server-fixture')
        self.service.stream=failed;self.view.input_edit.setText('retained fixture');self.view._send();self.bus.drain()
        self.assertEqual(self.view.input_edit.text(),'retained fixture');self.assertNotIn('private-server-fixture',self.view.chat_display.toPlainText())
        self.service.stream=lambda *args,**kwargs:'success fixture'
        self.view._send();self.view.input_edit.setText('newer unsent fixture');self.bus.drain()
        self.assertEqual(self.view.input_edit.text(),'newer unsent fixture')
    def test_saved_media_button_opens_references_without_replaying_chat(self):
        self.view.chat_display.setPlainText('![Saved](/api/comfy/media?filename=fixture.png)')
        with patch.object(self.view.media_panel,'add_references')as add:
            self.view.open_media_btn.click()
        self.assertEqual(self.calls,[]);add.assert_called_once_with(self.view.chat_display.toPlainText())

    def test_connection_failure_shows_safe_reason_without_erasing_partial_reply_or_draft(self):
        from native_studio.chat_service import NativeChatError
        def failed(*args,**kwargs):
            kwargs['on_text']('retained partial fixture')
            raise NativeChatError('The private chat connection is not ready. No API key entry is required.')
        self.service.stream=failed
        self.view.input_edit.setText('retained fixture')
        self.view._send();self.bus.drain()
        text=self.view.chat_display.toPlainText()
        self.assertIn('private local connection',text)
        self.assertIn('retained partial fixture',text)
        self.assertEqual(self.view.input_edit.text(),'retained fixture')
        self.assertEqual(self.view._conversation_history,[])

if __name__=='__main__':unittest.main()
