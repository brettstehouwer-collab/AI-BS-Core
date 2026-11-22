"""Opt-in mounted host drain; real disposable SQLite, no original stores."""
import asyncio
from contextlib import closing, contextmanager
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.swarm_runtime import SwarmRuntime
from db.swarm_sqlite import SQLiteStore
from database import cdz_audit_db as cdz
from modules import audit_ledger_watcher as module
from modules.cdz_host_lifecycle import CDZHostLifecycle
from modules import cdz_host_lifecycle as lifecycle_module
from routers import audit_ledger_router as api


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix='aibs-cdz-manual-drain-') as tmp:
        root = Path(tmp)
        project = root / 'project'
        for folder in ('backend', 'database'):
            path = project / folder / 'aibs_master.db'
            path.parent.mkdir(parents=True)
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE sentinel(value TEXT)')
                db.execute("INSERT INTO sentinel VALUES('original synthetic row')")
                db.commit()
        master = project / 'backend/aibs_master.db'
        original_master = master.read_bytes()
        source = root / 'source'
        source.mkdir()
        (source / 'synthetic_audit_ledger.json').write_text(json.dumps({'records': [{
            'index': 1, 'timestamp': 1700000001, 'domain': 'synthetic',
            'event': 'manual-drain', 'detail': 'disposable fixture',
            'hash': 'synthetic-one', 'prev_hash': 'previous', 'full_hash': 'full-one'}]}))
        workspace = root / 'tasks'
        workspace.mkdir()
        runtime = SwarmRuntime(workspace, project_root=project, config_path=ROOT / 'config/swarm_orchestration.json')
        store = runtime.stores['cdz_audit']
        store.activate(root / 'before.sqlite', allow_activation=True)
        watcher = module.CDZAuditLedgerWatcher(store=store, watch_dirs=[source])
        try:
            with patch.object(cdz, 'get_db_connection', side_effect=AssertionError('No legacy fallback')):
                yield root, project, runtime, store, watcher
        finally:
            assert watcher.drain(3), 'Owned watcher did not drain during fixture cleanup'
            assert runtime.close(timeout=3), 'Owned runtime did not close during fixture cleanup'
            assert master.read_bytes() == original_master
            with closing(sqlite3.connect(project / 'database/aibs_master.db')) as db:
                assert db.execute('select * from sentinel').fetchall() == [('original synthetic row',)]
                assert db.execute('pragma quick_check').fetchone() == ('ok',)


async def until(predicate):
    end = asyncio.get_running_loop().time() + 3
    while not predicate():
        if asyncio.get_running_loop().time() >= end:
            raise AssertionError('Bounded condition did not arrive')
        await asyncio.sleep(.002)


