"""Offline AST-only containment tests. Never imports the application or opens its stores."""
import ast
import builtins
import os
import asyncio
from pathlib import Path
from typing import Any, Optional, List, Dict
import unittest
from fastapi import HTTPException

ROOT = Path(os.environ.get('AIBS_FINANCIAL_FIXTURE_SOURCE_ROOT', 'C:/AI-BS'))
ROUTERS = [
    'backend/routers/phone_repair_router.py',
    'backend/commercial_gateway/storefront_router.py',
    'backend/routers/trading_router.py',
    'backend/routers/cro_ledger_router.py',
    'backend/modules/master_accounting/__init__.py',
]

def tree(path):
    return ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))

class GuardViolation(BaseException):
    pass

class Forbidden:
    def __getattr__(self, name):
        raise GuardViolation('Unowned operation reached dependency: ' + name)
    def __call__(self, *args, **kwargs):
        raise GuardViolation('Unowned operation reached dependency')


class BlockImports(ast.NodeTransformer):
    def visit_Import(self, node):
        return ast.copy_location(ast.Raise(exc=ast.Call(func=ast.Name(id='GuardViolation', ctx=ast.Load()), args=[ast.Constant('Handler attempted local import')], keywords=[])), node)
    visit_ImportFrom = visit_Import


def extract(path, name):
    node = next(n for n in ast.walk(tree(path)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    node.decorator_list = []
    # Annotations/default expressions are not handler behavior and must never execute.
    node.returns = None
    for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
        arg.annotation = None
    node.args.defaults = [ast.Constant(None) for n in node.args.defaults]
    node.args.kw_defaults = [ast.Constant(None) if n else None for n in node.args.kw_defaults]
    node = BlockImports().visit(node)
    def deny(*args, **kwargs):
        raise GuardViolation('Forbidden builtin/import/FS execution')
    safe_builtins = dict(vars(builtins))
    for key in ('__import__','open','exec','eval','compile','input','breakpoint'):
        safe_builtins[key] = deny
    ns = dict(HTTPException=HTTPException, GuardViolation=GuardViolation, LedgerIntegrityError=type('FixtureLedgerIntegrityError',(Exception,),{}))
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in ns and n.id not in safe_builtins:
            ns[n.id] = Forbidden()
    ns['__builtins__'] = safe_builtins
    ns['execution_status'] = lambda: {'status':'held'}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), path, 'exec'), ns)
    return ns[name]

class HarnessSafety(unittest.TestCase):
    def test_local_import_is_blocked_before_import_system(self):
        source = ast.parse('def fixture():\n    import socket\n    from pathlib import Path\n')
        transformed = ast.fix_missing_locations(BlockImports().visit(source))
        self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(transformed)))
        def import_denied(*args, **kwargs):
            self.fail('Transformed fixture reached Python import system')
        namespace = {'GuardViolation':GuardViolation,'__builtins__':dict(vars(builtins),__import__=import_denied)}
        exec(compile(transformed,'<synthetic-import-guard>','exec'),namespace)
        with self.assertRaises(GuardViolation):
            namespace['fixture']()

    def test_builtins_are_valid_and_effectful_operations_are_denied(self):
        fn = extract(ROUTERS[2], 'get_trade_ledger')
        safe = fn.__globals__['__builtins__']
        self.assertIs(safe['Exception'], Exception)
        self.assertIs(safe['str'], str)
        for name in ('open','__import__','exec','eval','compile'):
            with self.subTest(name=name):
                with self.assertRaises(GuardViolation):
                    safe[name]('never-open-or-import')
        self.assertIsInstance(fn.__globals__['Path'], Forbidden)
        with self.assertRaises(GuardViolation):
            fn.__globals__['Path']('never-open')

