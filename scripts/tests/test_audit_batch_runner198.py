"""Inspect the fixed audit plan without executing application or provider actions."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[2]
RUNNER=ROOT/'scripts/Run-AIBSAuditBatch.ps1'

class AuditBatchPlanTests(unittest.TestCase):
    def plan(self):
        self.assertTrue(RUNNER.is_file(),'Reviewed batch runner is absent')
        result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(RUNNER),'-ListOnly'],capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        return json.loads(result.stdout.decode('utf-8-sig'))

    def test_plan_contains_only_reviewed_checks_and_explicit_argument_arrays(self):
        plan=self.plan()
        self.assertEqual({r['Name'] for r in plan['Jobs']},{'Python','Clients','TypeScript','Versions'})
        for row in plan['Jobs']:
            self.assertIsInstance(row['Arguments'],list)
            self.assertTrue(Path(row['Executable']).is_absolute())
            self.assertNotIn('Invoke-Expression',' '.join(row['Arguments']))
        self.assertFalse(plan['ExternalDispatch'])

    def test_plan_enforces_trading_outreach_and_payment_holds(self):
        holds=self.plan()['Holds']
        self.assertEqual(holds['DRY_RUN'],'true');self.assertEqual(holds['HOLD_DISPATCH'],'true')
        self.assertEqual(holds['AIBS_PAYMENT_MODE'],'disabled')
        self.assertEqual(holds['RECDEBUT_SENDING_ENABLED'],'false')
        self.assertEqual(holds['AI_BS_BACKEND_MANAGE_DAEMONS'],'false')

    def test_runner_rejects_unreviewed_check_names(self):
        self.assertTrue(RUNNER.is_file())
        result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(RUNNER),'-Check','unreviewed-script','-ListOnly'],capture_output=True,timeout=15)
        self.assertNotEqual(result.returncode,0)

if __name__=='__main__':unittest.main()
