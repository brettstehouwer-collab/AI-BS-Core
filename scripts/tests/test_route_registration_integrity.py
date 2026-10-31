"""Offline registration tests: actual FastAPI, temporary plugins, forbidden engines."""
import asyncio
import contextlib
import importlib.util
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import tempfile
import types
import unittest
from unittest.mock import patch
import httpx
from fastapi import APIRouter, FastAPI
from starlette.routing import Route, WebSocketRoute, Mount

ROOT = Path(os.environ.get("AI_BS_ROUTE_TEST_ROOT", Path(__file__).resolve().parents[2]))
CANONICAL = Path(os.environ.get("AI_BS_CANONICAL_ROOT", "C:/AI-BS"))
sys.path.insert(0, str(CANONICAL / "backend"))

def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def forbidden(*args, **kwargs):
    raise AssertionError("engine/provider/handler hook must not execute")

class ForbiddenEngine:
    def __getattr__(self, name):
        return forbidden

@contextlib.contextmanager
def isolated_dependencies():
    modules = {}
    for name, attrs in {
        'security.firebase_auth': {'get_admin_principal': lambda key, auth: 'test-admin' if key == 'test-only' else None},
        'core.executive_action_dispatcher': {'executive_dispatcher': ForbiddenEngine(), 'TOOL_MANIFEST': {}},
        'core.obs_broadcast_controller': {'ObsBroadcastController': ForbiddenEngine()},
        'core.ecosystem_telemetry_engine': {'EcosystemTelemetryEngine': ForbiddenEngine()},
        'core.autonomous_sentinel_engine': {'sentinel_engine': ForbiddenEngine()},
        'core.cloud_gpu_burst_engine': {'cloud_burst_engine': ForbiddenEngine()},
        # A sentinel stub intentionally has no invented get_self_healing_sentinel export.
        'core.self_healing_sentinel': {},
    }.items():
        modules[name] = types.ModuleType(name)
        vars(modules[name]).update(attrs)
    with patch.dict(sys.modules, modules):
        # Earlier suites can cache this guard with a different principal resolver.
        # Load the actual guard against this fixture auth module; patch.dict
        # restores its prior sys.modules entry when the fixture exits.
        load('backend/security/host_control_access.py', 'security.host_control_access')
        yield

