"""Extract actual boundary functions without importing the commercial app/ML stack."""
import ast
import asyncio
import builtins
from pathlib import Path
import sqlite3
import tempfile
import hashlib
import os
import time
import unittest
from unittest.mock import Mock,patch
from fastapi import HTTPException
ROOT=Path(__file__).resolve().parents[2]

def functions(path,names,namespace):
    tree=ast.parse((ROOT/path).read_text(encoding='utf-8-sig'))
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    for node in nodes:node.decorator_list=[]
    # Postpone annotations to avoid importing unrelated API/model dependencies.
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),str(path),'exec'),namespace)
    return namespace

class AccessTests(unittest.TestCase):
    def test_legacy_paid_keys_and_receipt_only_schema_are_denied(self):
        import logging
        from typing import Optional,Dict,Any
        with tempfile.TemporaryDirectory(prefix='aibs-offline-key-') as folder:
            path=Path(folder)/'registry.sqlite'
            ns=functions(Path('backend/commercial_gateway/api_key_manager.py'),{'verify_api_key'},
                dict(sqlite3=sqlite3,os=os,hashlib=hashlib,time=time,Path=Path,Optional=Optional,Dict=Dict,Any=Any,
                     _hash_key=lambda key:key,USAGE_DB_PATH=str(path),TIER_SPECS={'sandbox':{}},logger=logging.getLogger('offline')))
            from contextlib import closing
            with closing(sqlite3.connect(path)) as conn:
                conn.execute('CREATE TABLE payment_events_v1(id INTEGER)'); conn.commit()
            self.assertIsNone(ns['verify_api_key']('fixture'))
            with closing(sqlite3.connect(path)) as conn:
                conn.execute('CREATE TABLE api_keys(key_hash TEXT,key_prefix TEXT,client_name TEXT,tier TEXT,expires_at REAL,is_active INTEGER,allowed_ips TEXT)')
                for tier in ['pro','enterprise','pass_1day']:
                    conn.execute('INSERT INTO api_keys VALUES(?,?,?,?,?,?,?)',(tier,'fixture','offline',tier,time.time()+3600,1,None))
                conn.commit()
            for tier in ['pro','enterprise','pass_1day']:self.assertIsNone(ns['verify_api_key'](tier))

    def test_chef_orders_never_accept_raw_cards_as_paid_or_dispatch(self):
        ns=functions(Path('backend/routers/chef_orders_router.py'),{'place_chef_order','dispatch_notifications_task'},dict(HTTPException=HTTPException))
        with self.assertRaises(HTTPException) as err:asyncio.run(ns['place_chef_order'](Mock(),Mock()))
        self.assertEqual(err.exception.status_code,503)
        with self.assertRaises(RuntimeError):ns['dispatch_notifications_task']({})
    def test_no_missing_invalid_or_development_key_fallback(self):
        from fastapi import Header,status
        verify=Mock(return_value=None)
        ns=functions(Path('backend/commercial_gateway/gateway_router.py'),{'authenticate_and_authorize'},
            dict(Header=Header,status=status,HTTPException=HTTPException,verify_api_key=verify,SecurityShield=Mock()))
        for token in (None,'bad','Bearer invalid'):
            with self.assertRaises(HTTPException):asyncio.run(ns['authenticate_and_authorize'](Mock(),token))
        self.assertLessEqual(verify.call_count,1)

    def test_public_paid_key_creation_and_upgrade_have_no_side_effect(self):
        ns=functions(Path('backend/commercial_gateway/gateway_router.py'),{'request_passkey','upgrade_passkey_tier'},dict(HTTPException=HTTPException))
        for function in ns['request_passkey'],ns['upgrade_passkey_tier']:
            # A regressed legacy implementation must never reach a real import/store.
            real_import=builtins.__import__
            def guarded(name,*args,**kwargs):
                if name.startswith('commercial_gateway'):raise AssertionError('Unexpected paid-key import')
                return real_import(name,*args,**kwargs)
            with patch('builtins.__import__',side_effect=guarded):
                with self.assertRaises(HTTPException) as err:asyncio.run(function(Mock()))
            self.assertEqual(err.exception.status_code,410)

    def test_key_manager_import_has_no_store_initialization_calls(self):
        tree=ast.parse((ROOT/'backend/commercial_gateway/api_key_manager.py').read_text(encoding='utf-8-sig'))
        self.assertFalse([n for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
            and isinstance(n.value.func,ast.Name) and n.value.func.id.startswith('init_')])
        init=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='init_usage_db')
        self.assertNotIn('INSERT OR REPLACE',ast.unparse(init))

    def test_financial_imports_never_initialize_stores_or_open_provider_sessions(self):
        import subprocess,sys
        code='''
import sys,sqlite3,socket
sys.path.insert(0,'backend')
from unittest.mock import patch
with patch.object(sqlite3,'connect',side_effect=AssertionError('Import attempted DB access')), patch.object(socket,'create_connection',side_effect=AssertionError('Import attempted network')):
    import core.payment_receipts
    import modules.accounting_router
    import commercial_gateway.billing_provisioner
    import commercial_gateway.api_key_manager
    import routers.chef_orders_router
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr[-3000:])

if __name__=='__main__':unittest.main()
