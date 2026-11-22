"""Actual-only Crypto.com replacement-key verifier; no order or live enable path.

Only REPLACEMENT_API_KEY/REPLACEMENT_API_SECRET in this child process are read.
No fallback credentials, .env, injected transport, test clock or mock proof exists.
All original financial responses and linkable hashes remain local DPAPI evidence.
"""
import argparse
import base64
from contextlib import ExitStack
from decimal import Decimal,InvalidOperation
import json
import os
from pathlib import Path
import re
import sys
import time
from uuid import UUID,uuid4

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'saved_data/crypto_credential_preparation_registry'


def receipt(status,mode,**fields):
    record=dict(status=status,mode=mode,credential_verified=False,bound=False,
        account_identity_verified=False,native_order_accepted=False,live_dispatch_enabled=False,
        ready_for_live=False,orders_sent=0,verification_kind='NOT_EXECUTED')
    record.update(fields)
    return record


class _Parser(argparse.ArgumentParser):
    def error(self,message):
        # Unknown secret-like command arguments must never be echoed by argparse.
        print(json.dumps(receipt('INVALID_ARGUMENTS','none')))
        raise SystemExit(2)


def arguments():
    parser=_Parser(description='Actual-only Crypto.com credential/current-state verification. Trading always remains held.')
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--probe-only',action='store_true',help='Read metadata and six current responses; do not bind a store.')
    modes.add_argument('--initialize-held',action='store_true',help='Initialize one canonical seed-only HELD local store if absent.')
    modes.add_argument('--verify-existing',action='store_true',help='Preflight an existing binding and expected opening snapshot, then read the same key scope.')
    modes.add_argument('--check-config',action='store_true',help='Check only child-process replacement configuration; never access network/storage.')
    parser.add_argument('--local-trial-uuid',help='Explicit LOCAL trial UUID, never an Exchange account UUID; required for probe/initialize.')
    parser.add_argument('--expected-snapshot-sha256',help='Existing immutable opening snapshot receipt SHA256; required for verify-existing.')
    parser.add_argument('--seed-usdt',help='Explicit local seed allocation; initialize-held only.')
    parser.add_argument('--max-entry-usdt',help='Explicit local entry cap; initialize-held only.')
    parser.add_argument('--daily-loss-usdt',help='Explicit local daily loss allowance; initialize-held only.')
    args=parser.parse_args()
    mode='probe-only' if args.probe_only else 'initialize-held' if args.initialize_held else 'verify-existing' if args.verify_existing else 'check-config'
    try:
        if args.probe_only or args.initialize_held:
            if type(args.local_trial_uuid) is not str or str(UUID(args.local_trial_uuid))!=args.local_trial_uuid:raise ValueError()
        elif args.local_trial_uuid is not None:raise ValueError()
        if args.verify_existing:
            value=args.expected_snapshot_sha256
            if (type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value) or len(set(value))==1
                    or value in ('0123456789abcdef'*4,'deadbeef'*8)):raise ValueError()
        elif args.expected_snapshot_sha256 is not None:raise ValueError()
        budgets=(args.seed_usdt,args.max_entry_usdt,args.daily_loss_usdt)
        if args.initialize_held:
            for value in budgets:
                if type(value) is not str or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?',value) or len(value)>100:raise ValueError()
                amount=Decimal(value)
                if not amount.is_finite() or not 0<amount<=Decimal('1e18'):raise ValueError()
            if Decimal(args.max_entry_usdt)<Decimal(args.seed_usdt):raise ValueError()
        elif any(value is not None for value in budgets):raise ValueError()
    except (ValueError,InvalidOperation,AttributeError):
        parser.error('Invalid explicit mode inputs')
    return args,mode


def _pair():
    pair=(os.environ.get('REPLACEMENT_API_KEY'),os.environ.get('REPLACEMENT_API_SECRET'))
    if any(type(value) is not str or not 1<=len(value)<=256 or value.strip()!=value for value in pair):return None
    return pair


