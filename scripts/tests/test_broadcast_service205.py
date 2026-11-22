"""Offline service lifecycle fixtures; never starts a server or encoder."""
from __future__ import annotations

import ast
from contextlib import nullcontext
import importlib
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[2]


def daemon_class():
    tree=ast.parse((ROOT/'backend/aibs_broadcast_daemon.py').read_text(encoding='utf-8-sig'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BroadcastDaemon')
    env={'List':List,'Dict':Dict,'Any':Any,'Optional':Optional,'WebSocket':object,
         'threading':threading,'logging':logging,'os':os,'json':json,
         'detect_optimal_encoder':Mock(side_effect=AssertionError('encoder work forbidden'))}
    exec(compile(ast.Module(body=[cls],type_ignores=[]),str(ROOT/'backend/aibs_broadcast_daemon.py'),'exec'),env)
    return env['BroadcastDaemon'],env


class BroadcastDaemonColdStartTests(unittest.TestCase):
    def test_archive_slug_trims_caption_whitespace_without_changing_window_identity(self):
        from scripts.tests.test_broadcast_daemon_integrity import load_daemon
        for title,expected in [('Fortnite  ','Fortnite'),('   ','General')]:
            with self.subTest(title=title):
                daemon,namespace,_,_=load_daemon()
                gui=SimpleNamespace(IsWindow=lambda h:True,IsWindowVisible=lambda h:True,
                                    IsIconic=lambda h:False,GetWindowText=Mock(return_value=title))
                namespace['win32gui']=gui
                namespace['win32process']=SimpleNamespace(GetWindowThreadProcessId=lambda h:(1,900))
                namespace['OBSOrchestrator']=Mock()
                self.assertTrue(daemon.start_stream([],game_name=title,
                                sources=[{'type':'window','hwnd':205,'pid':900,'title':title,'name':title}]))
                self.assertEqual(namespace['os'].makedirs.call_args.args[0],f'C:/AI-BS/recordings/{expected}')
                command=namespace['subprocess'].Popen.call_args.args[0]
                self.assertEqual(namespace['NativeWindowCapture'].call_args.args,(205,900,title))
                self.assertIn('rawvideo',command);self.assertIn('pipe:0',command)
                self.assertNotIn('gdigrab',command);self.assertNotIn('video=OBS Virtual Camera',command)
                namespace['OBSOrchestrator'].assert_not_called()
                self.assertNotIn(title+'/',command[-1])
                self.assertGreaterEqual(gui.GetWindowText.call_count,2)

    def test_ffmpeg_encoder_creation_explicitly_hides_its_console(self):
        from scripts.tests.test_broadcast_daemon_integrity import load_daemon
        daemon,namespace,_,_=load_daemon()
        process_api=namespace['subprocess']
        process_api.CREATE_NO_WINDOW=0x08000000
        self.assertTrue(daemon.start_stream([],sources=[{'type':'screen','enabled':True}]))
        kwargs=process_api.Popen.call_args.kwargs
        self.assertEqual(kwargs['creationflags'],process_api.CREATE_NO_WINDOW)
        self.assertEqual(kwargs['stdin'],process_api.PIPE)
        self.assertEqual(kwargs['stdout'],process_api.PIPE)
        self.assertEqual(kwargs['stderr'],process_api.STDOUT)

    def test_control_service_has_no_unused_virtual_camera_or_numpy_dependency(self):
        tree=ast.parse((ROOT/'backend/aibs_broadcast_daemon.py').read_text(encoding='utf-8-sig'))
        imported={name.name for node in tree.body if isinstance(node,ast.Import) for name in node.names}
        self.assertNotIn('pyvirtualcam',imported)
        self.assertNotIn('numpy',imported)

    def test_constructor_never_launches_encoder_probe(self):
        cls,env=daemon_class()
        with patch.object(threading,'Thread',side_effect=AssertionError('thread start forbidden')):
            instance=cls()
        self.assertFalse(instance.is_streaming)
        self.assertIsNone(instance.process)
        env['detect_optimal_encoder'].assert_not_called()

    def test_health_endpoint_is_typed_identity_without_dispatch(self):
        tree=ast.parse((ROOT/'backend/aibs_broadcast_daemon.py').read_text(encoding='utf-8-sig'))
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='broadcast_service_health')
        node.decorator_list=[]
        env={'os':os,'daemon':SimpleNamespace(process=None,is_streaming=False,encoder_config=None)}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'health_fixture','exec'),env)
        result=env[node.name]()
        self.assertEqual(result['service_id'],'ai-bs.broadcast-daemon')
        self.assertEqual(result['protocol_version'],1)
        self.assertEqual(result['pid'],os.getpid())
        self.assertFalse(result['process_running'])
        self.assertFalse(result['ingest_verified'])
        self.assertFalse(result['archive_verified'])


