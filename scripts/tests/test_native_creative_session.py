import json
from pathlib import Path
import sys
import unittest
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from native_studio.creative_session import CreativeSession, CreativeSessionError, decode_bootstrap
from native_studio.screenplay_client import ScreenplayClient, ScreenplayError


class NativeSessionTests(unittest.TestCase):
    def setUp(self):
        self.raw=dict(version=1,grant='nch_g_'+'a'*43,project='fixture',revision='r',source_sha256='a'*64,candidate_sha256='b'*64)
        self.packet=decode_bootstrap(json.dumps(self.raw).encode())
        self.now=100
        self.requests=[]
        self.result=dict(lease='nch_l_'+'b'*43,project='fixture',revision='r',source_sha256='a'*64,expires_in=60)
        def respond(request):
            self.requests.append(request)
            return httpx.Response(200,json=self.result)
        self.session=CreativeSession(headers_provider=lambda:{'X-Admin-Key':'synthetic-local-only'},
            transport=httpx.MockTransport(respond),clock=lambda:self.now)

    def test_redeem_uses_fixed_loopback_post_body_and_hides_secret_repr(self):
        self.session.redeem(self.packet)
        request=self.requests[0]
        self.assertEqual(str(request.url),'http://127.0.0.1:8080/api/screenwriting/native/redeem')
        self.assertEqual(json.loads(request.content),{'grant':self.raw['grant']})
        self.assertNotIn(self.raw['grant'],repr(self.packet))
        self.assertNotIn(self.result['lease'],repr(self.session))
        self.assertIn('X-AI-BS-Creative-Lease',self.session.headers(project='fixture',operation='read'))

    def test_scope_expiry_and_close_fail_without_local_admin_fallback(self):
        self.session.redeem(self.packet)
        for project,op in [('foreign','read'),('fixture','import'),('fixture','model')]:
            with self.assertRaises(CreativeSessionError):self.session.headers(project=project,operation=op)
        self.now=160
        with self.assertRaises(CreativeSessionError):self.session.headers(project='fixture',operation='read')
        self.session.close()
        with self.assertRaises(CreativeSessionError):self.session.headers(project='fixture',operation='read')

    def test_response_owner_scope_mismatch_or_invalid_lifetime_cannot_connect(self):
        for change in ({'project':'foreign'},{'revision':'other'},{'source_sha256':'c'*64},{'expires_in':True},{'expires_in':301}):
            saved=dict(self.result);self.result.update(change)
            with self.assertRaises(CreativeSessionError):self.session.redeem(self.packet)
            self.assertIsNone(self.session._lease)
            self.result=saved

    def test_packets_reject_duplicates_extra_owner_and_oversize(self):
        for raw in (b'{"version":1,"version":1}',b'x'*4097,json.dumps(dict(self.raw,owner='forged')).encode()):
            with self.assertRaises(CreativeSessionError):decode_bootstrap(raw)

    def test_missing_trusted_local_channel_makes_no_request(self):
        self.session._headers_provider=lambda:{}
        with self.assertRaises(CreativeSessionError):self.session.redeem(self.packet)
        self.assertEqual(self.requests,[])

    def test_redirect_is_not_followed(self):
        self.session._transport=httpx.MockTransport(lambda request:httpx.Response(307,headers={'location':'https://example.invalid'}))
        with self.assertRaises(CreativeSessionError):self.session.redeem(self.packet)
        self.assertIsNone(self.session._lease)

    def test_oversize_redemption_response_fails_without_retaining_lease(self):
        consumed=[]
        class Oversize(httpx.SyncByteStream):
            def __iter__(self):
                yield b'x'*4097
                consumed.append('beyond-limit')
                yield b'x'*4097
        self.session._transport=httpx.MockTransport(lambda request:httpx.Response(200,stream=Oversize()))
        with self.assertRaises(CreativeSessionError):self.session.redeem(self.packet)
        self.assertIsNone(self.session._lease)
        self.assertEqual(consumed,[])

    def test_native_writer_uses_only_delegated_scope_and_never_falls_back(self):
        self.session.redeem(self.packet)
        sent=[]
        client=ScreenplayClient(creative_session=self.session,
            transport=httpx.MockTransport(lambda request:(sent.append(request) or httpx.Response(200,json={}))))
        client._request('GET','/api/screenwriting/read',params={'project_name':'fixture'})
        self.assertEqual(sent[0].headers['X-AI-BS-Creative-Lease'],self.result['lease'])
        for method,route,kwargs in [('GET','/api/screenwriting/read',{'params':{'project_name':'foreign'}}),
                                    ('GET','/api/screenwriting/projects',{})]:
            with self.assertRaises(ScreenplayError):client._request(method,route,**kwargs)
        self.now=160
        with self.assertRaises(ScreenplayError):client._request('GET','/api/screenwriting/read',params={'project_name':'fixture'})
        self.assertEqual(len(sent),1)


if __name__=='__main__':unittest.main()
