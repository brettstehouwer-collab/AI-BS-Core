from pathlib import Path
import json, os, sys, unittest
cp = Path(Path('C:/AI-BS/workspace/proposal_v46_checkpoint.txt').read_text(encoding='utf-8'))
sys.path[:0] = ['C:/AI-BS/backend', 'C:/AI-BS/backend/tests']
reports = []
for name in ['test_preparation_history.PreparationHistoryTests', 'test_planning_controls.PlanningControlTests']:
    label = name.split('.')[0]
    os.environ['AIBS_SNAPSHOT_TEST_ROOT'] = str(cp/('regression_fixtures_'+label))
    suite = unittest.defaultTestLoader.loadTestsFromName(name)
    with (cp/(label+'.txt')).open('x', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    reports.append({'suite':name,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                    'skipped':len(result.skipped),'passed':result.wasSuccessful()})
(cp/'regressions.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports))
raise SystemExit(not all(r['passed'] for r in reports))
