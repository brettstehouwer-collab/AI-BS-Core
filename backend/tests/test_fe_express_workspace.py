"""Portal persistence infrastructure with synthetic SQLite and scoped auth."""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import FastAPI, APIRouter, Depends
from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fe_express_workspace as workspace
from security import fe_express_access as access


@pytest.fixture
def api(tmp_path, monkeypatch):
    app = FastAPI()
    parent = APIRouter(prefix=access.PREFIX, dependencies=[Depends(access.require_fe_express_access)])
    parent.include_router(workspace.router)
    app.include_router(parent)
    app.dependency_overrides[workspace.database_path] = lambda: tmp_path / 'portal.sqlite'
    monkeypatch.setattr(access, 'verify_admin_credentials', lambda key, auth: auth == 'Bearer synthetic-admin')
    return TestClient(app)


BASE = '/api/v1/fe-express/workspace'
AUTH = {'Authorization': 'Bearer synthetic-admin'}


def test_persistence_auth_revision_and_reopened_database(api):
    assert api.get(BASE).status_code == 401
    assert api.put(BASE, json={'revision': 0, 'values': {}}).status_code == 401
    first = api.get(BASE, headers=AUTH)
    assert first.headers['cache-control'] == 'no-store'
    assert first.json() == dict(revision=0, saved_at=None, values={})
    values = {'homeBase': 'Synthetic City', 'newDriverName': 'Synthetic draft', 'reportDriver': 'OWNER-DEVIN',
              'report.sheetDrafts': {'OWNER-DEVIN:2026-10-26': {'2026-10-26': {'revision': 7, 'notes': 'Kept draft'}}}}
    assert api.put(BASE, headers=AUTH, json=dict(revision=0, values=values)).json()['revision'] == 1
    assert api.get(BASE, headers=AUTH).json()['values'] == values
    assert api.put(BASE, headers=AUTH, json=dict(revision=0, values={})).status_code == 409
    assert api.get(BASE, headers=AUTH).json()['values'] == values


def test_concurrent_sessions_cannot_silently_replace(api):
    api.get(BASE, headers=AUTH)
    with ThreadPoolExecutor(2) as pool:
        codes = list(pool.map(lambda n: api.put(BASE, headers=AUTH, json=dict(revision=0, values={'homeBase': str(n)})).status_code, range(2)))
    assert sorted(codes) == [200, 409]


@pytest.mark.parametrize('body', [
    {'revision': True, 'values': {}}, {'revision': -1, 'values': {}},
    {'revision': 0, 'values': {'token': 'forbidden'}},
    {'revision': 0, 'values': {'homeBase': {}}},
    {'revision': 0, 'values': {'report.sheetDrafts': {'__proto__': {}}}},
    {'revision': 0, 'values': {'newDriverNotes': 'a' * 4001}},
    {'revision': 0, 'values': {'report.sheetDrafts': []}},
])
def test_invalid_payload_keeps_existing_save(api, body):
    assert api.put(BASE, headers=AUTH, json=body).status_code == 422
    assert api.get(BASE, headers=AUTH).json()['revision'] == 0


def test_duplicate_json_and_size_limit(api):
    assert api.put(BASE, headers=AUTH, content=b'{"revision":0,"revision":1,"values":{}}').status_code == 422
    assert api.put(BASE, headers=AUTH, content=b' ' * (workspace.MAX_BYTES + 1)).status_code == 413
