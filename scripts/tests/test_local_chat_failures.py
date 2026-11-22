"""Curated local failures, bounded provider data and no generation replay."""
import json
import unittest
from unittest.mock import patch

import httpx

from scripts.tests import test_local_chat_inference as fixtures

transport=fixtures.transport


class LocalChatFailureTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls=[];self.receipts=[];self.admission=fixtures.Admission()
        self.response=None;self.failure=None
        actual_client=httpx.AsyncClient
        def handler(request):
            self.calls.append(request)
            if self.failure is not None:raise self.failure
            return self.response
        def client(**kwargs):
            return actual_client(transport=httpx.MockTransport(handler),**kwargs)
        for guard in (patch.object(transport,'get_dispatcher',return_value=self.admission),
                      patch.object(transport.httpx,'AsyncClient',side_effect=client)):
            guard.start();self.addCleanup(guard.stop)
        self.kw=dict(model='fixture:latest',prompt='private prompt',system='system',role='primary',
                     endpoints=['http://127.0.0.1:11434/api/generate','http://127.0.0.1:11435/api/generate'],
                     receipt_sink=self.receipts.append)

    async def failure_code(self,stream):
        self.calls.clear();self.receipts.clear()
        before=self.admission.released
        if stream:
            text=''.join([part async for part in transport.stream_local(**self.kw)])
        else:
            with self.assertRaises(transport.LocalInferenceError) as failure:
                await transport.complete_local(**self.kw)
            text=str(failure.exception)
        self.assertEqual(len(self.calls),1,'A transmitted request must never be replayed')
        self.assertEqual(self.admission.released,before+1)
        self.assertFalse(self.receipts[-1]['completion_verified'])
        self.assertNotIn('private prompt',json.dumps(self.receipts))
        self.assertNotIn('UNTRUSTED_SECRET',text+json.dumps(self.receipts))
        return self.receipts[-1]['error_code']

    async def test_missing_model_and_route_404_have_distinct_curated_codes(self):
        cases=[(dict(error="model 'fixture:latest' not found"),'model_not_found'),
               (dict(detail='Not Found'),'provider_endpoint_not_found'),
               (dict(error='UNTRUSTED_SECRET'),'provider_http_404'),
               (dict(error="model 'different:latest' not found"),'provider_http_404')]
        for stream in (False,True):
            for body,code in cases:
                with self.subTest(stream=stream,code=code):
                    self.response=httpx.Response(404,json=body)
                    self.assertEqual(await self.failure_code(stream),code)

    async def test_plain_missing_route_is_classified_and_oversized_error_is_not(self):
        for stream in (False,True):
            self.response=httpx.Response(404,text='404 page not found')
            self.assertEqual(await self.failure_code(stream),'provider_endpoint_not_found')
            self.response=httpx.Response(404,json={'error':"model 'fixture:latest' not found",'padding':'x'*5000})
            self.assertEqual(await self.failure_code(stream),'provider_http_404')

    async def test_timeout_and_protocol_failures_are_curated_without_replay(self):
        cases=[(httpx.ReadTimeout,'local_read_timeout'),(httpx.WriteTimeout,'local_write_timeout'),
               (httpx.PoolTimeout,'local_pool_timeout'),(httpx.RemoteProtocolError,'local_protocol_error'),
               (httpx.ReadError,'local_read_error'),(httpx.WriteError,'local_write_error')]
        for stream in (False,True):
            for kind,code in cases:
                with self.subTest(stream=stream,code=code):
                    self.failure=kind('UNTRUSTED_SECRET')
                    self.assertEqual(await self.failure_code(stream),code)

    async def test_partial_read_timeout_preserves_text_and_does_not_replay(self):
        class Interrupted(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'{"model":"fixture:latest","response":"partial answer","done":false}\n'
                raise httpx.ReadTimeout('UNTRUSTED_SECRET')
        self.response=httpx.Response(200,stream=Interrupted())
        text=''.join([part async for part in transport.stream_local(**self.kw)])
        self.assertIn('partial answer',text)
        self.assertIn('no replay was attempted',text)
        self.assertEqual(self.receipts[-1]['error_code'],'local_read_timeout')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.admission.released,1)

    async def test_streamed_404_body_read_is_bounded(self):
        class LargeError(httpx.AsyncByteStream):
            consumed=0
            async def __aiter__(self):
                for _ in range(100):
                    self.consumed+=1
                    yield b'x'*1024
        body=LargeError();self.response=httpx.Response(404,stream=body)
        self.assertEqual(await self.failure_code(True),'provider_http_404')
        self.assertEqual(body.consumed,5)


if __name__=='__main__':unittest.main()