class LegacyPrivacy(unittest.TestCase):
    def test_every_sensitive_router_has_preparse_verified_admin_boundary(self):
        for path in ROUTERS:
            with self.subTest(path=path):
                calls = [n for n in ast.walk(tree(path)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'APIRouter']
                self.assertTrue(any(any(k.arg == 'route_class' and isinstance(k.value, ast.Name) and k.value.id == 'AdminHostControlRoute' for k in n.keywords) for n in calls))

    def test_import_does_not_initialize_legacy_databases(self):
        for path in ['backend/commercial_gateway/storefront_router.py','backend/core/cro_quantitative_ledger.py','backend/core/phone_repair_knowledge.py']:
            with self.subTest(path=path):
                calls = [c for n in tree(path).body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for c in ast.walk(n) if isinstance(c, ast.Call)]
                forbidden = {'init_db', 'init_schema', 'get_instance'}
                self.assertFalse(any((isinstance(c.func, ast.Name) and c.func.id in forbidden) or (isinstance(c.func, ast.Attribute) and c.func.attr in forbidden) for c in calls))

    def test_unowned_handlers_hold_before_any_dependency(self):
        cases = {
            ROUTERS[0]: [('get_repair_tickets',()),('create_repair_ticket',(Forbidden(),)),('update_ticket_status',(7,Forbidden()))],
            ROUTERS[1]: [('get_balance',()),('generate_content',(Forbidden(),)),('get_leads',()),('add_lead',(Forbidden(),))],
            ROUTERS[2]: [('get_trade_ledger',()),('get_wallet_balances',()),('get_kraken_balance',()),('get_kraken_open_orders',()),('get_kraken_trade_history',()),('get_kraken_deposit_address',())],
            ROUTERS[3]: [('get_trade_ledger',()),('record_trade',('BUY',1,2)),('get_price_history',()),('get_pattern_prediction',()),('record_live_snapshot',(1,))],
            ROUTERS[4]: [('draft_invoice',(Forbidden(),))],
        }
        for path, methods in cases.items():
            for name,args in methods:
                with self.subTest(path=path,handler=name):
                    fn = extract(path,name)
                    try:
                        asyncio.run(fn(*args))
                    except GuardViolation as exc:
                        self.fail(str(exc))
                    except HTTPException as exc:
                        self.assertEqual(exc.status_code,503)
                        self.assertNotIn('success',str(exc.detail).lower())
                    else:
                        self.fail('Unowned operation returned without held503')

    def test_repair_core_refuses_legacy_ticket_access(self):
        path='backend/core/phone_repair_knowledge.py'
        for name,args in [('create_repair_ticket',(Forbidden(),{})),('get_repair_tickets',(Forbidden(),)),('update_ticket_status',(Forbidden(),7,'Completed'))]:
            with self.subTest(handler=name):
                try:
                    extract(path,name)(*args)
                except GuardViolation as exc:
                    self.fail(str(exc))
                except RuntimeError:
                    pass
                else:
                    self.fail('Unowned repair core operation returned')

    def test_knowledge_constructor_does_not_seed_or_open_store(self):
        try:
            extract('backend/core/phone_repair_knowledge.py','__init__')(Forbidden())
        except GuardViolation as exc:
            self.fail(str(exc))

    def test_existing_store_connections_are_explicitly_read_only(self):
        for path,name in [('backend/core/phone_repair_knowledge.py','_get_connection'),('backend/core/cro_quantitative_ledger.py','get_db')]:
            with self.subTest(path=path):
                node=next(n for n in ast.walk(tree(path)) if isinstance(n,ast.FunctionDef) and n.name==name)
                self.assertTrue(any(isinstance(n,ast.Constant) and n.value=='?mode=ro' for n in ast.walk(node)))
                self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in {'makedirs','mkdir'} for n in ast.walk(node)))

    def test_explicit_legacy_schema_initializers_refuse_before_io(self):
        for path,name,args in [('backend/commercial_gateway/storefront_router.py','init_db',()),('backend/core/cro_quantitative_ledger.py','init_schema',()),('backend/core/phone_repair_knowledge.py','_init_db',(Forbidden(),))]:
            with self.subTest(path=path):
                try:
                    extract(path,name)(*args)
                except GuardViolation as exc:
                    self.fail(str(exc))
                except RuntimeError:
                    pass
                else:
                    self.fail('Implicit legacy schema initialization accepted')

    def test_cro_core_refuses_unowned_writes_before_connect(self):
        path='backend/core/cro_quantitative_ledger.py'
        for name,args in [('log_trade_entry',('BUY',1,2)),('log_price_snapshot',(1,)),('analyze_patterns_and_predict',(1,))]:
            with self.subTest(handler=name):
                fn = extract(path,name)
                try:
                    fn(*args)
                except GuardViolation as exc:
                    self.fail(str(exc))
                except (RuntimeError,HTTPException):
                    pass
                else:
                    self.fail('Unowned operation returned without hold')

if __name__ == '__main__':
    unittest.main(verbosity=2)
