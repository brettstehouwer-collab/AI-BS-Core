"""Retained synthetic maintenance fixtures; no real API/provider/deploy is used."""
from __future__ import annotations
import contextlib
import ast
import asyncio
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch, MagicMock
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from core import project_maintenance as pm

FIXTURES = []


def fixture_root():
    root = ROOT / 't' / ('mpt-' + uuid.uuid4().hex[:12]);root.mkdir(parents=True)
    FIXTURES.append(str(root))
    (root / 'backend').mkdir();(root / 'backend/example.py').write_text('answer = 42\n')
    (root / 'frontend/src').mkdir(parents=True);(root / 'frontend/src/main.jsx').write_text('export const value = 42;\n')
    (root / 'frontend/package.json').write_text('{}')
    (root / 'scripts').mkdir();(root / 'scripts/run_takeover_checks.py').write_text('print("fixture")')
    (root / 'scripts/release-version.cjs').write_text('console.log("fixture")')
    return root


def request_job(root, *, lane='all', mode='success', api=None, operation='build_update'):
    job_id = uuid.uuid4().hex;folder = pm._folder(root, job_id);folder.mkdir(parents=True);(folder / 'events').mkdir()
    record = {'job_id':job_id,'lane':lane,'operation':operation,'state':'queued','status':'queued',
              'server':api or {},'fixture_mode':mode,'created_at':pm.utc()}
    pm.write_json_record(folder/'request.json',record,exclusive=True)
    pm.write_json_record(folder/'state.json',record,exclusive=True)
    return job_id, folder


def old_dist(root):
    dist = root/'frontend/dist';(dist/'assets').mkdir(parents=True)
    (dist/'index.html').write_text('<script src="/assets/old-1234AbCd.js"></script>')
    (dist/'assets/old-1234AbCd.js').write_text('const old = true;')
    return pm._tree(dist)


def candidate(path):
    (path/'assets').mkdir(parents=True)
    (path/'index.html').write_text('<script src="/assets/new-5678EfGh.js"></script>')
    (path/'assets/new-5678EfGh.js').write_text('const newer = true;')


class FixtureRuntime(pm.Runtime):
    def __init__(self, mode='success'):
        self.mode=mode;self.restart_calls=0;self.check_calls=[];self.commands={}
    def resolve_server(self,root,request,folder):return request
    def check(self,label,argv,cwd,folder,environment,timeout=300):
        self.check_calls.append(label)
        self.commands[label]=list(map(str,argv))
        argv_fixture=[sys.executable,'-B','-c','print("bounded fixture check")']
        if self.mode=='check-fail' and label=='backend-checks':
            argv_fixture=[sys.executable,'-B','-c','import sys;print("retained failing fixture");sys.exit(7)']
        result=super().check(label,argv_fixture,cwd,folder,environment,timeout=30)
        if label=='frontend-build':candidate(Path(argv[-1]))
        if self.mode=='frontend-backend-drift' and label=='frontend-build':
            (Path(cwd).parent/'backend/example.py').write_text('answer = 99\n')
        if self.mode=='changed-source' and label=='backend-checks':
            (Path(cwd)/'backend/example.py').write_text('answer = 99\n')
        return result
    def backup(self,root,job_id,folder):
        (root/'.aibs_backups/project_maintenance'/job_id).mkdir(parents=True)
        return {'database_count':0,'scope':'synthetic adapter only'}
    def restart(self,root,request,folder):
        self.restart_calls+=1
        if self.mode=='restart-fail':raise ValueError('Synthetic new API readiness failure')
        if self.mode=='fixture-api':
            old=request['server'];process=pm.psutil.Process(old['pid'])
            pm.need(abs(process.create_time()-old['created'])<.001,'Fixture API PID changed')
            environment=process.environ();args=process.cmdline();process.terminate();process.wait(timeout=10)
            with (folder/'fixture-api.stdout.log').open('xb') as out, (folder/'fixture-api.stderr.log').open('xb') as err:
                replacement=subprocess.Popen(args,env=environment,stdout=out,stderr=err,stdin=subprocess.DEVNULL,
                                             creationflags=subprocess.CREATE_NO_WINDOW)
            pm.write_json_record(folder/'fixture-replacement.json',{'pid':replacement.pid,'created':pm.psutil.Process(replacement.pid).create_time()},exclusive=True)
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                try:
                    response=pm.httpx.get('http://127.0.0.1:'+str(old['fixture_port'])+'/health',trust_env=False,timeout=1)
                    if response.status_code==200 and response.json()['pid']==replacement.pid:
                        pm.need(response.json()['test_flag']=='preserve-this-flag','Fixture environment changed')
                        return {'api_ready':True,'old_pid':old['pid'],'new_pid':replacement.pid,'fixture_flag_preserved':True}
                except pm.httpx.RequestError:pass
                time.sleep(.05)
            raise ValueError('Fixture replacement did not become ready')
        return {'api_ready':True,'fixture_only':True}


