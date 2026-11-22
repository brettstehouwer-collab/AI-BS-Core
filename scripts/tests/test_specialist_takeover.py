"""Synthetic scheduler checks; never seed or execute the production registry."""
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import ast
import asyncio
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from core.subagent_coordinator import BoundedSwarmCoordinator


class FakeDatabase:
    def __init__(self, root):
        self.db_path = root / 'synthetic.sqlite'
        self.rows = []
        self.spec = SimpleNamespace(agent_id='fixture', active=True,
            workspace_scope=str(root), completion_check_cmd=[sys.executable, '-c', 'print("fixture")'],
            engine_target=SimpleNamespace(value='shared_core'))

    def get_specialist(self, agent_id):
        return self.spec if agent_id == self.spec.agent_id else None

    def record_evidence(self, **row):
        self.rows.append(row)


def process_shared_gate(root, ready, start, results):
    database = FakeDatabase(Path(root))
    sentinel = Path(root) / 'synthetic-active-slot'
    def runner(*args, **kwargs):
        with sentinel.open('x') as output:
            output.write('synthetic active gate')
        try:
            time.sleep(.1)
            return {'returncode': 0, 'stdout': 'synthetic', 'stderr': ''}
        finally:
            sentinel.unlink()
    coordinator = BoundedSwarmCoordinator(database, process_runner=runner)
    ready.put('ready')
    if not start.wait(5):
        results.put({'verified_pass': False, 'status': 'fixture-start-timeout'})
        return
    job = coordinator.enqueue_job('fixture', 'cross-process synthetic gate')
    results.put(coordinator.execute_verified_check(job, database.spec, timeout_sec=5))


class SpecialistTakeoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = FakeDatabase(self.root)

    def coordinator(self, runner, **kwargs):
        return BoundedSwarmCoordinator(self.db, process_runner=runner, **kwargs)

    def run_job(self, coordinator, priority=1, timeout=2):
        job = coordinator.enqueue_job('fixture', 'synthetic check', priority=priority)
        return coordinator.execute_verified_check(job, self.db.spec, timeout_sec=timeout)

    def test_completed_jobs_release_queue_capacity(self):
        c = self.coordinator(lambda *a, **k: {'returncode': 0, 'stdout': 'fixture', 'stderr': ''}, max_queue_size=2)
        for _ in range(7):
            self.assertTrue(self.run_job(c)['verified_pass'])
            self.assertEqual(c.job_queue.qsize(), 0)

    def test_missing_check_never_executes_or_creates_workspace(self):
        c = self.coordinator(lambda *a, **k: self.fail('unconfigured command executed'))
        self.db.spec.completion_check_cmd = [sys.executable, str(self.root / 'missing.py')]
        self.db.spec.workspace_scope = str(self.root / 'missing-workspace')
        result = self.run_job(c)
        self.assertFalse(result['verified_pass'])
        self.assertEqual(result['status'], 'unconfigured_check')
        self.assertFalse(Path(self.db.spec.workspace_scope).exists())

    def test_running_cancel_reaches_runner_and_keeps_partial_output(self):
        started = threading.Event()
        def runner(*args, cancelled=None, **kwargs):
            started.set()
            until = time.monotonic() + 2
            while not cancelled() and time.monotonic() < until:
                time.sleep(.005)
            return {'returncode': -1, 'error': 'cancelled', 'stdout': 'partial fixture', 'stderr': ''}
        c = self.coordinator(runner)
        job = c.enqueue_job('fixture', 'cancel synthetic check')
        with ThreadPoolExecutor() as pool:
            future = pool.submit(c.execute_verified_check, job, self.db.spec, 2)
            self.assertTrue(started.wait(1))
            c.cancel_job(job)
            result = future.result(3)
        self.assertEqual(result['status'], 'cancelled')
        self.assertIn('partial fixture', self.db.rows[0]['stdout'])
        self.assertFalse(result['verified_pass'])

    def test_timeout_error_cannot_be_a_pass_even_with_zero_exit(self):
        c = self.coordinator(lambda *a, **k: {'returncode': 0, 'error': 'timeout', 'stdout': 'partial', 'stderr': ''})
        result = self.run_job(c)
        self.assertFalse(result['verified_pass'])
        self.assertEqual(result['status'], 'timeout')
        self.assertEqual(self.db.rows[0]['stdout'], 'partial')
        self.assertNotEqual(self.db.rows[0]['returncode'], 0)

    def test_invalid_limits_rejected_before_execution(self):
        c = self.coordinator(lambda *a, **k: self.fail('invalid request executed'))
        for priority in (0, 6):
            with self.assertRaises(ValueError):
                c.enqueue_job('fixture', 'invalid', priority=priority)
        job = c.enqueue_job('fixture', 'invalid timeout')
        with self.assertRaises(ValueError):
            c.execute_verified_check(job, self.db.spec, timeout_sec=1801)

    def test_ready_jobs_run_in_priority_order_behind_active_check(self):
        started = threading.Event()
        release = threading.Event()
        calls = []
        def runner(argv, *args, **kwargs):
            name = argv[-1]
            calls.append(name)
            if name == 'first':
                started.set()
                self.assertTrue(release.wait(2))
            return {'returncode': 0, 'stdout': name, 'stderr': ''}
        c = self.coordinator(runner)
        def execute(name, priority):
            job = c.enqueue_job('fixture', name, priority)
            return c.execute_verified_check(job, self.db.spec, 3, [sys.executable, '-c', name])
        with ThreadPoolExecutor(max_workers=3) as pool:
            a = pool.submit(execute, 'first', 1)
            self.assertTrue(started.wait(1))
            b = pool.submit(execute, 'low', 5)
            d = pool.submit(execute, 'high', 1)
            until = time.monotonic() + 1
            while len(c._ready) < 3 and time.monotonic() < until:
                time.sleep(.005)
            self.assertEqual(len(c._ready), 3)
            release.set()
            self.assertTrue(all(f.result(4)['verified_pass'] for f in (a,b,d)))
        self.assertEqual(calls, ['first', 'high', 'low'])

    def test_cancelled_unstarted_job_releases_capacity(self):
        c = self.coordinator(lambda *a, **k: {'returncode': 0}, max_queue_size=1)
        job = c.enqueue_job('fixture', 'never started')
        c.cancel_job(job)
        self.assertEqual(c.job_queue.qsize(), 0)
        self.assertTrue(self.run_job(c)['verified_pass'])
        result = c.execute_verified_check(job, self.db.spec)
        self.assertEqual(result['status'], 'cancelled')

    def test_deadline_includes_reservation_and_executor_wait(self):
        c = self.coordinator(lambda *a, **k: self.fail('expired reservation ran'))
        job = c.enqueue_job('fixture', 'expired')
        with c._condition:
            ticket, agent = c._pending[job]
            c._pending[job] = ((ticket[0], ticket[1] - 2, ticket[2]), agent)
        result = c.execute_verified_check(job, self.db.spec, timeout_sec=1)
        self.assertEqual(result['status'], 'timeout')

    def test_command_change_during_execution_invalidates_pass(self):
        script = self.root / 'fixture.py'
        script.write_text('print(1)')
        self.db.spec.completion_check_cmd = [sys.executable, str(script)]
        def runner(*args, **kwargs):
            script.write_text('print(2)')
            return {'returncode': 0, 'stdout': 'one', 'stderr': ''}
        result = self.run_job(self.coordinator(runner))
        self.assertFalse(result['verified_pass'])
        self.assertEqual(result['status'], 'source_changed')
        self.assertTrue(result['source_changed_during_execution'])

    def test_registry_connections_close_and_updates_keep_job_evidence(self):
        import sqlite3
        from core.subagent_coordinator import PersistentAgentDatabase, SpecialistContract, EngineTarget
        db = PersistentAgentDatabase(self.root / 'registry.sqlite')
        spec = SpecialistContract('fixture', 1, 'Fixture', 'Synthetic', 'Synthetic result',
                                  EngineTarget.SHARED, 'none', [], str(self.root), [sys.executable, '-V'])
        db.upsert_specialist(spec)
        db.record_evidence(job_id='retained', agent_id='fixture', engine_target='shared_core',
                           source_revision='fixture', command=spec.completion_check_cmd,
                           returncode=0, stdout='synthetic', stderr='', duration=.01)
        spec.name = 'Updated fixture'
        db.upsert_specialist(spec)
        db.upsert_many_specialists([spec])
        with db._connect() as connection:
            self.assertEqual(connection.execute('select count(*) from agent_job_evidence').fetchone()[0], 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute('select 1')

    def test_distinct_coordinators_share_the_host_gate_lock(self):
        active = 0
        maximum = 0
        guard = threading.Lock()
        def runner(*args, **kwargs):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            time.sleep(.08)
            with guard:
                active -= 1
            return {'returncode': 0, 'stdout': 'fixture', 'stderr': ''}
        a, b = self.coordinator(runner), self.coordinator(runner)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(self.run_job, c) for c in (a,b)]
            self.assertTrue(all(f.result(3)['verified_pass'] for f in results))
        self.assertEqual(maximum, 1)

    def test_separate_serving_processes_share_the_host_gate_lock(self):
        context = multiprocessing.get_context('spawn')
        ready, results, start = context.Queue(), context.Queue(), context.Event()
        processes = [context.Process(target=process_shared_gate,
                     args=(str(self.root), ready, start, results)) for _ in range(2)]
        try:
            for process in processes:
                process.start()
            for _ in processes:
                self.assertEqual(ready.get(timeout=10), 'ready')
            start.set()
            rows = [results.get(timeout=10) for _ in processes]
            for process in processes:
                process.join(5)
                self.assertFalse(process.is_alive())
                self.assertEqual(process.exitcode, 0)
            self.assertTrue(all(row['verified_pass'] for row in rows), rows)
            self.assertFalse((self.root / 'synthetic-active-slot').exists())
        finally:
            start.set()
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(3)
            for pipe in (ready, results):
                pipe.close()
                pipe.join_thread()

    @unittest.skipUnless(sys.platform == 'win32', 'Windows Job Object check')
    def test_actual_process_timeout_retains_output_and_stops_descendant(self):
        import psutil
        child_pid = self.root / 'child.pid'
        child_code = 'import time; time.sleep(30)'
        parent_code = ('import subprocess,sys,time; from pathlib import Path; '
            f'p=subprocess.Popen([sys.executable,"-c",{child_code!r}]); '
            f'Path({str(child_pid)!r}).write_text(str(p.pid)); '
            'print("retained-before-timeout",flush=True); time.sleep(30)')
        self.db.spec.completion_check_cmd = [sys.executable, '-c', parent_code]
        c = BoundedSwarmCoordinator(self.db)
        result = self.run_job(c, timeout=1)
        self.assertEqual(result['status'], 'timeout')
        self.assertIn('retained-before-timeout', result['stdout'])
        self.assertTrue(child_pid.exists())
        pid = int(child_pid.read_text())
        self.assertFalse(psutil.pid_exists(pid) and psutil.Process(pid).is_running())


