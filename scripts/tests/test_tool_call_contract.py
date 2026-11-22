"""Offline AST-extracted production contract regressions; no service imports."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys
import tempfile
from types import ModuleType
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'backend'
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def load_parser(path):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == 'extract_and_parse_tool_call')
    env = {'json': json, 're': re}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / path), 'exec'), env)
    return env[node.name]


def load_registry():
    tree = ast.parse((ROOT / 'backend/tools/tool_registry.py').read_text(encoding='utf-8-sig'))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ToolRegistry')
    # Compile the real class, excluding only module-level imports and mkdir.
    env = {}
    try:
        from tools.tool_call_contract import validate_tool_call, ToolCallValidationError
        env.update(validate_tool_call=validate_tool_call, ToolCallValidationError=ToolCallValidationError)
    except ImportError:
        pass
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / 'backend/tools/tool_registry.py'), 'exec'), env)
    return env[node.name]


class ModelToolEnvelopeTests(unittest.TestCase):
    modules = ('backend/AI_BS_Backend.py', 'backend/AI_BS_Backend_shadow.py')

    def rejects(self, text):
        for path in self.modules:
            with self.subTest(path=path):
                self.assertEqual(load_parser(path)(text), (None, None))

    def test_duplicate_tool_name_never_last_key_wins(self):
        self.rejects('{"name":"get_ecosystem_health","name":"execute_powershell","arguments":{"command":"Write-Output unsafe"}}')

    def test_duplicate_nested_argument_rejected(self):
        self.rejects('{"name":"build_program","arguments":{"files":[],"run_immediately":false,"run_immediately":true}}')

    def test_nonfinite_numeric_constant_rejected(self):
        for number in ('NaN', 'Infinity', '-Infinity', '1e9999'):
            self.rejects('{"name":"calculate_noco_spatial_parameters","arguments":{"facility_sq_ft":' + number + '}}')

    def test_wrong_argument_container_never_coerced_to_defaults(self):
        for args in ('[]', 'null', '"{}"', 'false'):
            self.rejects('{"name":"list_programs","arguments":' + args + '}')

    def test_missing_arguments_never_authorizes_default_operation(self):
        self.rejects('{"name":"list_programs"}')

    def test_nonstring_name_never_coerced(self):
        self.rejects('{"name":123,"arguments":{}}')

    def test_prose_or_multiple_objects_are_not_a_tool_envelope(self):
        for text in ('Example: {"name":"list_programs","arguments":{}}',
                     'Never run this: ```json\n{"name":"list_programs","arguments":{}}\n```',
                     '{"name":"list_programs","arguments":{}} {"name":"list_programs","arguments":{}}'):
            self.rejects(text)

    def test_extra_envelope_keys_rejected(self):
        self.rejects('{"name":"list_programs","arguments":{},"authorized":true}')

    def test_strict_json_is_not_repaired(self):
        self.rejects('{"name":"list_programs","arguments":{},}')

    def test_canonical_alias_and_complete_fence_preserved(self):
        for path in self.modules:
            parser = load_parser(path)
            for text in ('{"name":"query_memory","arguments":{"search_term":"recipe"}}',
                         '```json\n{"tool_call":{"name":"query_memory","arguments":{"search_term":"recipe"}}}\n```'):
                with self.subTest(path=path, text=text):
                    self.assertEqual(parser(text), ('query_master_memory', {'search_term': 'recipe'}))

    def test_compact_fence_preserved(self):
        for path in self.modules:
            self.assertEqual(load_parser(path)('```json {"name":"list_programs","arguments":{}} ```'),
                             ('list_programs', {}))


class RegistryContractBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()
        self.calls = []
        module = ModuleType('core.program_builder_engine')
        calls = self.calls
        class Builder:
            @staticmethod
            def build_program(**kwargs):
                calls.append(kwargs)
                return {'status': 'success'}
        module.AutonomousProgramBuilder = Builder
        self.modules = patch.dict(sys.modules, {'core.program_builder_engine': module})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def assert_rejected_without_dispatch(self, arguments):
        result = self.registry.execute_tool('build_program', arguments)
        self.assertEqual(result.get('status'), 'error')
        self.assertEqual(result.get('error_code'), 'INVALID_TOOL_CALL')
        self.assertEqual(self.calls, [])

    def test_string_false_is_not_a_boolean_capability(self):
        self.assert_rejected_without_dispatch({'project_name': 'fixture', 'files': [], 'run_immediately': 'false'})

    def test_nested_file_schema_checked_before_dispatch(self):
        self.assert_rejected_without_dispatch({'project_name': 'fixture', 'files': [{'path': 'x.py', 'content': 7}], 'run_immediately': False})

    def test_required_fields_checked_before_default_dispatch(self):
        self.assert_rejected_without_dispatch({'files': [], 'run_immediately': False})

    def test_unknown_argument_rejected_before_default_dispatch(self):
        self.assert_rejected_without_dispatch({'project_name': 'fixture', 'files': [], 'run_immediatly': False})

    def test_valid_explicit_false_reaches_existing_handler_unchanged(self):
        result = self.registry.execute_tool('build_program', {'project_name': 'fixture', 'files': [], 'run_immediately': False, 'execute_build': False})
        self.assertEqual(result['status'], 'success')
        self.assertFalse(self.calls[0]['run_immediately'])
        self.assertFalse(self.calls[0]['execute_build'])

    def test_invalid_call_never_imports_an_effectful_handler(self):
        with patch('builtins.__import__', side_effect=AssertionError('handler import attempted')):
            self.assert_rejected_without_dispatch({'project_name': 'fixture', 'files': [], 'execute_build': 'false'})


class SharedContractTests(unittest.TestCase):
    def setUp(self):
        from tools.tool_call_contract import ToolCallValidationError, validate_tool_call
        self.error = ToolCallValidationError
        self.validate = validate_tool_call
        self.declarations = load_registry().get_tool_declarations()

    def test_existing_dispatch_names_all_have_contracts(self):
        tree = ast.parse((ROOT / 'backend/tools/tool_registry.py').read_text(encoding='utf-8-sig'))
        registry = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ToolRegistry')
        dispatch = next(n for n in registry.body if isinstance(n, ast.FunctionDef) and n.name == 'execute_tool')
        names = set()
        for node in ast.walk(dispatch):
            if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Name)
                    and node.left.id == 'tool_name'):
                value = ast.literal_eval(node.comparators[0])
                names.update(value if isinstance(value, list) else [value])
        for name in names:
            with self.subTest(name=name):
                try:
                    self.validate(name, {}, self.declarations)
                except self.error as exc:
                    self.assertNotEqual(str(exc), 'Unknown tool name.')

    def test_all_declared_required_contracts_accept_well_typed_values(self):
        def sample(schema):
            if 'enum' in schema:
                return schema['enum'][0]
            kind = schema['type']
            if kind == 'object':
                return {key: sample(schema['properties'][key]) for key in schema.get('required', [])}
            return {'array': [], 'string': 'fixture', 'boolean': False, 'integer': 1, 'number': 1.5}[kind]
        self.assertEqual(len(self.declarations), 129)
        for declaration in self.declarations:
            with self.subTest(name=declaration['name']):
                self.validate(declaration['name'], sample(declaration['parameters']), self.declarations)

    def test_aliases_normalize_without_changing_false_capabilities(self):
        original = {'project_name': 'fixture', 'files': [], 'run_immediately': False}
        name, result = self.validate('create_program', original, self.declarations)
        self.assertEqual(name, 'build_program')
        self.assertEqual(result, original)
        self.assertIsNot(result, original)
        self.assertEqual(self.validate('powershell', {'cmd': 'Write-Output fixture'}, self.declarations),
                         ('execute_powershell', {'command': 'Write-Output fixture'}))
        self.assertEqual(self.validate('query_large_knowledge_db', {'sql': 'SELECT 1'}, self.declarations),
                         ('query_large_knowledge_db', {'sql_query': 'SELECT 1'}))

    def test_conflicting_aliases_rejected(self):
        with self.assertRaises(self.error):
            self.validate('execute_powershell', {'command': 'Write-Output one', 'cmd': 'Write-Output two'}, self.declarations)

    def test_nonfinite_cycle_nonstring_keys_and_nonjson_types_rejected(self):
        cycle = {}; cycle['cycle'] = cycle
        for payload in ({'telemetry_payload': {'x': float('inf')}},
                        {'telemetry_payload': cycle}, {'telemetry_payload': {7: 'x'}},
                        {'telemetry_payload': {'x': b'bytes'}}):
            with self.subTest(payload_type=type(payload['telemetry_payload'])):
                with self.assertRaises(self.error):
                    self.validate('unknown_tool', payload, self.declarations)

    def test_depth_limit_and_oversized_envelopes_rejected(self):
        from tools.tool_call_contract import MAX_DEPTH, MAX_ENVELOPE_BYTES, parse_tool_call
        payload = '"x"'
        for _ in range(MAX_DEPTH + 1):
            payload = '[' + payload + ']'
        self.assertEqual(parse_tool_call('{"name":"list_programs","arguments":{"x":' + payload + '}}'), (None, None))
        self.assertEqual(parse_tool_call(' ' * (MAX_ENVELOPE_BYTES + 1)), (None, None))

    def test_dynamic_payload_remains_json_open_and_enum_is_enforced(self):
        declaration = [{'name': 'fixture_tool', 'parameters': {'type': 'object', 'properties':
                       {'metadata': {'type': 'object'}, 'mode': {'type': 'string', 'enum': ['read']}}}}]
        value = {'metadata': {'arbitrary': {'nested': [1, False, None]}}, 'mode': 'read'}
        self.assertEqual(self.validate('fixture_tool', value, declaration), ('fixture_tool', value))
        with self.assertRaises(self.error):
            self.validate('fixture_tool', {'mode': 'write'}, declaration)

    def test_integer_fields_do_not_accept_boolean_capabilities(self):
        with self.assertRaises(self.error):
            self.validate('execute_powershell', {'command': 'Write-Output fixture', 'timeout_seconds': True}, self.declarations)


class RegistrySandboxBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()
        self.folder = tempfile.TemporaryDirectory(prefix='tool_registry_guest_fixture_')
        self.addCleanup(self.folder.cleanup)
        self.script = Path(self.folder.name) / 'candidate.py'
        self.script.write_text('value = 1\n', encoding='utf-8')
        self.registry.execute_tool.__globals__['SANDBOX_DIR'] = self.folder.name
        self.calls = []
        self.response = SimpleNamespace(status='PASSED', exit_code=0, stdout='fixture only', stderr='', patch_applied=False, isolation_verified=True)
        owner = self
        class Runner:
            def __init__(self, **kwargs):
                pass
            def execute_in_sandbox(self, *args, **kwargs):
                owner.calls.append((args, kwargs))
                return owner.response
        module = ModuleType('core.ide_orchestrator.sandbox_runner')
        module.SubprocessSandboxRunner = Runner
        patches = patch.dict(sys.modules, {'core.ide_orchestrator.sandbox_runner': module})
        patches.start(); self.addCleanup(patches.stop)

    def execute(self, filename='candidate.py'):
        with patch('subprocess.run', side_effect=AssertionError('host execution forbidden')), \
             patch('urllib.request.urlopen', side_effect=AssertionError('model request forbidden')):
            return self.registry.execute_tool('execute_sandbox_script', {'filename': filename})

    def test_registry_delegates_to_verified_guest_without_host_or_model_fallback(self):
        before = self.script.read_bytes()
        result = self.execute()
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['isolation_verified'])
        self.assertFalse(result['patch_applied'])
        self.assertEqual(self.calls[0][0][1], before.decode('utf-8'))
        self.assertEqual(self.calls[0][1]['timeout_sec'], 15)
        self.assertEqual(self.script.read_bytes(), before)

    def test_isolation_unavailable_is_held_without_fallback(self):
        self.response.status = 'ISOLATION_UNAVAILABLE'
        self.response.isolation_verified = False
        self.response.exit_code = -1
        result = self.execute()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_code'], 'ISOLATION_UNAVAILABLE')
        self.assertEqual(len(self.calls), 1)

    def test_unverified_pass_never_claims_success(self):
        self.response.isolation_verified = False
        result = self.execute()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_code'], 'ISOLATION_UNAVAILABLE')

    def test_paths_and_nonpython_candidates_rejected_before_guest_dispatch(self):
        for name in ('../candidate.py', 'C:/candidate.py', 'candidate.txt', '_runner_entrypoint.py'):
            with self.subTest(name=name):
                self.assertEqual(self.execute(name)['status'], 'error')
        self.assertEqual(self.calls, [])

    def test_actual_runner_with_trusted_host_selected_is_held_by_registry(self):
        # This imports only the inert compatibility adapter, never a provider.
        import importlib.util
        path = ROOT / 'backend/core/ide_orchestrator/sandbox_runner.py'
        spec = importlib.util.spec_from_file_location('_aibs_contract_actual_guest_adapter', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {spec.name: module}):
            spec.loader.exec_module(module)
            with patch.dict(sys.modules, {'core.ide_orchestrator.sandbox_runner': module}), \
                 patch.dict('os.environ', {'AI_BS_EXECUTION_BACKEND': 'trusted_host'}):
                result = self.execute()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_code'], 'ISOLATION_UNAVAILABLE')
        self.assertFalse(result['isolation_verified'])
        self.assertFalse(result['patch_applied'])


if __name__ == '__main__':
    unittest.main()
