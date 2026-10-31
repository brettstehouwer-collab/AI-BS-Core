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

if __name__ == '__main__':
    unittest.main()