class SpecialistEndpointTests(unittest.IsolatedAsyncioTestCase):
    def gate_namespace(self, database, coordinator):
        from fastapi import HTTPException, Request
        from pydantic import BaseModel, Field
        from typing import Optional
        import queue
        source = Path(__file__).resolve().parents[2] / 'backend/routers/agent_crew_router.py'
        names = {'SpecialistRunGateRequest', 'run_specialist_gate_endpoint',
                 '_GateCancellation', '_execute_specialist_gate_request'}
        selected = [n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body
                    if getattr(n, 'name', '') in names]
        for node in selected:
            if hasattr(node, 'decorator_list'):
                node.decorator_list = []
        namespace = dict(HTTPException=HTTPException, Request=Request, BaseModel=BaseModel,
            Field=Field, Optional=Optional, asyncio=asyncio, queue=queue, threading=threading,
            _get_specialist_db=database, _get_specialist_coordinator=lambda _: coordinator)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
        return namespace

    async def test_lookup_and_enqueue_keep_event_loop_responsive(self):
        spec = SimpleNamespace(agent_id='fixture', name='Fixture', metadata={})
        class FakeRequest:
            async def is_disconnected(self): return False
        for slow_step in ('initialize', 'lookup', 'enqueue'):
            with self.subTest(slow_step=slow_step):
                def database():
                    if slow_step == 'initialize':
                        time.sleep(.12)
                    def lookup(_):
                        if slow_step == 'lookup':
                            time.sleep(.12)
                        return spec
                    return SimpleNamespace(get_specialist=lookup)
                class FakeCoordinator:
                    def enqueue_job(self, *args, **kwargs):
                        if slow_step == 'enqueue':
                            time.sleep(.12)
                        return 'fixture-job'
                    def execute_verified_check(self, **kwargs):
                        return {'verified_pass': True}
                    def cancel_job(self, job): pass
                namespace = self.gate_namespace(database, FakeCoordinator())
                task = asyncio.create_task(namespace['run_specialist_gate_endpoint']('fixture', FakeRequest()))
                before = time.monotonic()
                await asyncio.sleep(.02)
                delay = time.monotonic() - before
                # Join before asserting so a RED result retains no owned task.
                result = await task
                self.assertLess(delay, .09, (slow_step, delay))
                self.assertTrue(result['result']['verified_pass'])

    async def test_cancellation_during_admission_cancels_and_joins_reservation(self):
        spec = SimpleNamespace(agent_id='fixture', name='Fixture', metadata={})
        entered = threading.Event()
        release = threading.Event()
        cancelled = set()
        reservations = set()
        observations = []
        class FakeCoordinator:
            def enqueue_job(self, *args, **kwargs):
                entered.set()
                if not release.wait(2):
                    raise RuntimeError('Synthetic admission did not release')
                reservations.add('fixture-job')
                return 'fixture-job'
            def execute_verified_check(self, job_id, **kwargs):
                observations.append(job_id in cancelled)
                reservations.discard(job_id)
                return {'status': 'cancelled' if job_id in cancelled else 'passed',
                        'verified_pass': job_id not in cancelled}
            def cancel_job(self, job): cancelled.add(job)
        class FakeRequest:
            async def is_disconnected(self): return False
        namespace = self.gate_namespace(
            lambda: SimpleNamespace(get_specialist=lambda _: spec), FakeCoordinator())
        task = asyncio.create_task(namespace['run_specialist_gate_endpoint']('fixture', FakeRequest()))
        loop = asyncio.get_running_loop()
        def cancel_while_admitting():
            if entered.wait(1):
                loop.call_soon_threadsafe(task.cancel)
            time.sleep(.04)
            release.set()
        cancelling = threading.Thread(target=cancel_while_admitting)
        cancelling.start()
        try:
            with self.assertRaises(asyncio.CancelledError):
                await task
        finally:
            release.set()
            cancelling.join(2)
        self.assertFalse(cancelling.is_alive())
        self.assertEqual(observations, [True])
        self.assertEqual(reservations, set())

    async def test_catalog_database_work_runs_outside_event_loop(self):
        import httpx
        from fastapi import APIRouter, FastAPI, HTTPException
        source = Path(__file__).resolve().parents[2] / 'backend/routers/agent_crew_router.py'
        selected = [n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body
                    if getattr(n, 'name', '') == 'list_specialist_domains_endpoint']
        def database():
            time.sleep(.12)
            return SimpleNamespace(list_specialists=lambda **_: [])
        router = APIRouter()
        namespace = dict(router=router, _get_specialist_db=database, DOMAIN_TAXONOMY={},
                         HTTPException=HTTPException)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
        app = FastAPI()
        app.include_router(router)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://synthetic') as client:
            task = asyncio.create_task(client.get('/domains'))
            before = time.monotonic()
            await asyncio.sleep(.02)
            delay = time.monotonic() - before
            response = await task
        self.assertEqual(response.status_code, 200)
        self.assertLess(delay, .09)

    async def test_disconnect_during_admission_stops_before_execution(self):
        spec = SimpleNamespace(agent_id='fixture', name='Fixture', metadata={})
        entered, release = threading.Event(), threading.Event()
        cancelled, reservations, observations = set(), set(), []
        class FakeCoordinator:
            def enqueue_job(self, *args, **kwargs):
                entered.set()
                if not release.wait(2):
                    raise RuntimeError('Synthetic admission did not release')
                reservations.add('fixture-job')
                return 'fixture-job'
            def execute_verified_check(self, job_id, **kwargs):
                observations.append(job_id in cancelled)
                reservations.discard(job_id)
                return {'status': 'cancelled', 'verified_pass': False}
            def cancel_job(self, job): cancelled.add(job)
        class FakeRequest:
            async def is_disconnected(self):
                if entered.is_set():
                    asyncio.get_running_loop().call_later(.02, release.set)
                    return True
                return False
        namespace = self.gate_namespace(
            lambda: SimpleNamespace(get_specialist=lambda _: spec), FakeCoordinator())
        try:
            result = await namespace['run_specialist_gate_endpoint']('fixture', FakeRequest())
        finally:
            release.set()
        self.assertEqual(result['result']['status'], 'cancelled')
        self.assertEqual(observations, [True])
        self.assertEqual(reservations, set())

    def test_parallel_registry_initialization_publishes_only_completed_seed(self):
        source = Path(__file__).resolve().parents[2] / 'backend/routers/agent_crew_router.py'
        selected = [n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body
                    if getattr(n, 'name', '') == '_get_specialist_db']
        creations, seeds, premature = [], [], []
        namespace = dict(_specialist_db=None, _specialist_db_lock=threading.Lock())
        class FakeDatabase:
            def __init__(self):
                creations.append(self)
                time.sleep(.02)
            def list_specialists(self, **kwargs): return []
        def seed(database):
            premature.append(namespace['_specialist_db'] is not None)
            time.sleep(.02)
            seeds.append(database)
        namespace.update(PersistentAgentDatabase=FakeDatabase, seed_all_64_specialists=seed)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
        with ThreadPoolExecutor(max_workers=8) as pool:
            databases = list(pool.map(lambda _: namespace['_get_specialist_db'](), range(8)))
        self.assertEqual(len(creations), 1)
        self.assertEqual(seeds, creations)
        self.assertEqual(premature, [False])
        self.assertTrue(all(database is creations[0] for database in databases))

    def test_evidence_query_failure_closes_connection(self):
        from fastapi import HTTPException
        source = Path(__file__).resolve().parents[2] / 'backend/routers/agent_crew_router.py'
        selected = [n for n in ast.parse(source.read_text(encoding='utf-8-sig')).body
                    if getattr(n, 'name', '') == 'get_specialist_evidence_endpoint']
        selected[0].decorator_list = []
        closed = []
        class FakeCursor:
            def execute(self, *args):
                raise RuntimeError('Synthetic query failure')
        connection = SimpleNamespace(cursor=lambda: FakeCursor(), close=lambda: closed.append(True))
        namespace = dict(HTTPException=HTTPException,
                         _get_specialist_db=lambda: SimpleNamespace(db_path='unused-synthetic-path'))
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
        with patch.dict(sys.modules, {'sqlite3': SimpleNamespace(connect=lambda _: connection)}):
            with self.assertRaises(HTTPException) as caught:
                namespace['get_specialist_evidence_endpoint']('fixture')
        self.assertEqual(caught.exception.status_code, 500)
        self.assertEqual(closed, [True])

    async def test_route_keeps_event_loop_responsive(self):
        from pydantic import ValidationError
        spec = SimpleNamespace(agent_id='fixture', name='Fixture', metadata={})
        class FakeCoordinator:
            def enqueue_job(self, *args, **kwargs): return 'fixture-job'
            def execute_verified_check(self, **kwargs):
                time.sleep(.12)
                return {'verified_pass': True}
            def cancel_job(self, job): pass
        class FakeRequest:
            async def is_disconnected(self): return False
        ns = self.gate_namespace(lambda: SimpleNamespace(get_specialist=lambda _: spec), FakeCoordinator())
        for values in ({'timeout_sec': 0}, {'timeout_sec': 1801}, {'priority': 6}):
            with self.assertRaises(ValidationError):
                ns['SpecialistRunGateRequest'](**values)
        task = asyncio.create_task(ns['run_specialist_gate_endpoint']('fixture', FakeRequest()))
        start = time.monotonic()
        await asyncio.sleep(.02)
        self.assertLess(time.monotonic() - start, .09)
        self.assertTrue((await task)['result']['verified_pass'])


if __name__ == '__main__':
    unittest.main()
