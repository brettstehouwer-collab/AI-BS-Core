from pathlib import Path
import json,os,sys,unittest
root=Path(r'C:\AI-BS');cp=Path((root/'workspace/proposal_history_v48_checkpoint.txt').read_text(encoding='utf-8').strip())
label=sys.argv[1];os.environ['AIBS_SNAPSHOT_TEST_ROOT']=str(cp/('fixtures_'+label))
sys.path[:0]=[str(root/'backend'),str(root/'backend/tests')]
suite=unittest.defaultTestLoader.loadTestsFromName('test_proposal_history.ProposalHistoryTests')
with (cp/(label+'.txt')).open('x',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
report={'label':label,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful()}
with (cp/(label+'.json')).open('x',encoding='utf-8') as out:json.dump(report,out,indent=2)
print(json.dumps(report));raise SystemExit(not result.wasSuccessful())
