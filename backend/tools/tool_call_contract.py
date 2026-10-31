"""Inert JSON and argument checks shared by model parsing and tool dispatch.

Validation describes the input contract, not authorization. Existing authentication,
execution holds and per-tool safety controls remain responsible for authorization.
No code repair, coercion, imports of tool implementations, or execution occurs here.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re


class ToolCallValidationError(ValueError):
    """An invalid envelope or arguments must never reach a tool implementation."""


MAX_ENVELOPE_BYTES = 2 * 1024 * 1024
MAX_ARGUMENT_BYTES = 8 * 1024 * 1024
MAX_DEPTH = 32
MAX_NODES = 100000
_NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,127}\Z')
_FENCE = re.compile(r'```(?:json)?\s*(\{[\s\S]*\})\s*```\Z', re.IGNORECASE)


def _aliases(groups):
    return {alias: canonical for canonical, names in groups.items() for alias in names}


# These are the existing model-parser aliases, retained in one place.
_MODEL_ALIASES = _aliases({
    'generate_comfy_image': ('generate_image', 'create_image', 'comfyui_image', 'draw_image', 'generate_photo'),
    'query_master_memory': ('query_memory', 'master_memory', 'search_memory'),
    'query_large_knowledge_db': ('query_database', 'query_db', 'sql_query'),
    'create_comfy_workflow': ('create_workflow', 'generate_workflow', 'generate_video', 'create_video'),
    'run_ecosystem_script': ('run_script', 'execute_script', 'exec_script', 'run_python', 'script_runner'),
    'run_ecosystem_command': ('run_command', 'execute_command', 'run_terminal', 'run_cmd', 'powershell', 'shell'),
    'manage_ecosystem_service': ('manage_service', 'service_manager', 'service_control'),
    'get_ecosystem_health': ('ecosystem_health', 'system_health', 'health_check', 'matrix_doctor'),
})
_DISPATCH_ALIASES = _aliases({
    'execute_powershell': ('run_powershell', 'powershell_command', 'exec_powershell', 'powershell'),
    'execute_bash': ('run_bash', 'bash_command', 'bash', 'execute_sh', 'sh'),
    'execute_pip': ('pip_install', 'run_pip', 'pip', 'execute_pip3', 'pip3'),
    'build_program': ('scaffold_program', 'create_program'),
    'build_project': ('execute_build', 'run_build', 'project_build'),
    'run_program': ('execute_program',),
    'list_programs': ('get_built_programs',),
})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ToolCallValidationError('Duplicate JSON object key.')
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ToolCallValidationError('Non-finite JSON number.')


def _json_tree(value, *, limit=MAX_ARGUMENT_BYTES):
    """Check Python callers as well as decoded JSON, including cycles and infinity."""
    nodes = 0
    ancestors = set()

    def walk(item, depth):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise ToolCallValidationError('Tool JSON exceeds structural limits.')
        kind = type(item)
        if kind in (dict, list):
            identity = id(item)
            if identity in ancestors:
                raise ToolCallValidationError('Tool JSON contains a cycle.')
            ancestors.add(identity)
            if kind is dict:
                for key, child in item.items():
                    if type(key) is not str:
                        raise ToolCallValidationError('Tool JSON object keys must be strings.')
                    walk(child, depth + 1)
            else:
                for child in item:
                    walk(child, depth + 1)
            ancestors.remove(identity)
        elif kind is float:
            if not math.isfinite(item):
                raise ToolCallValidationError('Non-finite tool number.')
        elif kind not in (str, int, bool, type(None)):
            raise ToolCallValidationError('Tool arguments must contain JSON values.')

    walk(value, 0)
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ToolCallValidationError('Invalid tool JSON encoding.') from exc
    if len(encoded) > limit:
        raise ToolCallValidationError('Tool JSON exceeds size limit.')


def parse_tool_call(content_text):
    """Accept one complete JSON envelope, optionally in one complete code fence.

    Embedded examples, trailing prose, multiple calls, duplicate keys and malformed
    argument containers are never repaired into an executable request.
    """
    if type(content_text) is not str:
        return None, None
    try:
        if len(content_text) > MAX_ENVELOPE_BYTES or len(content_text.encode('utf-8')) > MAX_ENVELOPE_BYTES:
            return None, None
        text = content_text.strip()
        if text.startswith('```'):
            match = _FENCE.fullmatch(text)
            if match is None:
                return None, None
            text = match.group(1).strip()
        data = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
        _json_tree(data, limit=MAX_ENVELOPE_BYTES)
        if type(data) is dict and set(data) == {'tool_call'}:
            data = data['tool_call']
        if type(data) is not dict or set(data) != {'name', 'arguments'}:
            return None, None
        name, arguments = data['name'], data['arguments']
        if type(name) is not str or _NAME.fullmatch(name) is None or type(arguments) is not dict:
            return None, None
        return _MODEL_ALIASES.get(name, name), arguments
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        return None, None


def _object(properties, required=()):
    return {'type': 'object', 'properties': properties, 'required': list(required)}


# Dispatch-only tools were already implemented but absent from LLM declarations.
# Keep them callable through their existing contracts without advertising new tools.
_INTERNAL_SCHEMAS = {
    'kraken_op': _object({
        'action': {'type': 'string', 'enum': ['balance', 'ticker', 'deposit_address', 'deposit', 'order', 'open_orders', 'orders', 'trades', 'history', 'cancel', 'status']},
        'symbol': {'type': 'string'}, 'asset': {'type': 'string'},
        'side': {'type': 'string', 'enum': ['buy', 'sell']},
        'type': {'type': 'string', 'enum': ['market', 'limit']},
        'amount': {'type': 'number'}, 'price': {'type': 'number'}, 'order_id': {'type': 'string'},
    }),
    'execute_bash': _object({'command': {'type': 'string'}, 'timeout_seconds': {'type': 'integer'}, 'distro': {'type': 'string'}, 'environment': {'type': 'string'}}, ['command']),
    'execute_pip': _object({'command': {'type': 'string'}, 'timeout_seconds': {'type': 'integer'}}, ['command']),
    'list_programs': _object({}),
    'render_media_pipeline_recipe': _object({'recipe': {'type': 'object'}, 'job_id': {'type': 'string'}}, ['recipe']),
    'resume_media_pipeline_recipe': _object({'job_id': {'type': 'string'}, 'recipe': {'type': 'object'}}, ['job_id']),
}

_EXTRA_PROPERTIES = {
    **{name: {'output_filename': {'type': 'string'}} for name in ('execute_headless_blender', 'convert_ebook', 'optimize_pdf_stream', 'process_dsp_filter', 'stretch_pitch_tempo')},
    'generate_comfy_image': {'video': {'type': 'boolean'}},
    'lookup_symbol': {'limit': {'type': 'integer'}, 'symbol_type': {'type': 'string'}},
    'save_pipeline_checkpoint': {'stage_name': {'type': 'string'}},
}
_ARGUMENT_ALIASES = {
    'execute_powershell': {'command': ('command_or_script', 'script', 'cmd')},
    'execute_bash': {'command': ('cmd', 'script')},
    'execute_pip': {'command': ('package', 'args')},
    'query_large_knowledge_db': {'sql_query': ('query', 'sql')},
    'reconstruct_scene': {'image_url': ('image_path',)},
    'detect_objects': {'image_url': ('image_path',)},
    'build_project': {'project_name_or_dir': ('project_name', 'project_dir')},
}


def _check_schema(value, schema, path='arguments'):
    expected = schema.get('type')
    kind = type(value)
    valid = {
        'object': kind is dict, 'array': kind is list, 'string': kind is str,
        'boolean': kind is bool, 'integer': kind is int,
        'number': kind in (int, float), 'null': value is None,
    }
    if expected is not None and not valid.get(expected, False):
        raise ToolCallValidationError(f'{path} must have type {expected}.')
    if 'enum' in schema and value not in schema['enum']:
        raise ToolCallValidationError(f'{path} is not a declared choice.')
    if kind is dict:
        properties = schema.get('properties')
        for required in schema.get('required', []):
            if required not in value:
                raise ToolCallValidationError(f'{path} is missing required field {required}.')
        for key, child in value.items():
            if properties is not None and key in properties:
                _check_schema(child, properties[key], f'{path}.{key}')
            elif schema.get('additionalProperties') is False or (properties is not None and 'additionalProperties' not in schema):
                # Named argument records are closed. Opaque payload/metadata
                # dictionaries with no properties remain intentionally open.
                raise ToolCallValidationError(f'{path} contains an undeclared field.')
            elif type(schema.get('additionalProperties')) is dict:
                _check_schema(child, schema['additionalProperties'], f'{path}.*')
    elif kind is list and 'items' in schema:
        for child in value:
            _check_schema(child, schema['items'], f'{path}[]')


def validate_tool_call(tool_name, arguments, declarations):
    """Return a fresh normalized call or raise before effectful tool imports."""
    if type(tool_name) is not str or _NAME.fullmatch(tool_name) is None:
        raise ToolCallValidationError('Invalid tool name.')
    if type(arguments) is not dict:
        raise ToolCallValidationError('Tool arguments must be an object.')
    _json_tree(arguments)
    name = _DISPATCH_ALIASES.get(tool_name, tool_name)
    declaration = next((item for item in declarations if item.get('name') == name), None)
    schema = deepcopy(declaration['parameters']) if declaration is not None else deepcopy(_INTERNAL_SCHEMAS.get(name))
    if schema is None:
        raise ToolCallValidationError('Unknown tool name.')
    schema.setdefault('properties', {}).update(_EXTRA_PROPERTIES.get(name, {}))
    normalized = deepcopy(arguments)
    for canonical, aliases in _ARGUMENT_ALIASES.get(name, {}).items():
        supplied = [key for key in (canonical, *aliases) if key in normalized]
        if supplied:
            first = normalized[supplied[0]]
            if any(normalized[key] != first for key in supplied[1:]):
                raise ToolCallValidationError('Conflicting argument aliases.')
            normalized[canonical] = first
            for alias in aliases:
                normalized.pop(alias, None)
    _check_schema(normalized, schema)
    return name, normalized