class ManualDrainTests(unittest.TestCase):
    def test_mounted_shutdown_waits_for_writer_queued_scan_and_summary_then_reopens(self):
        for boundary in ('writer', 'summary'):
            with self.subTest(boundary=boundary), fixture() as (root, project, runtime, store, watcher):
                entered, release = threading.Event(), threading.Event()
                real_submit = store.submit
                real_summary = module.get_cdz_summary

                def submit(callback):
                    def held(conn, event):
                        entered.set()
                        if not release.wait(5):
                            raise AssertionError('Held synthetic writer not released')
                        return callback(conn, event)
                    return real_submit(held)

                def summary(**kwargs):
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError('Held synthetic summary not released')
                    return real_summary(**kwargs)

                lifecycle = CDZHostLifecycle(watcher, drain_timeout=3)
                app = FastAPI()
                app.state.swarm_runtime = runtime
                app.state.cdz_host_lifecycle = lifecycle
                app.include_router(api.router)

                async def run():
                    context = app.router.lifespan_context(app)
                    await context.__aenter__()
                    transport = httpx.ASGITransport(app=app)
                    async with httpx.AsyncClient(transport=transport, base_url='http://synthetic') as client:
                        headers = {'x-admin-key': 'synthetic'}
                        first = asyncio.create_task(client.post('/api/audit-ledger/scan', headers=headers))
                        await until(entered.is_set)
                        second = asyncio.create_task(client.post('/api/audit-ledger/scan', headers=headers))
                        await until(lambda: watcher.get_status()['active_scans'] == 2)
                        shutdown = asyncio.create_task(context.__aexit__(None, None, None))
                        await until(lambda: watcher.get_status()['draining'])
                        self.assertFalse(shutdown.done())
                        self.assertFalse(watcher.resume_scans())
                        self.assertFalse(watcher.start())
                        self.assertFalse(watcher.drain(0))
                        with self.assertRaises(module.CDZScanDraining):
                            watcher.scan_now()
                        refused = await client.post('/api/audit-ledger/scan', headers=headers)
                        self.assertEqual(refused.status_code, 409)
                        self.assertEqual(refused.headers['cache-control'], 'private, no-store')
                        self.assertNotIn(str(root), refused.text)
                        if boundary == 'summary':
                            # Standalone diagnostic query traffic is explicitly
                            # outside scan admission, and remains usable while
                            # the outer server has not closed its HTTP boundary.
                            status = await client.get('/api/audit-ledger/summary', headers=headers)
                            self.assertEqual(status.status_code, 200)
                            self.assertTrue(status.json()['watcher']['draining'])
                        with store.reader() as db:
                            self.assertEqual(db.execute('select * from sentinel').fetchall()[0][0], 'original synthetic row')
                        release.set()
                        responses = await asyncio.gather(first, second)
                        self.assertEqual([r.status_code for r in responses], [200, 200])
                        self.assertTrue(all(r.json()['summary']['total_blocks'] == 1 for r in responses))
                        await shutdown
                        self.assertEqual(watcher.get_status()['active_scans'], 0)
                        self.assertFalse(watcher.get_status()['accepting_scans'])
                        self.assertFalse(watcher.resume_scans())
                        with self.assertRaises(module.CDZScanDraining):
                            watcher.scan_now()
                        self.assertEqual(cdz.get_cdz_summary(store=store)['total_blocks'], 1)
                    # Same host object supports an explicit next lifecycle epoch.
                    async with app.router.lifespan_context(app):
                        self.assertTrue(watcher.get_status()['accepting_scans'])
                        result, current = await asyncio.to_thread(watcher.scan_and_summarize)
                        self.assertEqual(result['new_blocks_ingested'], 0)
                        self.assertEqual(current['total_blocks'], 1)

                try:
                    with patch.object(store, 'submit', side_effect=submit) if boundary == 'writer' else patch.object(module, 'get_cdz_summary', side_effect=summary), patch('security.host_control_access.get_admin_principal', side_effect=lambda key, auth: 'admin' if key == 'synthetic' else None):
                        asyncio.run(run())
                finally:
                    release.set()
                self.assertTrue(store.close(timeout=3))
                reopened = SQLiteStore(project, 'cdz_audit')
                reopened.activate(root / 'reopen-before.sqlite', allow_activation=True)
                try:
                    fresh = module.CDZAuditLedgerWatcher(store=reopened, watch_dirs=[root / 'source'])
                    result, current = fresh.scan_and_summarize()
                    self.assertEqual(result['new_blocks_ingested'], 0)
                    self.assertEqual(current['total_blocks'], 1)
                    self.assertTrue(fresh.drain(1))
                finally:
                    reopened.close(timeout=3)

    def test_timeout_keeps_store_open_and_refuses_new_epoch_until_actual_finish(self):
        with fixture() as (_, _, runtime, store, watcher):
            entered, release = threading.Event(), threading.Event()
            real_submit = store.submit
            def submit(callback):
                def held(conn, event):
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError('Release deadline')
                    return callback(conn, event)
                return real_submit(held)
            async def run():
                app = FastAPI()
                app.state.swarm_runtime = runtime
                app.state.cdz_host_lifecycle = CDZHostLifecycle(watcher, drain_timeout=0)
                app.include_router(api.router)
                ctx = app.router.lifespan_context(app)
                await ctx.__aenter__()
                scan = asyncio.create_task(asyncio.to_thread(watcher.scan_and_summarize))
                await until(entered.is_set)
                with self.assertRaisesRegex(RuntimeError, 'keep its store open'):
                    await ctx.__aexit__(None, None, None)
                self.assertFalse(watcher.resume_scans())
                with store.reader() as db:
                    self.assertEqual(db.execute('select count(*) from sentinel').fetchone()[0], 1)
                release.set()
                result, summary = await scan
                self.assertEqual(summary['total_blocks'], 1)
                self.assertTrue(watcher.drain(1))
            try:
                with patch.object(store, 'submit', side_effect=submit):
                    asyncio.run(run())
            finally:
                release.set()

    def test_legacy_stop_does_not_disable_ordinary_manual_scans(self):
        with tempfile.TemporaryDirectory(prefix='aibs-cdz-legacy-drain-') as tmp:
            root = Path(tmp)
            with patch.object(cdz, 'DB_PATH', str(root / 'legacy.db')):
                watcher = module.CDZAuditLedgerWatcher(watch_dirs=[root])
                self.assertTrue(watcher.stop())
                self.assertEqual(watcher.scan_now()['new_blocks_ingested'], 0)
                self.assertTrue(watcher.get_status()['accepting_scans'])
                self.assertEqual(cdz.get_cdz_summary()['total_blocks'], 0)

    def test_resume_cannot_cross_empty_owners_to_worker_stop_gap(self):
        watcher = module.CDZAuditLedgerWatcher(watch_dirs=[])
        owner = CDZHostLifecycle(watcher)
        self.assertTrue(watcher.bind_host(owner))
        entered, release = threading.Event(), threading.Event()
        original_stop = watcher.stop
        results = []
        def held_stop(timeout):
            entered.set()
            if not release.wait(3):
                raise AssertionError('Stop gap release deadline')
            return original_stop(timeout)
        with patch.object(watcher, 'stop', side_effect=held_stop):
            thread = threading.Thread(target=lambda: results.append(watcher.drain(2)))
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                self.assertFalse(watcher.resume_scans(owner=owner))
                self.assertFalse(watcher.resume_scans())
                self.assertFalse(watcher.start())
            finally:
                release.set()
                thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results, [True])
        self.assertFalse(watcher.resume_scans())
        self.assertTrue(watcher.resume_scans(owner=owner))

    def test_cancelled_http_waiter_does_not_retire_running_sqlite_work(self):
        with fixture() as (_, _, runtime, store, watcher):
            entered, release = threading.Event(), threading.Event()
            original_submit = store.submit
            def submit(callback):
                def held(conn, event):
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError('Cancellation release deadline')
                    return callback(conn, event)
                return original_submit(held)
            async def run():
                app = FastAPI()
                app.state.swarm_runtime = runtime
                app.state.cdz_host_lifecycle = CDZHostLifecycle(watcher, drain_timeout=3)
                app.include_router(api.router)
                context = app.router.lifespan_context(app)
                await context.__aenter__()
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://synthetic') as client:
                    request = asyncio.create_task(client.post('/api/audit-ledger/scan', headers={'x-admin-key': 'synthetic'}))
                    await until(entered.is_set)
                    request.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await request
                    closing = asyncio.create_task(context.__aexit__(None, None, None))
                    await until(lambda: watcher.get_status()['draining'])
                    self.assertFalse(closing.done())
                    self.assertEqual(watcher.get_status()['active_scans'], 1)
                    release.set()
                    await closing
                    self.assertEqual(cdz.get_cdz_summary(store=store)['total_blocks'], 1)
            try:
                with patch.object(store, 'submit', side_effect=submit), patch('security.host_control_access.get_admin_principal', return_value='admin'):
                    asyncio.run(run())
            finally:
                release.set()

    def test_opt_in_poll_lifespan_starts_and_actually_joins_its_worker(self):
        with fixture() as (_, _, runtime, store, _):
            watcher = module.CDZAuditLedgerWatcher(poll_interval=3600, store=store, watch_dirs=[])
            lifecycle = CDZHostLifecycle(watcher, poll=True, drain_timeout=2)
            async def run():
                app = FastAPI()
                app.state.swarm_runtime = runtime
                app.state.cdz_host_lifecycle = lifecycle
                app.include_router(api.router)
                async with app.router.lifespan_context(app):
                    await until(lambda: watcher.total_scans > 0)
                    self.assertTrue(watcher.get_status()['running'])
                self.assertFalse(watcher.get_status()['running'])
                self.assertFalse(watcher.resume_scans())
                self.assertTrue(watcher.drain(0))
            asyncio.run(run())

    def test_normal_include_router_absent_opt_in_is_inert(self):
        app = FastAPI()
        app.include_router(api.router)
        with patch.object(api.cdz_watcher, 'get_status', side_effect=AssertionError('Absent opt-in must be inert')), patch.object(api.cdz_watcher, 'start') as start, patch.object(api.cdz_watcher, 'stop') as stop, TestClient(app):
            pass
        start.assert_not_called()
        stop.assert_not_called()
        self.assertFalse(hasattr(app.state, 'cdz_watcher'))

    def test_normal_include_router_typed_opt_in_uses_testclient_lifespan(self):
        with fixture() as (_, _, runtime, store, watcher):
            app = FastAPI()
            app.state.swarm_runtime = runtime
            app.state.cdz_host_lifecycle = CDZHostLifecycle(watcher)
            app.include_router(api.router)
            with patch('security.host_control_access.get_admin_principal', return_value='admin'), TestClient(app) as client:
                self.assertIs(app.state.cdz_watcher, watcher)
                self.assertTrue(watcher.get_status()['host_bound'])
                response = client.post('/api/audit-ledger/scan')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['summary']['total_blocks'], 1)
            self.assertFalse(watcher.get_status()['accepting_scans'])
            self.assertEqual(cdz.get_cdz_summary(store=store)['total_blocks'], 1)

    def test_cancelled_shutdown_before_executor_start_retains_epoch_until_join(self):
        with fixture() as (_, _, runtime, _, watcher):
            lifecycle = CDZHostLifecycle(watcher, drain_timeout=1)
            actual_to_thread = asyncio.to_thread
            async def run():
                may_start = asyncio.Event()
                queued = asyncio.Event()
                drain_started = threading.Event()
                actual_drain = watcher.drain
                def observed_drain(*args):
                    drain_started.set()
                    return actual_drain(*args)
                async def delayed_to_thread(fn, *args):
                    queued.set()
                    await may_start.wait()
                    return await actual_to_thread(fn, *args)
                app = FastAPI()
                app.state.swarm_runtime = runtime
                app.state.cdz_host_lifecycle = lifecycle
                app.include_router(api.router)
                context = app.router.lifespan_context(app)
                await context.__aenter__()
                with patch.object(lifecycle_module.asyncio, 'to_thread', side_effect=delayed_to_thread), patch.object(watcher, 'drain', side_effect=observed_drain):
                    closing = asyncio.create_task(context.__aexit__(None, None, None))
                    await asyncio.wait_for(queued.wait(), 1)
                    self.assertFalse(drain_started.is_set())
                    self.assertFalse(watcher.get_status()['accepting_scans'])
                    for _ in range(2):
                        closing.cancel()
                        await asyncio.sleep(.005)
                        self.assertFalse(closing.done())
                        self.assertTrue(lifecycle._entered)
                        self.assertTrue(watcher.get_status()['host_join_pending'])
                        self.assertFalse(watcher.resume_scans(owner=lifecycle))
                        self.assertFalse(watcher.start())
                        with self.assertRaises(module.CDZScanDraining):
                            watcher.scan_now()
                        another = app.router.lifespan_context(app)
                        with self.assertRaisesRegex(RuntimeError, 'active host'):
                            await another.__aenter__()
                    may_start.set()
                    with self.assertRaises(asyncio.CancelledError):
                        await asyncio.wait_for(closing, 2)
                self.assertTrue(drain_started.is_set())
                self.assertTrue(lifecycle.last_drain_succeeded)
                self.assertFalse(lifecycle._entered)
                self.assertIsNone(lifecycle._drain_task)
                self.assertFalse(watcher.get_status()['host_join_pending'])
                self.assertFalse(watcher.resume_scans())
                async with app.router.lifespan_context(app):
                    self.assertTrue(watcher.get_status()['accepting_scans'])
            asyncio.run(run())

    def test_normal_include_router_malformed_opt_in_refuses_before_binding(self):
        for malformed in (object(), 'not-a-lifecycle', False):
            with self.subTest(type=type(malformed).__name__):
                app = FastAPI()
                app.state.cdz_host_lifecycle = malformed
                app.include_router(api.router)
                with patch.object(api.cdz_watcher, 'get_status', side_effect=AssertionError('Validate typed opt-in first')):
                    with self.assertRaisesRegex(RuntimeError, 'typed CDZHostLifecycle'):
                        with TestClient(app):
                            pass
                self.assertFalse(hasattr(app.state, 'cdz_watcher'))

    def test_normal_include_router_refuses_active_separate_legacy_scanner(self):
        with fixture() as (_, _, runtime, _, watcher):
            for status in ({'running': True, 'active_scans': 0}, {'running': False, 'active_scans': 1}):
                with self.subTest(status=status):
                    app = FastAPI()
                    app.state.swarm_runtime = runtime
                    app.state.cdz_host_lifecycle = CDZHostLifecycle(watcher)
                    app.include_router(api.router)
                    with patch.object(api.cdz_watcher, 'get_status', return_value=status), patch.object(api.cdz_watcher, 'stop') as stop:
                        with self.assertRaisesRegex(RuntimeError, 'Separate legacy CDZ scanning is active'):
                            with TestClient(app):
                                pass
                        stop.assert_not_called()
                    self.assertFalse(hasattr(app.state, 'cdz_watcher'))


if __name__ == '__main__':
    unittest.main()
