import importlib,json,unittest
from unittest.mock import Mock
import httpx

P='/api/v1/executive'


class ExecutiveServiceTests(unittest.TestCase):
    def setUp(self):
        self.m=importlib.import_module('native_studio.executive_service')
        self.calls=[];self.fail=None
        self.rows={
            '/health':{'status':'healthy'},P+'/actions/pending':{'status':'success','pending_actions':[],'autonomy_mode':'SAFE'},
            P+'/actions/history':{'status':'success','history':[]},P+'/settings/autonomy':{'status':'success','autonomy_mode':'SAFE'},
            P+'/sentinel/alerts':{'status':'success','alerts':[],'engine_status':{'running':False}},
            P+'/cloud/status':{'status':'success','gpu_sovereignty':{'cloud_burst_enabled':False,'current_daily_spend_usd':0},'queue':[]},
            '/api/tags':{'models':[{'name':'installed-fixture'}]},'/api/ps':{'models':[]}}
        def route(req):
            self.calls.append(req)
            if req.url.path==self.fail:return httpx.Response(503,json={'secret':'fixture-private-value'})
            if req.method=='GET':return httpx.Response(200,json=self.rows[req.url.path])
            payload=json.loads(req.content)
            if req.url.path.endswith('/settings/autonomy'):data={'status':'success','autonomy_mode':payload['mode']}
            elif req.url.path.endswith('/actions/halt'):data={'status':'HALTED','autonomy_mode':'SAFE','revoked_count':0}
            elif req.url.path.endswith('/chat'):data={'status':'success','response':'fixture reply','tool_calls':[]}
            else:data={'status':'success','resolution':{'status':'REJECTED'}}
            return httpx.Response(200,json=data)
        self.transport=httpx.MockTransport(route)
        self.headers=Mock(return_value={'X-Admin-Key':'fixture-private-value'})
        self.client=self.m.ExecutiveService(headers_provider=self.headers,transport=self.transport,
            port_probe=lambda port:port in {8080,11434},hardware_provider=lambda:{'system':{'cpu_pct':0},'gpu':{'detected':False}})

    def test_snapshot_reads_real_state_without_activation_or_credentials_on_peers(self):
        data=self.client.snapshot()
        self.assertTrue(data['sections']['pending']['ok'])
        self.assertEqual(data['sections']['pending']['data']['pending_actions'],[])
        self.assertFalse(data['ports'][8888]['listening'])
        self.assertTrue(data['ports'][8888]['onDemand'])
        self.assertEqual(data['sections']['loaded_models']['data']['models'],[])
        self.assertTrue(all(req.method=='GET' for req in self.calls))
        self.assertNotIn(P+'/matrix/status',[req.url.path for req in self.calls])
        for req in self.calls:
            self.assertEqual(req.url.host,'127.0.0.1')
            if req.url.port==11434:self.assertNotIn('X-Admin-Key',req.headers)
            else:self.assertEqual(req.headers.get('X-Admin-Key'),'fixture-private-value')

    def test_partial_failure_is_unknown_not_an_empty_successful_queue(self):
        self.fail=P+'/actions/pending';data=self.client.snapshot()
        self.assertFalse(data['sections']['pending']['ok'])
        self.assertNotIn('data',data['sections']['pending'])
        self.assertTrue(data['sections']['autonomy']['ok'])
        self.assertNotIn('fixture-private-value',json.dumps(data))

    def test_malformed_or_denied_reads_are_not_success(self):
        self.rows[P+'/actions/pending']={'pending_actions':'not a list'}
        self.assertFalse(self.client.snapshot()['sections']['pending']['ok'])
        self.rows[P+'/cloud/status']={'gpu_sovereignty':'invalid'}
        self.rows[P+'/sentinel/alerts']={'alerts':[],'engine_status':None}
        observed=self.client.snapshot()
        self.assertFalse(observed['sections']['cloud']['ok'])
        self.assertFalse(observed['sections']['sentinel']['ok'])
        denied=self.m.ExecutiveService(headers_provider=self.headers,transport=httpx.MockTransport(lambda r:httpx.Response(403,json={'detail':'fixture-private-value'})))
        with self.assertRaises(self.m.ExecutiveServiceError) as error:denied.get_autonomy()
        self.assertNotIn('fixture-private-value',str(error.exception))

    def test_actions_use_service_acknowledgement_and_validated_payloads(self):
        self.assertEqual(self.client.set_autonomy('SEMI_AUTO')['autonomy_mode'],'SEMI_AUTO')
        self.assertEqual(self.client.halt()['status'],'HALTED')
        self.assertEqual(self.client.chat('fixture prompt','fixture-model')['response'],'fixture reply')
        self.client.resolve('fixture-action','REJECT')
        self.assertEqual(json.loads(self.calls[-1].content),{'decision':'REJECT'})
        for bad in ['../other','a/b','',r'a\b']:
            with self.assertRaises(ValueError):self.client.resolve(bad,'APPROVE')
        with self.assertRaises(ValueError):self.client.set_autonomy('unvalidated')

    def test_timeout_writes_are_never_retried_or_reported_success(self):
        requests=[]
        def timeout(req):requests.append(req);raise httpx.ReadTimeout('fixture-private-value')
        client=self.m.ExecutiveService(headers_provider=self.headers,transport=httpx.MockTransport(timeout))
        with self.assertRaises(self.m.ExecutiveServiceError) as error:client.halt()
        self.assertEqual(len(requests),1)
        self.assertNotIn('fixture-private-value',str(error.exception))

    def test_redirects_and_unacknowledged_mutations_are_refused(self):
        requests=[]
        def redirect(req):requests.append(req);return httpx.Response(302,headers={'Location':'https://example.invalid/'})
        client=self.m.ExecutiveService(headers_provider=self.headers,transport=httpx.MockTransport(redirect))
        with self.assertRaises(self.m.ExecutiveServiceError):client.get_autonomy()
        self.assertEqual(len(requests),1)
        client=self.m.ExecutiveService(headers_provider=self.headers,transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'status':'success','autonomy_mode':'SAFE'})))
        with self.assertRaises(self.m.ExecutiveServiceError):client.set_autonomy('FULL_AUTO')


if __name__=='__main__':unittest.main()
