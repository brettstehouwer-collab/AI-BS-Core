from pathlib import Path
import json, os, sys, unittest
cp = Path(Path('C:/AI-BS/workspace/proposal_v46_checkpoint.txt').read_text(encoding='utf-8'))
label = sys.argv[1]
os.environ['AIBS_SNAPSHOT_TEST_ROOT'] = str(cp/('fixtures_'+label))
sys.path[:0] = ['C:/AI-BS/backend', 'C:/AI-BS/backend/tests']
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in
    (sys.argv[2:] or ['test_preparation_proposals.ProposalTests']))
with (cp/(label+'.txt')).open('x', encoding='utf-8') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
report = {'label':label,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful()}
(cp/(label+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
raise SystemExit(not result.wasSuccessful())