class NativeBroadcastServiceTests(unittest.TestCase):
    def setUp(self):
        self.service=importlib.import_module('native_studio.broadcast_service')

    def test_fixed_command_has_one_local_worker_without_script_bridge(self):
        argv=self.service.service_command()
        self.assertEqual(argv[0],r'C:\AI-BS\pyppeteer_env\Scripts\python.exe')
        self.assertEqual(argv[1:4],['-B','-m','uvicorn'])
        self.assertIn('aibs_broadcast_daemon:app',argv)
        self.assertEqual(argv[argv.index('--host')+1],'127.0.0.1')
        self.assertEqual(argv[argv.index('--port')+1],'8005')
        self.assertEqual(argv[argv.index('--workers')+1],'1')
        self.assertNotIn('--reload',argv)

    def test_child_environment_excludes_credentials_and_holds_trading(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'fixture-only','KRAKEN_SECRET_KEY':'fixture-only','HOLD_DISPATCH':'false','DRY_RUN':'false'}):
            env=self.service.service_environment()
        self.assertNotIn('OPENAI_API_KEY',env)
        self.assertNotIn('KRAKEN_SECRET_KEY',env)
        self.assertEqual(env['HOLD_DISPATCH'],'true')
        self.assertEqual(env['DRY_RUN'],'true')
        self.assertEqual(env['AI_BS_BACKEND_MANAGE_DAEMONS'],'false')

    def test_ready_existing_service_never_starts_another_process(self):
        ready={'status':'ready','pid':17,'started':False}
        with patch.object(self.service,'probe_broadcast_service',return_value=ready), \
             patch.object(self.service,'_spawn_service',side_effect=AssertionError('duplicate process')):
            self.assertEqual(self.service.ensure_broadcast_service_online(),ready)

    def test_unrelated_listener_is_refused_before_spawn(self):
        conflict={'status':'error','code':'PORT_CONFLICT'}
        with patch.object(self.service,'probe_broadcast_service',return_value=conflict), \
             patch.object(self.service,'_spawn_service',side_effect=AssertionError('port collision')):
            self.assertEqual(self.service.ensure_broadcast_service_online()['code'],'PORT_CONFLICT')

    def test_spawn_waits_for_matching_health_pid_before_reporting_ready(self):
        ready={'status':'ready','pid':17,'started':False}
        process=SimpleNamespace(pid=17,poll=lambda:None)
        with patch.object(self.service,'probe_broadcast_service',side_effect=[{'status':'offline'}, {'status':'offline'},ready]), \
             patch.object(self.service,'_startup_lock',return_value=nullcontext()), \
             patch.object(self.service,'_paths_ready',return_value=True), \
             patch.object(self.service,'_spawn_service',return_value=process) as spawn:
            result=self.service.ensure_broadcast_service_online()
        self.assertEqual(result['status'],'ready')
        self.assertTrue(result['started'])
        self.assertEqual(result['pid'],17)
        spawn.assert_called_once_with()

    def test_missing_runtime_and_early_child_exit_are_not_success(self):
        with patch.object(self.service,'probe_broadcast_service',return_value={'status':'offline'}), \
             patch.object(self.service,'_startup_lock',return_value=nullcontext()), \
             patch.object(self.service,'_paths_ready',return_value=False), \
             patch.object(self.service,'_spawn_service',side_effect=AssertionError('missing runtime')):
            self.assertEqual(self.service.ensure_broadcast_service_online()['code'],'RUNTIME_UNAVAILABLE')
        with patch.object(self.service,'probe_broadcast_service',return_value={'status':'offline'}), \
             patch.object(self.service,'_startup_lock',return_value=nullcontext()), \
             patch.object(self.service,'_paths_ready',return_value=True), \
             patch.object(self.service,'_spawn_service',return_value=SimpleNamespace(pid=17,poll=lambda:1)):
            self.assertEqual(self.service.ensure_broadcast_service_online()['code'],'START_FAILED')

    def test_probe_rejects_wrong_health_identity_or_pid(self):
        owner={'status':'owned','pid':17}
        for health in ({'service_id':'other','protocol_version':1,'pid':17},
                       {'service_id':'ai-bs.broadcast-daemon','protocol_version':1,'pid':18}):
            with patch.object(self.service,'_listener_owner',return_value=owner), \
                 patch.object(self.service,'_read_health',return_value=health):
                self.assertEqual(self.service.probe_broadcast_service()['code'],'PORT_CONFLICT')

    def test_invalid_startup_timeout_never_submits_work(self):
        with patch.object(self.service,'probe_broadcast_service',side_effect=AssertionError('probe forbidden')):
            for timeout in (float('nan'),-1,100):
                self.assertEqual(self.service.ensure_broadcast_service_online(timeout_s=timeout)['code'],'INVALID_TIMEOUT')

    def test_listener_owner_requires_exact_local_command_and_pid(self):
        listener=SimpleNamespace(status=self.service.psutil.CONN_LISTEN,
                                 laddr=SimpleNamespace(ip='127.0.0.1',port=8005),pid=17)
        command=self.service.service_command()
        process=SimpleNamespace(cmdline=lambda:command,exe=lambda:str(self.service.PYTHON))
        with patch.object(self.service.psutil,'net_connections',return_value=[listener]), \
             patch.object(self.service.psutil,'Process',return_value=process):
            self.assertEqual(self.service._listener_owner(),{'status':'owned','pid':17})
            command.append('--reload')
            self.assertEqual(self.service._listener_owner()['code'],'PORT_CONFLICT')
            command.pop();listener.laddr.ip='0.0.0.0'
            self.assertEqual(self.service._listener_owner()['code'],'PORT_CONFLICT')

    def test_hidden_spawn_uses_fixed_arguments_and_sanitized_environment(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(self.service,'LOG_FILE',Path(folder)/'service.log'), \
             patch.object(self.service.subprocess,'Popen',return_value=SimpleNamespace(pid=17)) as spawn:
            self.assertEqual(self.service._spawn_service().pid,17)
        argv=spawn.call_args.args[0];kwargs=spawn.call_args.kwargs
        self.assertEqual(argv,self.service.service_command())
        self.assertEqual(kwargs['cwd'],str(self.service.BACKEND))
        self.assertEqual(kwargs['env']['HOLD_DISPATCH'],'true')
        self.assertFalse(kwargs.get('shell',False))
        self.assertTrue(kwargs['creationflags'] & self.service.subprocess.CREATE_NO_WINDOW)

    def test_startup_timeout_cleans_only_its_own_child(self):
        process=SimpleNamespace(pid=17,poll=lambda:None,terminate=Mock())
        with patch.object(self.service,'probe_broadcast_service',return_value={'status':'offline'}), \
             patch.object(self.service,'_startup_lock',return_value=nullcontext()), \
             patch.object(self.service,'_paths_ready',return_value=True), \
             patch.object(self.service,'_spawn_service',return_value=process), \
             patch.object(self.service.time,'monotonic',side_effect=[0,1,30]), \
             patch.object(self.service.time,'sleep'):
            result=self.service.ensure_broadcast_service_online()
        self.assertEqual(result['code'],'START_TIMEOUT')
        process.terminate.assert_called_once_with()

    def test_windows_venv_redirector_requires_declared_base_and_exact_parent_command(self):
        fields=dict(line.split(' = ',1) for line in (ROOT/'pyppeteer_env/pyvenv.cfg').read_text().splitlines() if ' = ' in line)
        base=str(Path(fields['home'])/'python.exe')
        expected=self.service.service_command()
        child=SimpleNamespace(cmdline=lambda:[base,*expected[1:]],exe=lambda:base,ppid=lambda:16)
        parent=SimpleNamespace(cmdline=lambda:expected,exe=lambda:str(self.service.PYTHON))
        listener=SimpleNamespace(status=self.service.psutil.CONN_LISTEN,laddr=SimpleNamespace(ip='127.0.0.1',port=8005),pid=17)
        with patch.object(self.service.psutil,'net_connections',return_value=[listener]), \
             patch.object(self.service.psutil,'Process',side_effect=lambda pid:{17:child,16:parent}[pid]):
            result=self.service._listener_owner()
            self.assertEqual(result['status'],'owned')
            self.assertEqual(result['pid'],17)
            self.assertEqual(result['launcher_pid'],16)
            expected.append('--reload')
            self.assertEqual(self.service._listener_owner()['code'],'PORT_CONFLICT')

    def test_arbitrary_python_or_unlinked_base_interpreter_is_not_admitted(self):
        fields=dict(line.split(' = ',1) for line in (ROOT/'pyppeteer_env/pyvenv.cfg').read_text().splitlines() if ' = ' in line)
        base=str(Path(fields['home'])/'python.exe')
        expected=self.service.service_command()
        current=[base]
        child=SimpleNamespace(cmdline=lambda:[current[0],*expected[1:]],exe=lambda:current[0],ppid=lambda:16)
        parent=SimpleNamespace(cmdline=lambda:['unrelated.exe'],exe=lambda:'unrelated.exe')
        listener=SimpleNamespace(status=self.service.psutil.CONN_LISTEN,laddr=SimpleNamespace(ip='127.0.0.1',port=8005),pid=17)
        with patch.object(self.service.psutil,'net_connections',return_value=[listener]), \
             patch.object(self.service.psutil,'Process',side_effect=lambda pid:{17:child,16:parent}[pid]):
            self.assertEqual(self.service._listener_owner()['code'],'PORT_CONFLICT')
            current[0]=r'C:\OtherPython\python.exe'
            self.assertEqual(self.service._listener_owner()['code'],'PORT_CONFLICT')

    def test_spawn_accepts_verified_listener_child_of_its_venv_redirector(self):
        ready={'status':'ready','pid':17,'launcher_pid':16,'started':False}
        process=SimpleNamespace(pid=16,poll=lambda:None)
        with patch.object(self.service,'probe_broadcast_service',side_effect=[{'status':'offline'}, {'status':'offline'},ready]), \
             patch.object(self.service,'_startup_lock',return_value=nullcontext()), \
             patch.object(self.service,'_paths_ready',return_value=True), \
             patch.object(self.service,'_spawn_service',return_value=process):
            result=self.service.ensure_broadcast_service_online()
        self.assertEqual(result['status'],'ready')
        self.assertEqual(result['pid'],17)
        self.assertEqual(result['launcher_pid'],16)

    def test_failed_start_cleans_only_verified_base_child_then_launcher_with_wait(self):
        service=self.service;expected=service.service_command()
        fields=dict(line.split(' = ',1) for line in (ROOT/'pyppeteer_env/pyvenv.cfg').read_text().splitlines() if ' = ' in line)
        base=str(Path(fields['home'])/'python.exe')
        child=SimpleNamespace(pid=17,cmdline=lambda:[base,*expected[1:]],exe=lambda:base,ppid=lambda:16,
                              terminate=Mock(),wait=Mock(return_value=0),kill=Mock())
        unrelated=SimpleNamespace(pid=18,cmdline=lambda:['unrelated.exe'],exe=lambda:'unrelated.exe',ppid=lambda:16,
                                  terminate=Mock(),wait=Mock(return_value=0),kill=Mock())
        parent=SimpleNamespace(cmdline=lambda:expected,exe=lambda:str(service.PYTHON),children=lambda:[child,unrelated])
        process=SimpleNamespace(pid=16,poll=lambda:None,terminate=Mock(),wait=Mock(return_value=0),kill=Mock())
        with patch.object(service.psutil,'Process',return_value=parent):
            self.assertTrue(service._cleanup_owned_start(process))
        child.terminate.assert_called_once_with();child.wait.assert_called_once()
        unrelated.terminate.assert_not_called();unrelated.kill.assert_not_called()
        process.terminate.assert_called_once_with();process.wait.assert_called_once()

    def test_spawned_service_failure_reports_unconfirmed_cleanup_honestly(self):
        process=SimpleNamespace(pid=17,poll=lambda:None)
        with patch.object(self.service,'probe_broadcast_service',return_value={'status':'offline'}), \
             patch.object(self.service,'_startup_lock',return_value=nullcontext()), \
             patch.object(self.service,'_paths_ready',return_value=True), \
             patch.object(self.service,'_spawn_service',return_value=process), \
             patch.object(self.service,'_cleanup_owned_start',return_value=False) as cleanup, \
             patch.object(self.service.time,'monotonic',side_effect=[0,30]):
            result=self.service.ensure_broadcast_service_online()
        self.assertTrue(result['started'])
        self.assertFalse(result['cleanup_confirmed'])
        self.assertEqual(result['launcher_pid'],17)
        cleanup.assert_called_once_with(process)

    def test_exception_after_spawn_attempts_owned_cleanup(self):
        process=SimpleNamespace(pid=17,poll=lambda:None)
        with patch.object(self.service,'probe_broadcast_service',side_effect=[{'status':'offline'},{'status':'offline'},OSError('fixture health failure')]), \
             patch.object(self.service,'_startup_lock',return_value=nullcontext()), \
             patch.object(self.service,'_paths_ready',return_value=True), \
             patch.object(self.service,'_spawn_service',return_value=process), \
             patch.object(self.service,'_cleanup_owned_start',return_value=True) as cleanup:
            result=self.service.ensure_broadcast_service_online()
        self.assertEqual(result['code'],'START_UNAVAILABLE')
        self.assertTrue(result['cleanup_confirmed'])
        cleanup.assert_called_once_with(process)


if __name__=='__main__':unittest.main()
