"""No long chapter is silently truncated into the admitted local model window."""
import asyncio
from contextlib import asynccontextmanager
import importlib
import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import httpx
from fastapi import HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))

class NovelizerContextBudgetTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('routers.novelizer_router');self.calls=[];self.context=8192
        outer=self
        class Dispatcher:
            @asynccontextmanager
            async def lease(self,*args,**kwargs):yield {'keep_alive_s':1,'num_ctx':outer.context,'num_batch':64,'gpu_admitted':True}
        class Client:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def post(self,url,**kwargs):
                outer.calls.append(kwargs['json'])
                return httpx.Response(200,json={'model':'fixture:small','response':'Actual mocked model prose.','done':True,'done_reason':'stop'})
        for item in (patch.object(self.module,'get_dispatcher',return_value=Dispatcher()),
            patch.object(self.module,'_provider_config',return_value={'providers':{'local':{'host':'http://127.0.0.1:11434','model':'fixture:small'}}}),
            patch.object(self.module.httpx,'AsyncClient',return_value=Client()),patch.dict(os.environ,{},clear=True)):
            item.start();self.addCleanup(item.stop)
    def query(self,source,output=2048):return asyncio.run(self.module._query_llm(source,'Source-bound directive.',max_output_tokens=output))
    def refused(self,source,output=2048):
        with self.assertRaises(HTTPException) as error:self.query(source,output)
        self.assertEqual(error.exception.status_code,413);self.assertFalse(self.calls)
    def test_oversized_ascii_is_refused_before_provider_post(self):self.refused('a'*10000)
    def test_multibyte_source_uses_bytes_not_character_count(self):self.refused('🐈'*1800)
    def test_output_tokens_leave_real_input_and_framing_room(self):self.refused('small source',8192)
    def test_reduced_admission_is_used_without_reducing_requested_output(self):
        self.context=2048;self.refused('small source',2048)
    def test_small_request_passes_exact_source_and_reports_effective_budget(self):
        result=self.query('Source 🐈',16)
        self.assertEqual(self.calls[0]['prompt'],'Source 🐈');self.assertEqual(self.calls[0]['options']['num_predict'],16)
        self.assertEqual(result['context_budget']['input_utf8_bytes'],len(('Source 🐈'+'Source-bound directive.').encode()))
        self.assertEqual(result['context_budget']['admitted_context'],8192)

if __name__=='__main__':unittest.main()
