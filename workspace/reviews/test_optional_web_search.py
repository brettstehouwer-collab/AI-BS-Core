import asyncio,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from core.optional_web_search import optional_web_context
class OptionalSearchTests(unittest.IsolatedAsyncioTestCase):
 async def test_disabled_never_calls_provider(self):
  def forbidden(query): raise AssertionError('search without opt-in')
  for flag in (False,None,'false',1):
   self.assertEqual(await optional_web_context('private draft',flag,search=forbidden),'')
 async def test_only_explicit_query_and_safe_cited_results(self):
  queries=[]
  def search(q):
   queries.append(q);return [{'title':'Official docs','href':'https://example.com/docs','body':'Evidence'}, {'href':'javascript:bad()','body':'unsafe'}]
  text=await optional_web_context('public query',True,search=search)
  self.assertEqual(queries,['public query']);self.assertIn('https://example.com/docs',text);self.assertNotIn('javascript:',text);self.assertIn('untrusted',text.lower())
 async def test_failure_is_truthful_and_does_not_leak_exception(self):
  def broken(q):raise RuntimeError('private-token-value')
  text=await optional_web_context('query',True,search=broken)
  self.assertIn('unavailable',text.lower());self.assertNotIn('private-token-value',text)
if __name__=='__main__':unittest.main()
