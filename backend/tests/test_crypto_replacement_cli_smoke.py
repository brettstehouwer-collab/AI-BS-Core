"""Ten black-box local CLI guards; NOT actual authentication or live proof.

Every subprocess receives an environment with all REPLACEMENT* names removed.
No credentials, account requests, test transports or private roots are created.
"""
from pathlib import Path
from hashlib import sha256
import json
import os
import subprocess
import unittest
from uuid import uuid4

ROOT=Path('C:/AI-BS')
PROGRAM=ROOT/'scripts/verify_crypto_replacement.py'
PYTHON=ROOT/'runtime/recovery-20261110/Scripts/python.exe'
SHA=sha256(b'local-configuration-guard-only-not-an-opening-receipt').hexdigest()


class ReplacementCliSmoke(unittest.TestCase):
    def setUp(self):
        self.assertTrue(PROGRAM.is_file(),'Replacement CLI not implemented')
        self.environment_before=dict(os.environ)
        self.child_env={key:value for key,value in os.environ.items() if not key.upper().startswith('REPLACEMENT')}
        self.child_env['PYTHONDONTWRITEBYTECODE']='1'
        self.assertFalse(any(key.upper().startswith('REPLACEMENT') for key in self.child_env))

    def run_cli(self,*args):
        result=subprocess.run([str(PYTHON),str(PROGRAM),*args],cwd=ROOT,env=self.child_env,
            shell=False,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertNotIn('Traceback (most recent call last)',result.stdout+result.stderr)
        self.assertEqual(dict(os.environ),self.environment_before)
        return result

    def missing_configuration(self,*args):
        result=self.run_cli(*args);self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        answer=json.loads(result.stdout)
        self.assertEqual(answer['status'],'MISSING_REPLACEMENT_CONFIGURATION')
        self.assertIs(answer['credential_verified'],False)
        for key in ('account_identity_verified','native_order_accepted','live_dispatch_enabled','ready_for_live'):
            self.assertIs(answer[key],False)
        self.assertEqual(answer['orders_sent'],0)
        return answer

    def test_01_check_config_missing_is_not_verification(self):
        self.missing_configuration('--check-config')

    def test_02_probe_requires_configuration_before_any_read(self):
        self.missing_configuration('--probe-only','--local-trial-uuid',str(uuid4()))

    def test_03_initialization_requires_configuration_before_any_creation(self):
        self.missing_configuration('--initialize-held','--local-trial-uuid',str(uuid4()),
            '--seed-usdt','2','--max-entry-usdt','10','--daily-loss-usdt','1')

    def test_04_existing_verification_requires_configuration(self):
        self.missing_configuration('--verify-existing','--expected-snapshot-sha256',SHA)

    def test_05_mode_is_required_and_exclusive(self):
        for args in ((),('--probe-only','--check-config'),('--initialize-held','--verify-existing')):
            with self.subTest(args=args):self.assertEqual(self.run_cli(*args).returncode,2)

    def test_06_probe_and_initialization_require_canonical_local_uuid(self):
        for args in (('--probe-only',),('--probe-only','--local-trial-uuid','not-a-uuid'),
                ('--initialize-held','--seed-usdt','2','--max-entry-usdt','10','--daily-loss-usdt','1')):
            with self.subTest(args=args):self.assertEqual(self.run_cli(*args).returncode,2)

    def test_07_initialization_requires_all_explicit_budget_fields(self):
        for flags in ((),('--seed-usdt','2'),('--seed-usdt','2','--max-entry-usdt','10')):
            with self.subTest(flags=flags):
                self.assertEqual(self.run_cli('--initialize-held','--local-trial-uuid',str(uuid4()),*flags).returncode,2)

    def test_08_existing_verification_requires_nonplaceholder_snapshot_hash(self):
        for flags in ((),('--expected-snapshot-sha256','bad'),('--expected-snapshot-sha256','a'*64),
                ('--expected-snapshot-sha256','A'*64)):
            with self.subTest(flags=flags):self.assertEqual(self.run_cli('--verify-existing',*flags).returncode,2)

    def test_09_secret_flags_are_not_cli_inputs(self):
        help_result=self.run_cli('--help');self.assertEqual(help_result.returncode,0)
        self.assertNotIn('--api-key',help_result.stdout);self.assertNotIn('--secret',help_result.stdout)
        for flag in ('--api-key','--secret'):
            with self.subTest(flag=flag):self.assertEqual(self.run_cli('--check-config',flag,'SYNTHETIC_NOT_A_CREDENTIAL').returncode,2)

    def test_10_unknown_flags_refused_and_child_environment_does_not_mutate_parent(self):
        self.assertEqual(self.run_cli('--check-config','--send-order').returncode,2)
        self.assertEqual(self.run_cli('--check-config','--history').returncode,2)
        self.assertEqual(dict(os.environ),self.environment_before)


if __name__=='__main__':unittest.main()

