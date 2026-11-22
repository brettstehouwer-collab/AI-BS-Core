from types import SimpleNamespace
import json,unittest,uuid
from native_studio.game_engine.content_jobs import ContentProposalJobs

class ContentJobTests(unittest.TestCase):
    def fixture(self):
        scope=SimpleNamespace(project='p',branch='main',world_id=str(uuid.uuid4()),host_epoch=str(uuid.uuid4()))
        client=SimpleNamespace(state='ready',generation=1,pending_count=0,head=SimpleNamespace(scope=scope,head_revision=4))
        row=SimpleNamespace(uuid=str(uuid.uuid4()),type_id='firstboot.Door',name='Main door',fields=(('x',-33.),))
        current=[str(uuid.uuid4()),'a'*64,(row,)]
        return client,current,row,ContentProposalJobs(client,lambda:tuple(current))
    def test_pinned_job_is_one_shot_and_does_not_use_mutated_prompt(self):
        client,current,row,jobs=self.fixture();job,prompt=jobs.begin()
        prompt['objects'][0]['fields']['x']=500
        source=json.dumps({'version':1,'label':'Move','edits':[{'entity_id':row.uuid,'field':'x','value':-32.5}]})
        packet=jobs.consume(job,source)
        self.assertTrue(packet.startswith(b'AIBP'))
        with self.assertRaises(ValueError):jobs.consume(job,source)
    def test_late_generation_head_or_definition_never_rebinds(self):
        for change in ('generation','revision','fingerprint','definition'):
            client,current,row,jobs=self.fixture();job,_=jobs.begin()
            if change=='generation':client.generation+=1
            elif change=='revision':client.head.head_revision+=1
            elif change=='fingerprint':current[1]='b'*64
            else:current[0]=str(uuid.uuid4())
            with self.assertRaises(ValueError):jobs.consume(job,'{}')
            self.assertEqual(jobs.pending_count,0)
    def test_pending_operation_waits_and_cancellation_and_limits(self):
        client,current,row,jobs=self.fixture();job,_=jobs.begin();client.pending_count=1
        with self.assertRaises(ValueError):jobs.consume(job,'{}')
        self.assertEqual(jobs.pending_count,1);client.pending_count=0;jobs.cancel_all()
        self.assertEqual(jobs.pending_count,0)
        for _ in range(8):jobs.begin()
        with self.assertRaises(ValueError):jobs.begin()
    def test_worker_cannot_read_widgets_or_mutate_job_state(self):
        from concurrent.futures import ThreadPoolExecutor
        client,current,row,jobs=self.fixture()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(jobs.begin)
            with self.assertRaises(RuntimeError):future.result()
        self.assertEqual(jobs.pending_count,0)

if __name__=='__main__':unittest.main()