class MaintenanceTests(unittest.TestCase):
    def test_fixed_targets_do_not_reinterpret_other_projects_or_custom_commands(self):
        root=fixture_root()
        self.assertEqual(pm.maintenance_target('AI-BS',root),'all')
        self.assertEqual(pm.maintenance_target(str(root/'frontend'),root),'frontend')
        self.assertIsNone(pm.maintenance_target('my-custom-app',root))
        self.assertIsNone(pm.maintenance_target('',root));self.assertIsNone(pm.maintenance_target('  ',root))
        with patch.object(pm,'submit') as submit:
            self.assertIsNone(pm.dispatch('frontend','npm run my-custom-build'))
            submit.assert_not_called()

    def test_unknown_status_does_not_create_a_job(self):
        root=fixture_root();identifier=uuid.uuid4().hex
        with self.assertRaises(ValueError):pm.get_job(identifier,root)
        self.assertFalse(pm._folder(root,identifier).exists())
        for bad in ('../bad','x'*32,'0'*31):
            with self.assertRaises(ValueError):pm.get_job(bad,root)

    def test_input_identity_includes_fixed_helpers_tests_and_release_authority(self):
        root=fixture_root();checks=root/'scripts/tests';checks.mkdir()
        test_file=checks/'retained_fixture.py';test_file.write_text('value = 1\n')
        native=root/'native_studio';native.mkdir();native_file=native/'fixture.py';native_file.write_text('value = 1\n')
        (root/'version.txt').write_text('1.2.3')
        before=pm._inputs(root,'frontend')
        for name in ('backend/example.py','scripts/run_takeover_checks.py','scripts/release-version.cjs','scripts/tests/retained_fixture.py','native_studio/fixture.py','version.txt'):
            self.assertIn(name,before)
        test_file.write_text('value = 2\n')
        self.assertNotEqual(pm._inputs(root,'frontend'),before)

    def test_success_retains_source_previous_dist_and_old_tab_assets(self):
        root=fixture_root();previous=old_dist(root);job,folder=request_job(root)
        runtime=FixtureRuntime();result=pm.run_job(job,root=root,runtime=runtime)
        self.assertEqual(result['state'],'succeeded');self.assertTrue(result['api_ready'])
        self.assertEqual(runtime.restart_calls,1)
        self.assertIn('frontend-checks',runtime.check_calls)
        self.assertLess(runtime.check_calls.index('frontend-checks'),runtime.check_calls.index('frontend-build'))
        self.assertEqual(runtime.commands['frontend-checks'][1:3],['--experimental-vm-modules','--test'])
        self.assertEqual({Path(p).name for p in runtime.commands['frontend-checks'][3:]},set(pm.FRONTEND_CHECKS))
        self.assertEqual(pm._tree(root/'.aibs_backups/project_maintenance'/job/'dist-before'),previous)
        self.assertTrue((root/'frontend/dist/assets/old-1234AbCd.js').is_file())
        self.assertTrue((root/'frontend/dist/assets/new-5678EfGh.js').is_file())
        self.assertEqual((folder/'source-before/backend/example.py').read_text(),'answer = 42\n')
        self.assertEqual((root/'backend/example.py').read_text(),'answer = 42\n')
        self.assertEqual(pm.get_job(job,root)['state'],'succeeded')

    def test_failed_check_retains_old_release_and_does_not_restart(self):
        root=fixture_root();previous=old_dist(root);job,folder=request_job(root,mode='check-fail')
        runtime=FixtureRuntime('check-fail');result=pm.run_job(job,root=root,runtime=runtime)
        self.assertEqual(result['state'],'failed');self.assertEqual(runtime.restart_calls,0)
        self.assertEqual(pm._tree(root/'frontend/dist'),previous)
        self.assertIn('retained failing fixture',(folder/'backend-checks.stdout.local.log').read_text())

    def test_changed_source_holds_built_candidate_without_apply(self):
        root=fixture_root();previous=old_dist(root);job,folder=request_job(root,mode='changed-source')
        runtime=FixtureRuntime('changed-source');result=pm.run_job(job,root=root,runtime=runtime)
        self.assertEqual(result['state'],'failed');self.assertEqual(runtime.restart_calls,0)
        self.assertEqual(pm._tree(root/'frontend/dist'),previous)
        self.assertEqual((folder/'source-before/backend/example.py').read_text(),'answer = 42\n')

    def test_frontend_lane_backend_drift_refuses_api_restart(self):
        root=fixture_root();previous=old_dist(root);job,folder=request_job(root,lane='frontend',mode='frontend-backend-drift')
        runtime=FixtureRuntime('frontend-backend-drift');result=pm.run_job(job,root=root,runtime=runtime)
        self.assertEqual(result['state'],'failed');self.assertEqual(runtime.restart_calls,0)
        self.assertIn('backend-checks',runtime.check_calls)
        self.assertEqual(pm._tree(root/'frontend/dist'),previous)
        self.assertEqual((folder/'source-before/backend/example.py').read_text(),'answer = 42\n')

    def test_restart_only_runs_backend_checks_without_frontend_build(self):
        root=fixture_root();previous=old_dist(root);job,folder=request_job(root,lane='frontend',operation='restart')
        runtime=FixtureRuntime();result=pm.run_job(job,root=root,runtime=runtime)
        self.assertEqual(result['state'],'succeeded');self.assertEqual(runtime.check_calls,['backend-checks'])
        self.assertTrue((folder/'backend-syntax.json').is_file());self.assertEqual(runtime.restart_calls,1)
        self.assertEqual(pm._tree(root/'frontend/dist'),previous)

    def test_invalid_backend_restart_keeps_actual_fixture_api_healthy(self):
        root=fixture_root();previous=old_dist(root);(root/'backend/example.py').write_text('def broken(:\n')
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        job,folder=request_job(root,lane='frontend',mode='fixture-api',operation='restart')
        old=None;outputs=[]
        try:
            out=(folder/'old-fixture-api.stdout.log').open('xb');err=(folder/'old-fixture-api.stderr.log').open('xb');outputs=[out,err]
            args=[sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--fixture-api',str(port),str(root),job]
            environment=os.environ.copy();environment['MAINTENANCE_TEST_FLAG']='preserve-this-flag'
            old=subprocess.Popen(args,env=environment,stdout=out,stderr=err,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
            request=pm._read(folder/'request.json');request['server']={'pid':old.pid,'created':pm.psutil.Process(old.pid).create_time(),'fixture_port':port}
            pm.write_json_record(folder/'request.json',request)
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                try:
                    if pm.httpx.get(f'http://127.0.0.1:{port}/health',timeout=1,trust_env=False).status_code==200:break
                except pm.httpx.RequestError:pass
                time.sleep(.05)
            else:self.fail('Fixture API failed to start')
            self.assertEqual(pm.httpx.post(f'http://127.0.0.1:{port}/start',timeout=5,trust_env=False).status_code,202)
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                result=pm.get_job(job,root)
                if result['state'] in pm.TERMINAL:break
                time.sleep(.05)
            self.assertEqual(result['state'],'failed',result);self.assertEqual(result['error_type'],'SyntaxError')
            self.assertEqual(pm.httpx.get(f'http://127.0.0.1:{port}/health',timeout=2,trust_env=False).json()['pid'],old.pid)
            self.assertIsNone(old.poll());self.assertFalse((folder/'fixture-replacement.json').exists())
            self.assertEqual(pm._tree(root/'frontend/dist'),previous)
        finally:
            if old and old.poll() is None:old.terminate();old.wait(timeout=10)
            replacement=folder/'fixture-replacement.json'
            if replacement.is_file():
                data=pm._read(replacement)
                with contextlib.suppress(pm.psutil.Error):
                    process=pm.psutil.Process(data['pid'])
                    if abs(process.create_time()-data['created'])<.001:process.terminate();process.wait(timeout=10)
            for output in outputs:output.close()

    def test_restart_failure_restores_frontend_without_false_backend_health(self):
        root=fixture_root();previous=old_dist(root);job,folder=request_job(root,mode='restart-fail')
        result=pm.run_job(job,root=root,runtime=FixtureRuntime('restart-fail'))
        self.assertEqual(result['state'],'failed');self.assertFalse(result['api_ready'])
        self.assertEqual(result['frontend_recovery'],'previous-dist-restored')
        self.assertEqual(pm._tree(root/'frontend/dist'),previous)
        self.assertTrue((folder/'failed-dist/index.html').is_file())
        self.assertIn('No exact rollback',result['backend_recovery'])

    def test_failed_directory_promotion_restores_old_directory(self):
        root=fixture_root();previous=old_dist(root);staged=root/'t/staged';candidate(staged)
        real=pm.os.replace
        def replace(source,destination):
            if Path(source)==staged:raise OSError('synthetic promotion failure')
            return real(source,destination)
        with patch.object(pm.os,'replace',side_effect=replace):
            with self.assertRaises(OSError):pm._apply_web(root,staged,root/'.aibs_backups/dist-before')
        self.assertEqual(pm._tree(root/'frontend/dist'),previous)
        self.assertTrue((staged/'index.html').is_file())

    def test_asset_hash_collision_keeps_active_dist(self):
        root=fixture_root();previous=old_dist(root);staged=root/'t/staged';candidate(staged)
        (staged/'assets/old-1234AbCd.js').write_text('unexpected conflicting bytes')
        with self.assertRaises(ValueError):pm._apply_web(root,staged,root/'.aibs_backups/dist-before')
        self.assertEqual(pm._tree(root/'frontend/dist'),previous)

    def test_missing_frontend_reference_is_not_qualified(self):
        root=fixture_root();staged=root/'t/staged';staged.mkdir(parents=True)
        (staged/'index.html').write_text('<script src="/assets/missing.js"></script>')
        with self.assertRaises(ValueError):pm._validate_web(staged)

    def test_completed_job_is_not_replayed(self):
        root=fixture_root();job,folder=request_job(root,lane='backend');runtime=FixtureRuntime()
        first=pm.run_job(job,root=root,runtime=runtime)
        second=pm.run_job(job,root=root,runtime=runtime)
        self.assertEqual(first,second);self.assertEqual(runtime.restart_calls,1)

    def test_unacknowledged_worker_never_builds_or_restarts(self):
        root=fixture_root();job,folder=request_job(root);runtime=FixtureRuntime()
        result=pm.run_dispatched_job(job,root=root,runtime=runtime,wait_seconds=0)
        self.assertEqual(result['state'],'interrupted');self.assertEqual(runtime.check_calls,[]);self.assertEqual(runtime.restart_calls,0)

    def test_queue_rebinds_only_to_a_successful_owned_restart_receipt(self):
        root=fixture_root();old_job,old_folder=request_job(root)
        record=pm._read(old_folder/'state.json');record['state']='succeeded';pm.write_json_record(old_folder/'state.json',record)
        job,folder=request_job(root);identity={'pid':456,'created':200,'argv':['fixture'],'cwd':'fixture'}
        pm.write_json_record(folder.parent/'current-api.json',{'job_id':old_job,'identity':identity})
        request={'server':{'pid':123,'created':100}}
        with patch.object(pm,'_server_identity',side_effect=lambda pid:identity if pid==456 else {'pid':999}):
            rebound=pm.Runtime().resolve_server(root,request,folder)
            self.assertEqual(rebound['server'],identity)
            record['state']='failed';pm.write_json_record(old_folder/'state.json',record)
            with self.assertRaises(ValueError):pm.Runtime().resolve_server(root,request,folder)

    def test_dead_worker_gets_interrupted_receipt_and_keeps_partial_evidence(self):
        root=fixture_root();job,folder=request_job(root)
        record=pm._read(folder/'state.json');record['worker']={'pid':os.getpid(),'created':0}
        pm.write_json_record(folder/'state.json',record)
        (folder/'partial.log').write_text('incomplete evidence')
        result=pm.get_job(job,root)
        self.assertEqual(result['state'],'interrupted');self.assertIn('No automatic replay',result['message'])
        self.assertEqual((folder/'partial.log').read_text(),'incomplete evidence')

    def test_status_can_read_atomic_progress_while_worker_journals(self):
        root=fixture_root();job,folder=request_job(root)
        record=pm._read(folder/'state.json');record['worker']={'pid':os.getpid(),'created':pm.psutil.Process(os.getpid()).create_time()}
        pm.write_json_record(folder/'state.json',record)
        with pm.record_lock(folder/'receipt.lock'):
            self.assertEqual(pm.get_job(job,root)['state'],'queued')

    def test_submission_identifier_is_idempotent(self):
        root=fixture_root();pid=os.getpid();identity={'pid':pid,'created':pm.psutil.Process(pid).create_time(),
            'argv':[sys.executable,'-m','uvicorn','AI_BS_Backend:app'],'cwd':str(root/'backend')}
        with patch.object(pm,'_server_identity',return_value=identity), patch.object(pm.subprocess,'Popen',return_value=MagicMock(pid=pid)) as launch:
            identifier=uuid.uuid4().hex
            first=pm.submit('all',job_id=identifier,root=root);second=pm.submit('all',job_id=identifier,root=root)
            self.assertEqual(first['job_id'],second['job_id']);self.assertEqual(launch.call_count,1)
            with self.assertRaises(ValueError):pm.submit('backend',job_id=identifier,root=root)

    def test_private_sqlite_snapshot_is_consistent_and_not_a_shared_content_dump(self):
        root=fixture_root();source=root/'backend/aibs_master.db'
        with pm.sqlite3.connect(source) as connection:
            connection.execute('CREATE TABLE fixture(value TEXT)');connection.execute('INSERT INTO fixture VALUES (?)',('synthetic',))
        vault=root/'backend/stehouwer_vault.db'
        with pm.sqlite3.connect(vault) as connection:
            connection.execute('CREATE TABLE fixture(value TEXT)');connection.execute('INSERT INTO fixture VALUES (?)',('synthetic-owned-vault',))
        job,folder=request_job(root);result=pm.Runtime().backup(root,job,folder)
        self.assertEqual(result['database_count'],2)
        snapshot=Path(result['private_recovery_root'])/'backend/aibs_master.db'
        with pm.sqlite3.connect(snapshot) as connection:self.assertEqual(connection.execute('SELECT value FROM fixture').fetchall(),[('synthetic',)])
        with pm.sqlite3.connect(Path(result['private_recovery_root'])/'backend/stehouwer_vault.db') as connection:
            self.assertEqual(connection.execute('SELECT value FROM fixture').fetchall(),[('synthetic-owned-vault',)])
        receipt=pm._read(folder/'private-recovery.json')
        self.assertFalse(receipt['contents_public']);self.assertNotIn('synthetic',json.dumps(receipt))

    def test_reused_or_unrelated_api_pid_is_never_terminated(self):
        root=fixture_root();job,folder=request_job(root)
        process=MagicMock();process.create_time.return_value=200
        with patch.object(pm.psutil,'Process',return_value=process):
            with self.assertRaises(ValueError):pm.Runtime().restart(root,{'server':{'pid':123,'created':100}},folder)
        process.terminate.assert_not_called()

    def test_canonical_api_identity_rejects_external_or_duplicate_binding(self):
        process=MagicMock();process.cwd.return_value=str(pm.ROOT/'backend')
        for args in (
            [sys.executable,'-m','uvicorn','AI_BS_Backend:app','--host','0.0.0.0','--port','8080'],
            [sys.executable,'-m','uvicorn','AI_BS_Backend:app','--host','127.0.0.1','--host','0.0.0.0','--port','8080'],
            [sys.executable,'-m','uvicorn','AI_BS_Backend:app','--host','127.0.0.1','--port','8080','--reload'],
        ):
            process.cmdline.return_value=args
            with patch.object(pm.psutil,'Process',return_value=process):
                with self.assertRaises(ValueError):pm._server_identity(123)
        process.terminate.assert_not_called()

    def test_actual_restart_adapter_preserves_env_and_requires_matching_ready_pid(self):
        root=fixture_root();job,folder=request_job(root)
        args=[sys.executable,'-m','uvicorn','AI_BS_Backend:app','--host','127.0.0.1','--port','8080']
        identity={'pid':123,'created':100,'argv':args,'cwd':str(root/'backend')}
        environment={'AI_BS_ADMIN_KEY':'synthetic-token-never-journal','AI_BS_BACKEND_MANAGE_DAEMONS':'false',
                     'AI_BS_BACKEND_BACKGROUND_ENABLED':'false','RECDEBUT_REPLY_FORWARDING_ENABLED':'true'}
        old=MagicMock();old.create_time.return_value=100;old.cmdline.return_value=args;old.cwd.return_value=identity['cwd'];old.environ.return_value=environment;old.children.return_value=[]
        new=MagicMock();new.create_time.return_value=200;new.cmdline.return_value=args;new.environ.return_value=environment
        spawned=MagicMock(pid=456);spawned.poll.return_value=None
        mail={'sending_enabled':False,'reply_forwarding':{'enabled':True,'status':'scanned'}}
        class Response:
            status_code=200
            def __init__(self,value):self.value=value
            def json(self):return self.value
        client=MagicMock();client.__enter__.return_value=client
        client.get.side_effect=lambda path:Response(mail if path.endswith('/email/live') else
            {'service':'AI-BS Central Cognitive Engine API','process_id':456,'local_maintenance_protocol':1})
        anonymous=MagicMock(status_code=401)
        with patch.object(pm,'_server_identity',return_value=identity),patch.object(pm.psutil,'Process',side_effect=lambda pid:old if pid==123 else new),\
             patch.object(pm.subprocess,'Popen',return_value=spawned) as launch,patch.object(pm.httpx,'Client',return_value=client),patch.object(pm.httpx,'get',return_value=anonymous):
            result=pm.Runtime().restart(root,{'server':identity},folder)
        self.assertTrue(result['api_ready']);self.assertTrue(result['activation_flags_preserved'])
        self.assertEqual(launch.call_args.kwargs['env'],environment);self.assertEqual(launch.call_args.args[0],args)
        old.terminate.assert_called_once();new.terminate.assert_not_called()
        self.assertFalse(any(b'synthetic-token-never-journal' in p.read_bytes() for p in folder.rglob('*') if p.is_file()))

    def test_real_worker_survives_its_fixture_api_parent_restart(self):
        root=fixture_root();old_dist(root)
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        job,folder=request_job(root,mode='fixture-api')
        environment=os.environ.copy();environment['MAINTENANCE_TEST_FLAG']='preserve-this-flag'
        outputs=[];old=None
        try:
            out=(folder/'old-fixture-api.stdout.log').open('xb');err=(folder/'old-fixture-api.stderr.log').open('xb');outputs=[out,err]
            args=[sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--fixture-api',str(port),str(root),job]
            old=subprocess.Popen(args,env=environment,stdout=out,stderr=err,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
            identity={'pid':old.pid,'created':pm.psutil.Process(old.pid).create_time(),'fixture_port':port}
            request=pm._read(folder/'request.json');request['server']=identity;pm.write_json_record(folder/'request.json',request)
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                try:
                    if pm.httpx.get(f'http://127.0.0.1:{port}/health',timeout=1,trust_env=False).status_code==200:break
                except pm.httpx.RequestError:pass
                time.sleep(.05)
            else:self.fail('Fixture API failed to start')
            # The API starts its own detached worker and then that worker kills
            # only this exact fixture parent, rebinds the random loopback port
            # and writes a terminal receipt after the original HTTP ACK.
            response=pm.httpx.post(f'http://127.0.0.1:{port}/start',timeout=5,trust_env=False)
            self.assertEqual(response.status_code,202)
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                result=pm.get_job(job,root)
                if result['state'] in pm.TERMINAL:break
                time.sleep(.1)
            self.assertEqual(result['state'],'succeeded',result)
            self.assertNotEqual(result['restart']['new_pid'],old.pid)
            self.assertTrue(result['restart']['fixture_flag_preserved'])
            self.assertTrue((folder/'frontend-activation.json').is_file())
            self.assertIsNotNone(old.poll())
        finally:
            if old and old.poll() is None:old.terminate();old.wait(timeout=10)
            replacement=folder/'fixture-replacement.json'
            if replacement.is_file():
                data=pm._read(replacement)
                with contextlib.suppress(pm.psutil.Error):
                    process=pm.psutil.Process(data['pid'])
                    if abs(process.create_time()-data['created'])<.001:process.terminate();process.wait(timeout=10)
            for output in outputs:output.close()

    def test_declared_tool_routes_default_build_and_restart_to_durable_jobs(self):
        from tools.tool_registry import ToolRegistry
        queued={'state':'queued','status':'queued','job_id':'1'*32}
        with patch.object(pm,'dispatch',return_value=queued) as dispatch:
            result=ToolRegistry.execute_tool('build_project',{'project_name_or_dir':'frontend','maintenance_action':'status','maintenance_job_id':'1'*32})
            self.assertEqual(result,queued);dispatch.assert_called_once()
        with patch.object(pm,'submit',return_value=queued) as submit:
            result=ToolRegistry.execute_tool('manage_daemon_state',{'port':8080,'action':'restart'})
            self.assertEqual(result,queued);submit.assert_called_once_with('backend','restart')

    def test_natural_build_formatter_preserves_queued_receipt_without_false_failure(self):
        from tools.tool_registry import ToolRegistry
        source=ROOT/'backend/core/hybrid_reasoning_engine.py'
        tree=ast.parse(source.read_text(encoding='utf-8-sig'))
        branch=next(node for node in ast.walk(tree) if isinstance(node,ast.If) and isinstance(node.test,ast.Compare)
                    and isinstance(node.test.left,ast.Name) and node.test.left.id=='t_name'
                    and any(isinstance(value,ast.Constant) and value.value=='build_project' for value in node.test.comparators))
        wrapper=ast.parse('async def fixture(t_args):\n    yield "placeholder"').body[0]
        wrapper.body=branch.body
        namespace={'asyncio':asyncio};module=ast.fix_missing_locations(ast.Module(body=[wrapper],type_ignores=[]))
        exec(compile(module,str(source),'exec'),namespace)
        async def collect():return ''.join([piece async for piece in namespace['fixture']({'project_name_or_dir':'frontend'})])
        with patch.object(ToolRegistry,'execute_tool',return_value={'job_id':'1'*32,'state':'queued','status':'queued'}):
            text=asyncio.run(collect())
        self.assertIn('Local update in progress',text);self.assertIn('1'*32,text)
        self.assertNotIn('Build Failed',text);self.assertNotIn('Exit Code',text)


def fixture_worker(root, job):
    folder=pm._folder(root,job);request=pm._read(folder/'request.json')
    time.sleep(.5)
    result=pm.run_dispatched_job(job,root=root,runtime=FixtureRuntime(request['fixture_mode']))
    return 0 if result['state']=='succeeded' else 1


def fixture_api(port,root,job):
    folder=pm._folder(root,job)
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            data=json.dumps({'pid':os.getpid(),'test_flag':os.environ.get('MAINTENANCE_TEST_FLAG')}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
        def do_POST(self):
            if self.path!='/start':self.send_error(404);return
            with (folder/'fixture-worker.stdout.log').open('xb') as out, (folder/'fixture-worker.stderr.log').open('xb') as err:
                worker=subprocess.Popen([sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--fixture-worker',str(root),job],
                    stdout=out,stderr=err,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
            record=pm._read(folder/'state.json');record['worker']={'pid':worker.pid,'created':pm.psutil.Process(worker.pid).create_time()}
            pm.write_json_record(folder/'state.json',record)
            pm.write_json_record(folder/'dispatch-ready.json',{'job_id':job},exclusive=True)
            self.send_response(202);self.end_headers();self.wfile.write(b'queued')
    http.server.HTTPServer(('127.0.0.1',int(port)),Handler).serve_forever()


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1] in {'--fixture-worker','--fixture-api'}:
        if sys.argv[1]=='--fixture-worker':raise SystemExit(fixture_worker(Path(sys.argv[2]),sys.argv[3]))
        fixture_api(sys.argv[2],Path(sys.argv[3]),sys.argv[4])
    else:
        unittest.main()
