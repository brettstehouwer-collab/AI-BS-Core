"""Cold-import acceptance with a sentinel preventing server code execution."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]


class StartupImportBoundaryTests(unittest.TestCase):
    def test_app_import_never_attempts_server_engines_in_source_or_frozen_mode(self):
        for frozen in (False,True):
            with self.subTest(frozen=frozen):
                code=r'''
import importlib.abc,json,sys
from pathlib import Path
root=Path(sys.argv[1]); frozen=sys.argv[2]=='true'
sys.path.insert(0,str(root))
if frozen:
    sys.frozen=True
    sys._MEIPASS=str(root)
attempts=[]
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='backend' or fullname.startswith('backend.'):
            attempts.append(fullname)
            raise ModuleNotFoundError('Server import prevented by startup acceptance sentinel')
sys.meta_path.insert(0,Guard())
import native_studio.app
print(json.dumps({'serverImportAttempts':attempts,'mainWindowConstructed':False}))
'''
                result=subprocess.run([sys.executable,'-I','-c',code,str(ROOT),str(frozen).lower()],capture_output=True,text=True,encoding='utf-8',timeout=30)
                self.assertEqual(result.returncode,0,result.stderr[-1500:])
                observed=json.loads(result.stdout.splitlines()[-1])
                self.assertEqual(observed['serverImportAttempts'],[])


if __name__=='__main__':unittest.main()
