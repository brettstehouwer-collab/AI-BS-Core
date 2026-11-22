"""Read Python syntax without importing applications or asserting live coverage.

Only route literals and symbol names are retained, never bodies or call arguments.
Conditional mounts, duplicate registrations and dynamic expressions need review.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

MAX_SOURCE_BYTES = 8 * 1024 * 1024
METHODS = {'get','post','put','patch','delete','options','head','websocket','api_route'}
SINKS = {'subprocess.run','subprocess.Popen','subprocess.call','subprocess.check_output',
         'subprocess.check_call','os.system','os.popen','eval','exec','compile',
         'sqlite3.connect','httpx.get','httpx.post','httpx.request','requests.get',
         'requests.post','requests.request'}


def _symbol(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _symbol(node.value)
        return parent + '.' + node.attr if parent else None
    return None


def _string(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value,str) else None


def _dependencies(node):
    names = set()
    for child in ast.walk(node):
        if (isinstance(child,ast.Call) and _symbol(child.func) in {'Depends','fastapi.Depends'}
                and child.args):
            symbol = _symbol(child.args[0])
            if symbol: names.add(symbol)
    return sorted(names)


def inspect_source(path, root):
    """Inventory a bounded file beneath root; parse failures remain explicit."""
    root, path = Path(root).absolute(), Path(path).absolute()
    if not path.is_relative_to(root):
        raise ValueError('Source is outside the selected inventory root')
    if any(p.is_symlink() or getattr(p,'is_junction',lambda:False)()
           for p in (path,*path.parents)):
        raise ValueError('Redirected inventory source is not admitted')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Resolved source is outside the inventory root')
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError('Source exceeds the inventory size limit')
    raw = path.read_bytes()
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError('Source grew beyond the inventory size limit')
    report = {'file':path.relative_to(root).as_posix(),'bytes':len(raw),
              'sha256':hashlib.sha256(raw).hexdigest(),'parse_status':'ok',
              'runtime_registration_verified':False,'routes':[],'mounts':[],
              'candidate_sinks':[],'duplicate_source_groups':[]}
    try:
        tree = ast.parse(raw.decode('utf-8-sig'))
    except (SyntaxError,UnicodeError,RecursionError) as error:
        report.update(parse_status='error',error_type=type(error).__name__)
        return report
    prefixes = {}
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Call):
            if _symbol(node.value.func) in {'APIRouter','fastapi.APIRouter'}:
                prefix = next((_string(k.value) for k in node.value.keywords if k.arg=='prefix'),'')
                for target in node.targets:
                    name = _symbol(target)
                    if name: prefixes[name] = prefix

    def visit(node, context):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if not isinstance(decorator,ast.Call) or not isinstance(decorator.func,ast.Attribute):
                    continue
                method = decorator.func.attr
                owner = _symbol(decorator.func.value)
                if method not in METHODS or not owner: continue
                route = _string(decorator.args[0]) if decorator.args else None
                if route is None:
                    route = next((_string(k.value) for k in decorator.keywords if k.arg=='path'),None)
                methods = [method.upper()]
                unresolved = route is None
                if method=='api_route':
                    values = next((k.value for k in decorator.keywords if k.arg=='methods'),None)
                    methods = ([_string(x) for x in values.elts]
                               if isinstance(values,(ast.List,ast.Tuple)) else [])
                    unresolved = unresolved or not methods or any(x is None for x in methods)
                prefix = prefixes.get(owner,'')
                unresolved = unresolved or prefix is None
                report['routes'].append({'line':node.lineno,'handler':node.name,'owner_symbol':owner,
                    'methods':methods,'declared_path':route,
                    'source_path':prefix+route if prefix is not None and route is not None else None,
                    'dependency_symbols':sorted(set(_dependencies(node.args)+_dependencies(decorator))),
                    'context':context,'unresolved':unresolved,'authorization_verified':False})
        if isinstance(node,ast.Call):
            name = _symbol(node.func)
            if name and name.endswith('.include_router'):
                report['mounts'].append({'line':node.lineno,'target_symbol':name,
                    'router_symbol':_symbol(node.args[0]) if node.args else None,
                    'prefix':next((_string(k.value) for k in node.keywords if k.arg=='prefix'),''),
                    'dependency_symbols':_dependencies(node),'context':context})
            if name in SINKS:
                report['candidate_sinks'].append({'line':node.lineno,'call':name,
                    'context':context,'taint_or_exploitability_verified':False})
        extra = []
        if isinstance(node,ast.If): extra=['if']
        elif isinstance(node,ast.Try): extra=['try']
        elif isinstance(node,ast.ExceptHandler): extra=['except']
        elif isinstance(node,(ast.For,ast.AsyncFor,ast.While)): extra=['loop']
        elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): extra=['function:'+node.name]
        elif isinstance(node,ast.ClassDef): extra=['class:'+node.name]
        for child in ast.iter_child_nodes(node): visit(child,context+extra)

    visit(tree,[])
    groups = {}
    for route in report['routes']:
        for method in route['methods']:
            if route['source_path'] is not None:
                groups.setdefault((route['owner_symbol'],method,route['source_path']),[]).append(route['handler'])
    report['duplicate_source_groups']=[handlers for handlers in groups.values() if len(handlers)>1]
    return report
