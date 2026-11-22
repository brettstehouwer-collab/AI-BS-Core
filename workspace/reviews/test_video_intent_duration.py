import ast,re,json,sys,unittest
from pathlib import Path
from typing import Dict,Any,Optional,Tuple
ROOT=Path(__file__).resolve().parents[2]
class DurationTests(unittest.TestCase):
 def detector(self):
  t=ast.parse((ROOT/'backend/core/hybrid_reasoning_engine.py').read_text(encoding='utf-8'));nodes=[n for n in t.body if getattr(n,'name','') in ['detect_tool_intent','clean_tool_prompt']];ns=dict(re=re,json=json,Dict=Dict,Any=Any,Optional=Optional,Tuple=Tuple);exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-intent>','exec'),ns);return ns['detect_tool_intent']
 def test_default_and_explicit_duration_are_truthful(self):
  detect=self.detector();self.assertEqual(detect('Create a video of a blue cup')[1]['duration_seconds'],3)
  self.assertEqual(detect('Create a 3 second video of a blue cup')[1]['duration_seconds'],3)
  self.assertEqual(detect('Create a 10 second video of a blue cup')[1]['duration_seconds'],10)
if __name__=='__main__':unittest.main()
