"""JSON-line fixture transport for actual screenplay route bodies and models.

Uses only TemporaryDirectory manuscripts. This is not the application HTTP/auth
stack, a running production service, or a real-user project acceptance test.
"""
import ast
import json
import sys
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, StrictInt, ValidationError

from test_creation_project_lifecycle import ProjectLifecycleTests, ROOT


fixture = ProjectLifecycleTests()
fixture.setUp()
scope = fixture.scope
scope.update(BaseModel=BaseModel, StrictInt=StrictInt)
model_names = {'WriteScreenplayPayload', 'WorkflowMutationPayload', 'BranchCreatePayload',
               'BranchSwitchPayload', 'SprintStartPayload', 'SprintEndPayload', 'WorkflowRecoveryPayload',
               'ReorderBeatsPayload'}
tree = ast.parse((ROOT / 'backend/routers/screenwriting_router.py').read_text(encoding='utf-8'))
models = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in model_names]
exec(compile(ast.Module(body=models, type_ignores=[]), '<actual-payload-models>', 'exec'), scope)
reorder = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'reorder_beats')
reorder.decorator_list = []
exec(compile(ast.Module(body=[reorder], type_ignores=[]), '<actual-reorder-route>', 'exec'), scope)
routes = {
    '/write': ('write_screenplay', 'WriteScreenplayPayload'),
    '/branch/create': ('create_branch', 'BranchCreatePayload'),
    '/branch/switch': ('switch_branch', 'BranchSwitchPayload'),
    '/sprint/start': ('start_sprint', 'SprintStartPayload'),
    '/sprint/end': ('end_sprint', 'SprintEndPayload'),
    '/workflow/recover': ('recover_workflow', 'WorkflowRecoveryPayload'),
    '/beats/reorder': ('reorder_beats', 'ReorderBeatsPayload'),
}
fail_next_write = False


def dispatch(message):
    global fail_next_write
    if message.get('fixture') == 'bytes':
        return {'hex': fixture.script.read_bytes().hex()}
    if message.get('fixture') == 'external_write':
        fixture.script.write_bytes(message['content'].encode('utf-8'))
        return {'ok': True}
    if message.get('fixture') == 'interrupt_next_write':
        fail_next_write = True
        return {'ok': True}
    parsed = urlsplit(message['url'])
    prefix = '/api/screenwriting'
    if not parsed.path.startswith(prefix + '/'):
        raise HTTPException(404, 'Unknown fixture route')
    path = parsed.path[len(prefix):]
    method = message.get('method', 'GET')
    if method == 'GET' and path in {'/read', '/branches', '/sprints'}:
        project = parse_qs(parsed.query).get('project_name', [None])[0]
        handler = {'/read': 'read_screenplay', '/branches': 'list_branches', '/sprints': 'list_sprints'}[path]
        return scope[handler](project)
    if method != 'POST' or path not in routes:
        raise HTTPException(405, 'Unsupported fixture request')
    handler, model = routes[path]
    payload = scope[model](**json.loads(message.get('body', '{}')))
    if fail_next_write and path == '/write':
        fail_next_write = False
        with patch('os.replace', side_effect=PermissionError('synthetic atomic-write interruption')):
            return scope[handler](payload)
    return scope[handler](payload)


try:
    for line in sys.stdin:
        try:
            body = dispatch(json.loads(line))
            result = {'status': 200, 'body': body}
        except HTTPException as error:
            result = {'status': error.status_code, 'body': {'detail': error.detail}}
        except ValidationError:
            result = {'status': 422, 'body': {'detail': 'Fixture payload validation failed'}}
        except Exception as error:
            result = {'status': 500, 'body': {'detail': type(error).__name__}}
        print(json.dumps(result), flush=True)
finally:
    fixture.doCleanups()
