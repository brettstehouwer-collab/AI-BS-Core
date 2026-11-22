import copy
import importlib.util
from pathlib import Path
import unittest

MODULE=Path(r'C:\AI-BS\workspace\authorized_worker_readonly_launch.py')

class WorkerSourcePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('worker_probe',MODULE)
        cls.subject=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.subject)

    def valid(self):
        return {'pid':291912,'created':1792856848.810399,'sid':'S-1-5-21-2133766663-4066672948-2456486318-1005',
                'elevated':False,'integrity':8192,'exe':r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
                'argv':['powershell.exe','-NoProfile','-NoExit','-ExecutionPolicy','Bypass','-File',r'C:\AI-BS\isolated_workers\windows\control\Read-CurrentVMState.ps1']}

    def test_verified_standard_worker_allowed(self):
        self.subject.validate_source(self.valid())

    def test_other_user_denied(self):
        info=self.valid();info['sid']='S-1-5-18'
        with self.assertRaises(ValueError):self.subject.validate_source(info)

    def test_elevated_worker_denied(self):
        info=self.valid();info['elevated']=True
        with self.assertRaises(ValueError):self.subject.validate_source(info)

    def test_high_integrity_denied(self):
        info=self.valid();info['integrity']=12288
        with self.assertRaises(ValueError):self.subject.validate_source(info)

    def test_reused_pid_denied(self):
        info=self.valid();info['created']+=1
        with self.assertRaises(ValueError):self.subject.validate_source(info)

    def test_other_program_denied(self):
        info=self.valid();info['exe']=r'C:\Windows\System32\cmd.exe'
        with self.assertRaises(ValueError):self.subject.validate_source(info)

    def test_arbitrary_source_command_denied(self):
        info=self.valid();info['argv'][-1]=r'C:\AI-BS\scratch\other.ps1'
        with self.assertRaises(ValueError):self.subject.validate_source(info)

if __name__=='__main__':unittest.main(verbosity=2)
