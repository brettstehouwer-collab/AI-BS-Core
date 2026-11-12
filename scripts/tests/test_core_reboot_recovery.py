"""Synthetic boot/status contracts; no real process, daemon or network activation."""
import ast
from datetime import datetime
import importlib
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def function(path,name,scope):
    tree=ast.parse((ROOT/path).read_text(encoding='utf-8'))
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-source-fixture>','exec'),scope)
    return scope[name]


class StatusAndDemandTests(unittest.TestCase):
    def test_read_only_oversight_reports_offline_daemons_without_starting_them(self):
        activate=Mock()
        supervisor=SimpleNamespace(get_supervisor_status=lambda:{'online_count':0,'total_services':2})
        scope={'time':time,'datetime':datetime,'MASTER_43_MODULES':[],'Dict':dict,'Any':object}
        inspect=function('backend/core/oversight_parent_engine.py','inspect_all_modules',scope)
        with patch.dict(sys.modules,{'core.daemon_manager':SimpleNamespace(daemon_supervisor=supervisor),'aibs_ecosystem_spawner':SimpleNamespace(activate_all_daemons=activate)}):
            result=inspect(object())
        activate.assert_not_called()
        self.assertEqual(result['active_daemons'],0)
        self.assertEqual(result['total_daemons'],2)

    def test_disabled_activation_does_not_enter_wmi_lock_or_watchdog_paths(self):
        forbidden=Mock(side_effect=AssertionError('Activation path entered'))
        scope={'os':os,'sys':sys,'Dict':dict,'Any':object,'DAEMON_SPECS':[{'port':8080,'name':'fixture core'},{'port':8188,'name':'fixture media'}],
               'is_port_open':lambda p:p==8080,'_trigger_wmi_breakaway_spawner':forbidden,'_acquire_spawner_lock':forbidden,
               '_release_spawner_lock':forbidden,'ensure_crypto_watchdog':forbidden}
        activate=function('backend/aibs_ecosystem_spawner.py','activate_all_daemons',scope)
        with patch.dict(os.environ,{'AI_BS_BACKEND_MANAGE_DAEMONS':'false'}):result=activate(False)
        forbidden.assert_not_called()
        self.assertEqual(result['spawned'],[])
        self.assertEqual(result['active_now'],[8080])
        self.assertEqual(result['pending'],[8188])
        self.assertTrue(result['activation_disabled'])

    def test_unreal_is_not_in_general_spawner_registry(self):
        tree=ast.parse((ROOT/'backend/aibs_ecosystem_spawner.py').read_text(encoding='utf-8'))
        assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DAEMON_SPECS' for t in n.targets))
        ports=[ast.literal_eval(v) for entry in assignment.value.elts for k,v in zip(entry.keys,entry.values) if isinstance(k,ast.Constant) and k.value=='port']
        self.assertNotIn(8888,ports)


class ControlledBootTests(unittest.TestCase):
    def setUp(self):self.m=importlib.import_module('scripts.core_boot')

    def test_private_core_environment_overrides_inherited_or_dotenv_activation(self):
        source={key:'true' for key in self.m.FLAGS};source.update(AI_BS_ADMIN_KEY='fixture-only',PATH='fixture-path')
        env=self.m.controlled_environment(source,private=True)
        self.assertTrue(all(env[key]=='false' for key in self.m.FLAGS))
        self.assertEqual(env['AI_BS_ADMIN_KEY'],'fixture-only')
        self.assertEqual(source[self.m.FLAGS[0]],'true')

    def test_other_services_do_not_inherit_local_authentication(self):
        source={'AI_BS_ADMIN_KEY':'fixture-only','CF_API_TOKEN':'fixture-only','PATH':'fixture-path','USERPROFILE':'fixture-user'}
        env=self.m.controlled_environment(source,private=False)
        self.assertNotIn('AI_BS_ADMIN_KEY',env)
        self.assertNotIn('CF_API_TOKEN',env)
        self.assertEqual(env['PATH'],'fixture-path')

    def test_planned_services_bind_loopback_and_exclude_destructive_legacy_boot(self):
        specs=self.m.service_specs(ROOT)
        self.assertEqual([s.port for s in specs],[8080,8000,11434,5173,20243])
        serialized=repr(specs)
        for forbidden in ['Shutdown_AI_BS','zombie_node_cleaner','AI_BS_Unreal_Signaling_Server','boot_matrix_headless','Launch_AI_BS.bat']:
            self.assertNotIn(forbidden,serialized)
        backend=specs[0]
        self.assertIn('127.0.0.1',backend.argv)
        self.assertIn('--workers',backend.argv)

    def test_existing_service_requires_exact_binding_executable_arguments_and_flags(self):
        spec=self.m.ServiceSpec('fixture',8080,(r'C:\Fixture\python.exe','-m','uvicorn'),ROOT,True)
        process=SimpleNamespace(pid=101,exe=lambda:spec.argv[0],cmdline=lambda:list(spec.argv),
            environ=lambda:{key:'false' for key in self.m.FLAGS},create_time=lambda:123.5)
        rows=[SimpleNamespace(laddr=SimpleNamespace(ip='127.0.0.1'))]
        self.assertTrue(self.m.validate_existing(spec,rows,process)['adopted'])
        for bad in [[],rows+rows,[SimpleNamespace(laddr=SimpleNamespace(ip='0.0.0.0'))]]:
            with self.assertRaises(RuntimeError):self.m.validate_existing(spec,bad,process)
        for name,value in [('exe',lambda:r'C:\Other\python.exe'),('cmdline',lambda:[spec.argv[0],'other.py']),('environ',lambda:{})]:
            original=getattr(process,name);setattr(process,name,value)
            with self.assertRaises(RuntimeError):self.m.validate_existing(spec,rows,process)
            setattr(process,name,original)


if __name__=='__main__':unittest.main()
