import asyncio,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from core.video_generation import generate_video
class ExecutionTests(unittest.IsolatedAsyncioTestCase):
 def info(self):return json.loads((Path((ROOT/'scratch/current_native_video_checkpoint.txt').read_text().strip())/'object_info_before.local.json').read_text())
 async def test_missing_capability_never_submits(self):
  calls=[]
  async def submit(g):calls.append(g);return 'fixture'
  r=await generate_video({'prompt':'test'},info={},submit=submit)
  self.assertEqual(r['status'],'error');self.assertEqual(calls,[])
 async def test_timeout_retains_exact_job_without_second_submission(self):
  calls=[]
  async def submit(g):calls.append(g);return 'fixture-prompt'
  async def wait(pid):raise TimeoutError()
  r=await generate_video({'prompt':'test'},info=self.info(),submit=submit,wait=wait)
  self.assertEqual(r['status'],'pending');self.assertEqual(r['prompt_id'],'fixture-prompt');self.assertEqual(len(calls),1);self.assertNotIn('filename',r)
 async def test_completed_mp4_retains_actual_dimensions(self):
  async def submit(g):return 'fixture-prompt'
  async def wait(pid):return {'status':{'completed':True,'status_str':'success'},'outputs':{'11':{'images':[{'filename':'clip.mp4','subfolder':'video','type':'output'}]}}}
  r=await generate_video({'prompt':'test','width':512,'height':384,'steps':6},info=self.info(),submit=submit,wait=wait)
  self.assertEqual(r['status'],'success');self.assertEqual(r['width'],512);self.assertEqual(r['num_frames'],49);self.assertIn('/api/comfy/media?',r['image_url'])
 async def test_failed_or_nonvideo_output_is_not_success(self):
  async def submit(g):return 'fixture-prompt'
  for status,filename in [({'completed':False,'status_str':'error'},'clip.mp4'),({'completed':True,'status_str':'success'},'still.png')]:
   async def wait(pid):return {'status':status,'outputs':{'11':{'images':[{'filename':filename,'subfolder':'','type':'output'}]}}}
   r=await generate_video({'prompt':'test'},info=self.info(),submit=submit,wait=wait);self.assertNotEqual(r['status'],'success')
if __name__=='__main__':unittest.main()