def _private_archive(stack):
    # Existing saved_data only; never create an arbitrary/untrusted parent tree.
    saved=ROOT/'saved_data'
    if not saved.is_dir() or any(path.is_symlink() or getattr(path,'is_junction',lambda:False)()
            for path in (saved,*saved.parents)):
        raise ValueError('Protected local archive parent unavailable')
    from native_studio.screenplay_client import _private_recovery_directory
    from security.crypto_trial_root import TrialRootLease
    archive=saved/('crypto-replacement-evidence-'+uuid4().hex)
    # This existing creator pins the measured SID owner as well as the DACL.
    lease=TrialRootLease.create(saved,archive.name);stack.callback(lease.close)
    _private_recovery_directory(archive,saved)
    lease.validate()
    import win32crypt
    sequence=0
    def normalize(value):
        if type(value) is bytes:return {'base64_original_bytes':base64.b64encode(value).decode('ascii')}
        if type(value) is dict:return {key:normalize(item) for key,item in value.items()}
        if type(value) in (list,tuple):return [normalize(item) for item in value]
        return value
    def sink(value):
        nonlocal sequence
        lease.validate();sequence+=1
        payload=json.dumps(normalize(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        protected=win32crypt.CryptProtectData(payload,'AI-BS replacement private evidence',None,None,None,1)
        path=archive/('evidence-%04d.dpapi'%sequence)
        with path.open('xb') as stream:
            stream.write(protected);stream.flush();os.fsync(stream.fileno())
        lease.pin_file(path.name)
        if win32crypt.CryptUnprotectData(path.read_bytes(),None,None,None,1)[1]!=payload:
            raise ValueError('Private evidence readback failed')
        lease.validate()
    return sink


def main():
    args,mode=arguments();pair=_pair()
    if pair is None:
        print(json.dumps(receipt('MISSING_REPLACEMENT_CONFIGURATION',mode)))
        return 2
    if args.check_config:
        print(json.dumps(receipt('CONFIGURATION_PRESENT_NOT_VERIFIED',mode)))
        return 0
    # Imports and all filesystem/network work come AFTER explicit config guards.
    sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
    output=receipt('REFUSED',mode)
    try:
        import ctypes
        if os.name!='nt' or ROOT!=Path('C:/AI-BS') or not ctypes.windll.shell32.IsUserAnAdmin():
            raise ValueError('Verified local administrator required')
        from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
        from core.crypto_credential_preparation import read_credential_preparation,validate_preparation
        from core.crypto_current_snapshot import read_current_snapshot
        from core.crypto_credential_preparation_registry import CredentialPreparationRegistry
        from core.crypto_held_preparation_runtime import HeldPreparationRuntime
        from security.crypto_trial_root import TrialRootLease
        with ExitStack() as stack:
            principal_token=bind_memory_principal('local_admin');stack.callback(reset_memory_principal,principal_token)
            index=held=None
            if args.verify_existing:
                # Verify protected EXISTING metadata and immutable opening first.
                with TrialRootLease.open_for_locator(INDEX) as measured:
                    index=CredentialPreparationRegistry.open(INDEX,expected_identity=measured.identity)
                stack.callback(index.close)
                held=HeldPreparationRuntime.open(index);stack.callback(held.close)
                held.status()
                if held._binding['snapshot_receipt_sha256']!=args.expected_snapshot_sha256:
                    raise ValueError('Expected immutable opening snapshot differs')
                trial=index._record['preparation']['local_trial_uuid']
                selected=index._record['preparation']
            else:
                trial=args.local_trial_uuid
                if args.initialize_held:
                    try:INDEX.lstat()
                    except FileNotFoundError:pass
                    else:raise ValueError('Canonical selection already exists; no reset or overwrite')
            sink=_private_archive(stack)
            preparation=read_credential_preparation(local_trial_uuid=trial,
                credential_provider=lambda:pair,private_sink=sink)
            current=preparation.to_record()
            if args.verify_existing:
                # New key or rotated secret cannot rotate/adopt the selected store.
                validate_preparation(preparation,principal='local_admin',
                    credential_partition_sha256=selected['credential_partition_sha256'],
                    credential_generation_sha256=selected['credential_generation_sha256'],now_ms=time.time_ns()//1000000)
                index.register(preparation=preparation,
                    credential_partition_sha256=selected['credential_partition_sha256'],
                    credential_generation_sha256=selected['credential_generation_sha256'],now_ms=time.time_ns()//1000000)
            snapshot=read_current_snapshot(preparation=preparation,credential_provider=lambda:pair,private_sink=sink)
            if args.initialize_held:
                index=CredentialPreparationRegistry.create(INDEX.parent,INDEX.name,preparation=preparation,
                    credential_partition_sha256=current['credential_partition_sha256'],
                    credential_generation_sha256=current['credential_generation_sha256'],now_ms=time.time_ns()//1000000)
                stack.callback(index.close)
                held=HeldPreparationRuntime.create(index,preparation=preparation,snapshot=snapshot,
                    credential_partition_sha256=current['credential_partition_sha256'],
                    credential_generation_sha256=current['credential_generation_sha256'],
                    seed_budget_usdt=args.seed_usdt,max_entry_budget_usdt=args.max_entry_usdt,daily_loss_budget_usdt=args.daily_loss_usdt)
                stack.callback(held.close);held.status()
            elif args.verify_existing:held.status()
            status=('HELD_PREPARATION_INITIALIZED' if args.initialize_held else
                'EXISTING_HELD_BINDING_VERIFIED' if args.verify_existing else 'CREDENTIAL_READS_VERIFIED_NOT_BOUND')
            output=receipt(status,mode,credential_verified=True,bound=not args.probe_only,
                verification_kind='ACTUAL_TLS_READS',current_read_requests=7)
            sink({'kind':'PRIVATE_REPLACEMENT_VERIFICATION_RESULT','public_receipt':output,
                'preparation_receipt_sha256':current['receipt_sha256'],
                'snapshot_receipt_sha256':snapshot.to_record()['receipt_sha256']})
        print(json.dumps(output));return 0
    except Exception:
        # Never expose private paths, raw bodies, API keys, fingerprints or errors.
        print(json.dumps(receipt('REFUSED',mode)));return 1


if __name__=='__main__':raise SystemExit(main())