class RegistrationTests(unittest.IsolatedAsyncioTestCase):
    def test_loader_policy_and_order(self):
        loader = load('backend/core/plugin_loader.py', 'fixture_loader')
        calls = []
        @contextlib.asynccontextmanager
        async def lifecycle(app):
            calls.append('lifespan')
            yield
        router = APIRouter(lifespan=lifecycle)
        router.add_api_route('/same', forbidden, methods=['GET'])
        router.on_startup.append(forbidden)
        modules = {name: types.SimpleNamespace(router=router, init_module=forbidden) for name in ['a_plugin', 'z_plugin']}
        with tempfile.TemporaryDirectory() as directory:
            for name in modules:
                Path(directory, name + '.py').write_text('')
            app = FastAPI()
            with patch.dict(os.environ, {'AI_BS_BACKEND_BACKGROUND_ENABLED': 'false'}), patch.dict(sys.modules, modules):
                rows = loader.PluginRegistry().discover_and_mount_plugins(app, [directory])
            self.assertEqual([r['name'] for r in rows], ['a_plugin','z_plugin'])
            self.assertEqual([r['init_status'] for r in rows], ['skipped_policy'] * 2)
            self.assertTrue(all(r['registration_status'] == 'registered' for r in rows))
            self.assertTrue(rows[1]['conflicts'])
            self.assertIs(router.lifespan_context, lifecycle)
            self.assertEqual(router.on_startup, [forbidden])
            asyncio.run(self.check_lifecycle(app))
            self.assertEqual(calls, [])

    def test_enabled_lifespan_and_sync_init_are_preserved(self):
        loader = load('backend/core/plugin_loader.py', 'fixture_loader_enabled')
        events = []
        @contextlib.asynccontextmanager
        async def lifecycle(app):
            events.append('enter')
            yield
            events.append('exit')
        router = APIRouter(lifespan=lifecycle)
        router.add_api_route('/enabled', forbidden, methods=['GET'])
        module = types.SimpleNamespace(router=router, init_module=lambda app: events.append('init'))
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'enabled_plugin.py').write_text('')
            with patch.dict(os.environ, {'AI_BS_BACKEND_BACKGROUND_ENABLED':'true'}), patch.dict(sys.modules, {'enabled_plugin':module}):
                app = FastAPI()
                rows = loader.PluginRegistry().discover_and_mount_plugins(app,[directory,directory])
            self.assertEqual(rows[0]['init_status'],'initialized')
            self.assertEqual(rows[1]['status'],'duplicate_discovery')
            asyncio.run(self.check_lifecycle(app))
            status = rows[0]['lifecycle_status']
            self.assertIn(status, ['integrated','unavailable_framework'])
            self.assertEqual(events,['init','enter','exit'] if status == 'integrated' else ['init'])
            self.assertIs(router.lifespan_context,lifecycle)

    async def check_lifecycle(self, app):
        async with app.router.lifespan_context(app):
            pass

    def test_loader_failure_and_async_truth(self):
        loader = load('backend/core/plugin_loader.py', 'fixture_loader_async')
        async def hook(app):
            forbidden()
        def failure(app):
            raise RuntimeError('secret-file-path-or-token')
        with tempfile.TemporaryDirectory() as directory:
            for name in ['a_async','b_failure']:
                Path(directory, name + '.py').write_text('')
            modules = {'a_async': types.SimpleNamespace(init_module=hook), 'b_failure': types.SimpleNamespace(init_module=failure)}
            with patch.dict(os.environ, {'AI_BS_BACKEND_BACKGROUND_ENABLED':'true'}), patch.dict(sys.modules, modules):
                rows = loader.PluginRegistry().discover_and_mount_plugins(FastAPI(),[directory])
            self.assertEqual(rows[0]['init_status'],'deferred_async')
            self.assertEqual(rows[1]['init_status'],'failed')
            self.assertNotIn('secret-file-path-or-token', str(rows))
            self.assertEqual(rows[1]['error_type'],'RuntimeError')

    async def test_sentinel_admin_and_held(self):
        with isolated_dependencies():
            module = load('backend/routers/self_healing_router.py','fixture_self_healing')
            app = FastAPI(); app.include_router(module.router)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                for path, method, body in [('/status','GET',None),('/incidents','GET',None),('/heal','POST',{'error_trace':'x'}),('/circuit-breaker/reset','POST',{})]:
                    url = '/api/sentinel' + path
                    self.assertEqual((await client.request(method,url,json=body)).status_code,403)
                    response = await client.request(method,url,json=body,headers={'x-admin-key':'test-only'})
                    self.assertEqual(response.status_code,503)
                    self.assertEqual(response.headers['cache-control'],'private, no-store')

    async def test_runtime_audit_order_auth_and_limits(self):
        with isolated_dependencies():
            load('backend/core/plugin_loader.py','core.plugin_loader')
            module = load('backend/routers/executive_cockpit_router.py','fixture_executive')
            app = FastAPI(); app.include_router(module.router)
            nested = APIRouter(); nested.add_api_route('/leaf',forbidden,methods=['GET'])
            parent = APIRouter(); parent.include_router(nested,prefix='/inner')
            app.include_router(parent,prefix='/outer')
            app.router.routes.extend([Route('/duplicate',forbidden,methods=['GET']), Route('/duplicate',forbidden,methods=['GET']), WebSocketRoute('/ws',forbidden), Mount('/nested',routes=[Route('/leaf',forbidden,methods=['POST'])])])
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                url='/api/v1/executive/route-audit'
                self.assertEqual((await client.get(url)).status_code,403)
                response=await client.get(url,headers={'x-admin-key':'test-only'})
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.headers['cache-control'],'private, no-store')
                data=response.json()
                self.assertEqual([r['path'] for r in data['routes'][-5:]],['/duplicate','/duplicate','/ws','/nested','/nested/leaf'])
                self.assertEqual(data['routes'][-3]['kind'],'websocket')
                self.assertTrue(any(r['path']=='/duplicate' for r in data['duplicates']))
                self.assertFalse(data['truncated'])
                self.assertTrue(any(r['path']=='/api/v1/executive/route-audit' for r in data['routes']))
                self.assertTrue(any(r['path']=='/outer/inner/leaf' for r in data['routes']))
                self.assertEqual(set(data['routes'][0]), {'index','kind','path','name','methods','depth'})
                nested = Route('/deep', forbidden)
                for _ in range(12):
                    nested = Mount('/layer',routes=[nested])
                app.router.routes.append(nested)
                depth_limited=(await client.get(url,headers={'x-admin-key':'test-only'})).json()
                self.assertTrue(depth_limited['truncated'])
                self.assertLessEqual(max(r['depth'] for r in depth_limited['routes']),8)
                app.router.routes.extend(Route('/bounded',forbidden) for _ in range(1100))
                limited=(await client.get(url,headers={'x-admin-key':'test-only'})).json()
                self.assertTrue(limited['truncated'])
                self.assertEqual(len(limited['routes']),1000)

