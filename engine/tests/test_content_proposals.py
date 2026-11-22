from pathlib import Path
import json,subprocess,tempfile,unittest
from native_studio.game_engine.content_proposals import ProposalContext,encode_proposal

import os
from dataclasses import replace
EXE=Path(os.environ.get('AIBS_CONTENT_PROPOSAL_EXE',str(Path(__file__).resolve().parents[1]/'out/windows-msvc/Debug/aibs_content_authoring_tests.exe')))
class ContentProposalTests(unittest.TestCase):
    def test_structured_proposal_uses_real_native_authoring_and_exact_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=subprocess.run([str(EXE),'--proposal-context',str(root)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            context=ProposalContext.from_dict(json.loads((root/'context.json').read_text()))
            target=context.fields[0][0]
            proposal=json.dumps({'version':1,'label':'Move the main doorway','edits':[{'entity_id':target,'field':'x','value':-32.5}]})
            request=root/'proposal.bin';request.write_bytes(encode_proposal(proposal,context,'ai-job-one'))
            result=subprocess.run([str(EXE),'--proposal-apply',str(root),str(request)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode());self.assertIn(b'applied 1',result.stdout)
            saved=(root/'chapter.aiba').read_bytes()
            result=subprocess.run([str(EXE),'--proposal-apply',str(root),str(request)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode());self.assertIn(b'duplicate 1',result.stdout)
            self.assertEqual(saved,(root/'chapter.aiba').read_bytes())
            request.write_bytes(encode_proposal(proposal,context,'stale-ai-job'))
            result=subprocess.run([str(EXE),'--proposal-apply',str(root),str(request)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(saved,(root/'chapter.aiba').read_bytes())
            refresh=subprocess.run([str(EXE),'--proposal-context',str(root)],capture_output=True)
            self.assertEqual(refresh.returncode,0,refresh.stderr.decode())
            current=ProposalContext.from_dict(json.loads((root/'context.json').read_text()))
            wrong_branch=replace(current,branch='different-branch')
            changed=json.dumps({'version':1,'label':'Wrong branch','edits':[{'entity_id':target,'field':'x','value':-32.6}]})
            request.write_bytes(encode_proposal(changed,wrong_branch,'wrong-branch-job'))
            result=subprocess.run([str(EXE),'--proposal-apply',str(root),str(request)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertIn(b'scope',result.stderr);self.assertEqual(saved,(root/'chapter.aiba').read_bytes())
            blocked=json.dumps({'version':1,'label':'Invalid aperture','edits':[{'entity_id':target,'field':'x','value':100.}]})
            request.write_bytes(encode_proposal(blocked,current,'blocked-ai-job'))
            result=subprocess.run([str(EXE),'--proposal-apply',str(root),str(request)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(saved,(root/'chapter.aiba').read_bytes())
            for bad in ('{"version":1,"version":1}',json.dumps({'version':1,'label':'No code','edits':[],'execute':'bad'}),json.dumps({'version':1,'label':'No state writes','edits':[{'entity_id':target,'field':'unlocked','value':True}]})):
                with self.assertRaises(ValueError):encode_proposal(bad,context,'invalid-job')

if __name__=='__main__':unittest.main()