class RouteCatalogPagingTests(unittest.IsolatedAsyncioTestCase):
    def loader(self, name='fixture_paging_loader'):
        return load('backend/core/plugin_loader.py', name)

    def audit_app(self):
        self.loader('core.plugin_loader')
        module = load('backend/routers/executive_cockpit_router.py', 'fixture_paging_executive')
        app = FastAPI()
        app.include_router(module.router)
        return app

    async def test_second_page_reaches_tail_with_global_indexes(self):
        with isolated_dependencies():
            app = self.audit_app()
            app.router.routes.extend(Route(f'/paging/{n}', forbidden, methods=['GET']) for n in range(1205))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                first = (await client.get('/api/v1/executive/route-audit', headers={'x-admin-key':'test-only'})).json()
                response = await client.get('/api/v1/executive/route-audit',
                    params={'offset':1000,'expected_snapshot':first['snapshot']}, headers={'x-admin-key':'test-only'})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers['cache-control'],'private, no-store')
            second = response.json()
            self.assertEqual(len(first['routes']),1000)
            self.assertEqual(first['pagination']['next_offset'],1000)
            self.assertEqual(second['routes'][0]['index'],1000)
            self.assertIn('/paging/1204',{r['path'] for r in second['routes']})
            self.assertFalse({r['index'] for r in first['routes']} & {r['index'] for r in second['routes']})
            self.assertEqual(first['snapshot'],second['snapshot'])
            self.assertEqual(second['pagination']['total_routes'],len(first['routes'])+len(second['routes']))
            self.assertIsNone(second['pagination']['next_offset'])
            self.assertTrue(second['pagination']['complete'])
            self.assertFalse(second['pagination']['traversal_truncated'])
            self.assertEqual(set(second['routes'][0]),{'index','kind','path','name','methods','depth'})

    async def test_cross_page_duplicate_retains_first_global_index(self):
        with isolated_dependencies():
            app = self.audit_app()
            loader = self.loader('core.plugin_loader')
            first_index = len(loader.collect_route_metadata(app.routes)['routes'])
            app.router.routes.append(Route('/paging-shared',forbidden,methods=['GET']))
            app.router.routes.extend(Route(f'/paging-gap/{n}',forbidden,methods=['GET']) for n in range(1050))
            app.router.routes.append(Route('/paging-shared',forbidden,methods=['GET']))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                response = await client.get('/api/v1/executive/route-audit',params={'offset':1000},headers={'x-admin-key':'test-only'})
            data = response.json()
            duplicate = next(r for r in data['duplicates'] if r['path']=='/paging-shared' and r['method']=='GET')
            self.assertEqual(duplicate['first_index'],first_index)
            self.assertEqual(duplicate['index'],first_index+1051)
            self.assertTrue(any(r['index']==duplicate['index'] for r in data['routes']))

    async def test_query_bounds_and_snapshot_format_follow_admission(self):
        with isolated_dependencies():
            app = self.audit_app()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                for params in [{'offset':-1},{'offset':10001},{'offset':'wrong'},{'limit':0},{'limit':1001},
                               {'limit':'wrong'},{'expected_snapshot':'not-a-snapshot'},{'expected_snapshot':'F'*64}]:
                    with self.subTest(params=params):
                        denied = await client.get('/api/v1/executive/route-audit',params=params)
                        invalid = await client.get('/api/v1/executive/route-audit',params=params,headers={'x-admin-key':'test-only'})
                        self.assertEqual(denied.status_code,403)
                        self.assertEqual(invalid.status_code,422)
                        self.assertEqual(denied.headers['cache-control'],'private, no-store')
                        self.assertEqual(invalid.headers['cache-control'],'private, no-store')

    async def test_changed_catalog_rejects_stale_snapshot_without_route_data(self):
        with isolated_dependencies():
            app = self.audit_app()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                first = (await client.get('/api/v1/executive/route-audit',params={'limit':3},headers={'x-admin-key':'test-only'})).json()
                app.router.routes.append(Route('/paging-added',forbidden,methods=['GET']))
                params = {'offset':3,'limit':3,'expected_snapshot':first['snapshot']}
                denied = await client.get('/api/v1/executive/route-audit',params=params)
                stale = await client.get('/api/v1/executive/route-audit',params=params,headers={'x-admin-key':'test-only'})
                refreshed = (await client.get('/api/v1/executive/route-audit',headers={'x-admin-key':'test-only'})).json()
                current = await client.get('/api/v1/executive/route-audit',
                    params={'offset':3,'limit':3,'expected_snapshot':refreshed['snapshot']},headers={'x-admin-key':'test-only'})
            self.assertEqual(denied.status_code,403)
            self.assertEqual(stale.status_code,409)
            self.assertEqual(stale.headers['cache-control'],'private, no-store')
            self.assertNotIn('routes',stale.json())
            self.assertNotIn('snapshot',stale.json())
            self.assertNotEqual(first['snapshot'],refreshed['snapshot'])
            self.assertEqual(current.status_code,200)

    def test_conflict_after_first_page_is_reported_without_hooks(self):
        loader = self.loader()
        app = FastAPI()
        app.router.routes.extend(Route(f'/existing/{n}',forbidden,methods=['GET']) for n in range(1005))
        app.router.routes.append(Route('/late-conflict',forbidden,methods=['GET']))
        router = APIRouter()
        router.add_api_route('/late-conflict',forbidden,methods=['GET'])
        module = types.SimpleNamespace(router=router,init_module=forbidden)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory,'paging_plugin.py').write_text('')
            with patch.dict(os.environ,{'AI_BS_BACKEND_BACKGROUND_ENABLED':'false'}),patch.dict(sys.modules,{'paging_plugin':module}):
                rows = loader.PluginRegistry().discover_and_mount_plugins(app,[directory])
        self.assertEqual(rows[0]['registration_status'],'registered')
        self.assertEqual(rows[0]['init_status'],'skipped_policy')
        conflict = next(c for c in rows[0]['conflicts'] if c['path']=='/late-conflict' and c['method']=='GET')
        self.assertGreater(conflict['existing_indices'][0],1000)
        self.assertFalse(rows[0]['conflicts_truncated'])

    def test_incoming_plugin_tail_conflicts_are_also_reported(self):
        loader = self.loader()
        app = FastAPI()
        app.router.routes.append(Route('/incoming-tail',forbidden,methods=['GET']))
        router = APIRouter()
        for n in range(1005):
            router.add_api_route(f'/incoming/{n}',forbidden,methods=['GET'])
        router.add_api_route('/incoming-tail',forbidden,methods=['GET'])
        module = types.SimpleNamespace(router=router,init_module=forbidden)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory,'incoming_plugin.py').write_text('')
            with patch.dict(os.environ,{'AI_BS_BACKEND_BACKGROUND_ENABLED':'false'}),patch.dict(sys.modules,{'incoming_plugin':module}):
                rows = loader.PluginRegistry().discover_and_mount_plugins(app,[directory])
        self.assertTrue(any(c['path']=='/incoming-tail' for c in rows[0]['conflicts']))
        self.assertFalse(rows[0]['conflicts_truncated'])

    def test_depth_cycles_and_repeated_sibling_mounts_stay_bounded(self):
        loader = self.loader()
        cycle = Mount('/cycle',routes=[])
        cycle.routes.append(cycle)
        shared = Mount('/shared',routes=[Route('/leaf',forbidden,methods=['GET'])])
        deep = Route('/bottom',forbidden,methods=['GET'])
        for _ in range(12):
            deep = Mount('/level',routes=[deep])
        catalog = loader.collect_route_metadata([cycle,shared,shared,deep])
        self.assertTrue(catalog['truncated'])
        self.assertTrue(catalog['pagination']['traversal_truncated'])
        self.assertTrue(catalog['pagination']['truncation_reasons']['cycle'])
        self.assertTrue(catalog['pagination']['truncation_reasons']['depth'])
        self.assertFalse(catalog['pagination']['truncation_reasons']['visits'])
        self.assertIsNone(catalog['pagination']['total_routes'])
        self.assertFalse(catalog['pagination']['complete'])
        self.assertLessEqual(max(r['depth'] for r in catalog['routes']),8)
        self.assertEqual(sum(r['path']=='/shared/leaf' for r in catalog['routes']),2)
        self.assertTrue(any(r['path']=='/shared/leaf' for r in catalog['duplicates']))
        self.assertEqual(catalog['snapshot'],loader.collect_route_metadata([cycle,shared,shared,deep])['snapshot'])

    def test_global_visit_budget_cannot_claim_an_unvisited_total(self):
        loader = self.loader()
        produced = []
        def routes():
            for n in range(loader.ROUTE_AUDIT_MAX_VISITS+20):
                produced.append(n)
                yield Route(f'/visit-budget/{n}',forbidden,methods=['GET'])
        catalog = loader.collect_route_metadata(routes(),offset=9000)
        self.assertLessEqual(len(produced),loader.ROUTE_AUDIT_MAX_VISITS+1)
        self.assertEqual(catalog['pagination']['visits'],loader.ROUTE_AUDIT_MAX_VISITS)
        self.assertEqual(len(catalog['routes']),1000)
        self.assertEqual(catalog['routes'][0]['index'],9000)
        self.assertEqual(catalog['routes'][-1]['index'],9999)
        self.assertTrue(catalog['pagination']['truncation_reasons']['visits'])
        self.assertIsNone(catalog['pagination']['total_routes'])
        self.assertFalse(catalog['pagination']['complete'])

    def test_snapshot_covers_full_names_and_paths_beyond_display_bounds(self):
        loader = self.loader()
        first = Route('/'+'p'*2050+'left',forbidden,methods=['GET'],name='n'*260+'left')
        second = Route('/'+'p'*2050+'right',forbidden,methods=['GET'],name='n'*260+'right')
        left = loader.collect_route_metadata([first])
        right = loader.collect_route_metadata([second])
        self.assertEqual(left['routes'],right['routes'])
        self.assertNotEqual(left['snapshot'],right['snapshot'])

    def test_empty_tail_and_invalid_direct_bounds_are_explicit(self):
        loader = self.loader()
        empty = loader.collect_route_metadata([])
        self.assertEqual(empty['routes'],[])
        self.assertEqual(empty['pagination']['total_routes'],0)
        self.assertTrue(empty['pagination']['complete'])
        tail = loader.collect_route_metadata([Route('/one',forbidden)],offset=10000,limit=1)
        self.assertEqual(tail['routes'],[])
        self.assertIsNone(tail['pagination']['next_offset'])
        self.assertEqual(tail['pagination']['total_routes'],1)
        class MustNotIterate:
            def __iter__(self):
                forbidden()
        for options in [{'offset':-1},{'offset':10001},{'offset':True},{'offset':1.5},
                        {'limit':0},{'limit':1001},{'limit':True},{'limit':'10'}]:
            with self.subTest(options=options),self.assertRaises(ValueError):
                loader.collect_route_metadata(MustNotIterate(),**options)


if __name__ == '__main__':
    unittest.main()
