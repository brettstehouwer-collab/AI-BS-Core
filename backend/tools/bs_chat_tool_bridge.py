"""Opt-in, authenticated read-only diagnostics. Importing performs no I/O."""
from pathlib import Path, PurePosixPath
import hashlib
import importlib.util
import os
import shutil
import sqlite3
import stat

from core.personal_memory_scope import current_memory_principal


class BSChatToolBridge:
    """Construct only in trusted task code; approved paths are exact files."""

    def __init__(self, root=Path('C:/AI-BS'), approved_diff_paths=(), batch_status_provider=None,
                 crypto_market_provider=None, crypto_trial_registry=None, crypto_preparation_reader=None):
        self.root = Path(root).absolute()
        self.approved = frozenset(self._relative(p) for p in approved_diff_paths)
        self.batch_status_provider = batch_status_provider
        self.crypto_market_provider = crypto_market_provider
        self.crypto_trial_registry = crypto_trial_registry
        self.crypto_preparation_reader = crypto_preparation_reader

    @staticmethod
    def _relative(value):
        if type(value) is not str or not value or '\\' in value or ':' in value:
            raise ValueError('Invalid relative file')
        parts = PurePosixPath(value).parts
        if (value != '/'.join(parts) or '..' in parts or value.startswith('/')
                or any(p.startswith('.') for p in parts)
                or any(word in value.lower() for word in
                       ('vault', 'private', 'credential', 'secret', 'manuscript', 'personal', 'backup'))
                or Path(value).suffix.lower() in ('.db', '.sqlite', '.sqlite3', '.pem', '.key')):
            raise ValueError('Unavailable file')
        return value

    def _path(self, relative, allow_missing=False):
        target = self.root / relative
        for part in (self.root, *target.parents):
            if part == self.root.parent:
                break
            if part.exists() and (part.is_symlink() or
                    getattr(part.lstat(), 'st_file_attributes', 0) & 0x400):
                raise ValueError('Redirected path')
        if target.exists():
            info = target.lstat()
            if (not stat.S_ISREG(info.st_mode) or target.is_symlink() or info.st_nlink != 1
                    or getattr(info, 'st_file_attributes', 0) & 0x400):
                raise ValueError('Unavailable file')
        elif not allow_missing:
            raise ValueError('Missing file')
        if not target.resolve().is_relative_to(self.root.resolve()):
            raise ValueError('Path escape')
        return target

    @staticmethod
    def _authorize():
        if current_memory_principal() is None:
            raise PermissionError('Verified caller required')

    def execute_tool(self, tool_name, args):
        try:
            self._authorize()
            allowed = {'run_coding_smoke': {'max_checks'}, 'verify_sqlite_wal': set(),
                       'inspect_source_diff': {'path'}, 'check_service_health': {'service'},
                       'inspect_database_schema': {'database'}, 'discover_databases': set(),
                       'process_batch_status': set(),
                       'get_crypto_preparation_status': set(),
                       'get_crypto_trial_status': set(),
                       'get_crypto_protective_review': set(),
                       'preview_crypto_spot': {'budget_usdt', 'stop_percent', 'target_percent',
                           'max_exposure_usdt', 'daily_loss_budget_usdt', 'entry_fee_bps', 'exit_fee_bps',
                           'stop_type', 'trigger_reference_type', 'stop_limit_price'}}
            if type(tool_name) is not str or tool_name not in allowed or type(args) is not dict:
                raise ValueError('Invalid invocation')
            if not set(args).issubset(allowed[tool_name]):
                raise ValueError('Unexpected argument')
            return getattr(self, tool_name)(**args)
        except PermissionError:
            return {'status': 'denied'}
        except Exception:
            return {'status': 'error', 'error': 'diagnostic_unavailable'}

    def get_crypto_preparation_status(self):
        """Review dated selected preparation only; never obtain credentials or initialize."""
        self._authorize()
        from core.crypto_preparation_status import PreparationStatusReader,validate_preparation_status
        reader=self.crypto_preparation_reader
        if reader is None:reader=PreparationStatusReader()
        return validate_preparation_status(reader.status())

    def get_crypto_trial_status(self):
        """Read only a server-selected registered runtime; never create or reserve."""
        self._authorize()
        from core.crypto_trial_status_contract import validate_trial_status
        registry=self.crypto_trial_registry
        if registry is None:
            from core.crypto_trial_registry import get_default_registry
            registry=get_default_registry()
        return validate_trial_status(registry.status())

    def get_crypto_protective_review(self):
        """Read retained protection evidence only; never replay or submit."""
        self._authorize()
        from core.crypto_protective_review_contract import validate_protective_review
        registry=self.crypto_trial_registry
        if registry is None:
            from core.crypto_trial_registry import get_default_registry
            registry=get_default_registry()
        return validate_protective_review(registry.protective_review())

    @staticmethod
    def _public_crypto_market():
        """Two bounded anonymous GETs, fixed origin; no credential/environment use."""
        import httpx
        from datetime import datetime, timezone
        from core.crypto_com_acknowledgements import _json
        results = {}
        with httpx.Client(trust_env=False, follow_redirects=False, timeout=10) as client:
            for method in ('get-instruments', 'get-book'):
                params = {'instrument_name': 'CRO_USDT', 'depth': 10} if method == 'get-book' else {}
                raw = bytearray()
                with client.stream('GET', 'https://api.crypto.com/exchange/v1/public/' + method, params=params) as response:
                    if response.status_code != 200:
                        raise ValueError('Public market observation unavailable')
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 2 * 1024 * 1024:
                            raise ValueError('Public market response exceeds bound')
                data = _json(bytes(raw))
                if not isinstance(data, dict) or type(data.get('code')) is not int or data['code'] != 0:
                    raise ValueError('Public market response unavailable')
                results[method] = data['result']['data']
        instruments = [row for row in results['get-instruments'] if row.get('symbol') == 'CRO_USDT']
        if len(instruments) != 1 or instruments[0].get('tradable') is not True or len(results['get-book']) != 1:
            raise ValueError('Spot instrument unavailable')
        instrument, book = instruments[0], results['get-book'][0]
        return {'bid': book['bids'][0][0], 'ask': book['asks'][0][0],
                'quantity_step': instrument['qty_tick_size'], 'price_tick': instrument['price_tick_size'],
                'observed_at_utc': datetime.now(timezone.utc).isoformat()}

    def preview_crypto_spot(self, budget_usdt='2', stop_percent='2', target_percent=None,
                            max_exposure_usdt=None, daily_loss_budget_usdt='1',
                            entry_fee_bps='25', exit_fee_bps='50', stop_type='STOP_LOSS',
                            trigger_reference_type='LAST_PRICE', stop_limit_price=None):
        """Public-market arithmetic; supplied/default rates are never account facts."""
        self._authorize()
        from decimal import localcontext, ROUND_CEILING
        from core.crypto_execution_controls import number, text_decimal
        from core.crypto_spot_preview import preview_cro_spot
        if (type(stop_type) is not str or stop_type not in ('STOP_LOSS','STOP_LIMIT')
                or type(trigger_reference_type) is not str
                or trigger_reference_type not in ('LAST_PRICE','MARK_PRICE','INDEX_PRICE')
                or (stop_limit_price is not None and (type(stop_limit_price) is not str
                    or number(stop_limit_price) <= 0 or stop_type != 'STOP_LIMIT'))):
            raise ValueError('Explicit supported draft stop choices required')
        arguments = {'budget': budget_usdt, 'stop': stop_percent, 'target': target_percent,
                     'exposure': max_exposure_usdt, 'daily': daily_loss_budget_usdt,
                     'entry_fee': entry_fee_bps, 'exit_fee': exit_fee_bps}
        for name, value in arguments.items():
            if value is not None and (type(value) is not str or number(value) < 0):
                raise ValueError('Explicit decimal strings required')
        if (number(budget_usdt) <= 0 or not 0 < number(stop_percent) < 100
                or (target_percent is not None and number(target_percent) <= 0)
                or number(entry_fee_bps) >= 10000 or number(exit_fee_bps) >= 10000
                or (max_exposure_usdt is not None and number(max_exposure_usdt) <= 0)
                or number(daily_loss_budget_usdt) <= 0):
            raise ValueError('Invalid preview assumptions')
        observed = (self.crypto_market_provider or self._public_crypto_market)()
        market = {name: observed[name] for name in ('bid', 'ask', 'quantity_step', 'price_tick', 'observed_at_utc')}
        if type(market['observed_at_utc']) is not str or len(market['observed_at_utc']) > 100:
            raise ValueError('Observation timestamp unavailable')
        with localcontext() as context:
            context.prec = 96
            bid, tick = number(market['bid']), number(market['price_tick'])
            if tick <= 0:
                raise ValueError('Positive price tick required')
            def rounded(price):
                return text_decimal((price / tick).to_integral_value(rounding=ROUND_CEILING) * tick)
            stop = rounded(bid * (1 - number(stop_percent) / 100))
            target = rounded(bid * (1 + number(target_percent) / 100)) if target_percent is not None else None
        preview = preview_cro_spot(budget_usdt=budget_usdt, bid=market['bid'], ask=market['ask'],
            quantity_step=market['quantity_step'], price_tick=market['price_tick'],
            minimum_notional_usd='1', usdt_usd_index='1', entry_fee_bps=entry_fee_bps,
            exit_fee_bps=exit_fee_bps, stop_price=stop, target_price=target,
            max_exposure_usdt=max_exposure_usdt, daily_loss_budget_usdt=daily_loss_budget_usdt)
        from core.crypto_spot_protection import review_cro_protection
        return {'status': 'preview', 'preview': preview, 'market': market,
                'protection_review': review_cro_protection(preview, stop_type=stop_type,
                    trigger_reference_type=trigger_reference_type, stop_limit_price=stop_limit_price,
                    price_tick=market['price_tick'], minimum_notional_usd='1', usdt_usd_index='1'),
                'fee_rate_source': 'SCENARIO_INPUTS_NOT_AUTHENTICATED_ACCOUNT_RATES',
                'minimum_rule': 'US$1_EQUIVALENT_RULE_USDT_USD_INDEX_ASSUMED_1',
                'account_accessed': False, 'orders_sent': 0}

    def run_coding_smoke(self, max_checks=15):
        self._authorize()
        if type(max_checks) is not int or not 12 <= max_checks <= 15:
            raise ValueError('The existing profile has twelve checks')
        script = self._path('scripts/check_coding_candidate.py')
        spec = importlib.util.spec_from_file_location('_aibs_candidate_diagnostics', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checks = module.run_checks()
        if type(checks) is not list or len(checks) != 12:
            raise ValueError('Unexpected profile')
        passed = sum(type(c) is dict and c.get('passed') is True for c in checks)
        return {'status': 'success' if passed == 12 else 'failed',
                'check_count': 12, 'passed_count': passed, 'failed_count': 12 - passed}

    def verify_sqlite_wal(self):
        self._authorize()
        observations = []
        for name, relative in (('backend_master', 'backend/aibs_master.db'),
                               ('cdz_audit', 'database/aibs_master.db')):
            observation = {'database': name, 'status': 'unavailable'}
            try:
                path = self._path(relative)
                connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)
                try:
                    mode = connection.execute('PRAGMA journal_mode').fetchone()[0]
                    sync = connection.execute('PRAGMA synchronous').fetchone()[0]
                finally:
                    connection.close()
                observation.update(status='observed', journal_mode=mode if mode in
                                   ('wal', 'delete', 'truncate', 'persist', 'memory', 'off') else 'unknown',
                                   synchronous=sync if type(sync) is int and 0 <= sync <= 3 else None)
            except Exception:
                pass
            observations.append(observation)
        return {'status': 'success' if all(o['status'] == 'observed' for o in observations)
                else 'incomplete', 'scope': 'new_read_only_connections_not_live_application_settings',
                'observations': observations}

    def _git(self, arguments):
        from core.coding_process import run_bounded_check
        git = shutil.which('git')
        if not git:
            raise ValueError('Git unavailable')
        result = run_bounded_check([git, '-c', 'core.fsmonitor=false',
                                   '-c', 'core.hooksPath=', *arguments],
                                  cwd=str(self.root), env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0',
                                  'GIT_TERMINAL_PROMPT': '0'}, timeout_seconds=5, output_limit=16384)
        if result.get('error'):
            raise ValueError('Git diagnostic failed')
        return result

    def discover_databases(self):
        """Enumerate only the two registered files; no drive or resource scan."""
        self._authorize()
        results = []
        for name, relative in (('backend_master', 'backend/aibs_master.db'),
                               ('cdz_audit', 'database/aibs_master.db')):
            try:
                self._path(relative)
                status = 'available'
            except Exception:
                status = 'unavailable'
            results.append({'database': name, 'status': status})
        return {'status': 'success', 'scope': 'registered_allowlist_only', 'databases': results}

    def inspect_database_schema(self, database='backend_master'):
        self._authorize()
        databases = {'backend_master': 'backend/aibs_master.db', 'cdz_audit': 'database/aibs_master.db'}
        if type(database) is not str or database not in databases:
            raise ValueError('Unregistered database')
        path = self._path(databases[database])
        import time
        deadline = time.monotonic() + 1
        connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)
        try:
            connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 100)
            # Limits apply inside SQLite before materializing results. No row values.
            rows = connection.execute(
                "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' LIMIT 33").fetchall()
            tables = []
            for (name,) in rows[:32]:
                if type(name) is not str or len(name) > 128:
                    continue
                columns = connection.execute(
                    'SELECT name, type FROM pragma_table_info(?) LIMIT 65', (name,)).fetchall()
                tables.append({'name': name, 'columns': [
                    {'name': str(n)[:128], 'type': str(t)[:64]} for n, t in columns[:64]],
                    'columns_truncated': len(columns) > 64})
            return {'status': 'success', 'database': database, 'tables': tables,
                    'tables_truncated': len(rows) > 32, 'row_values_exposed': False}
        finally:
            connection.close()

    def process_batch_status(self):
        self._authorize()
        if self.batch_status_provider is None:
            return {'status': 'unavailable', 'reason': 'no_existing_controller_bound'}
        value = self.batch_status_provider()
        if type(value) is not dict:
            raise ValueError('Invalid controller observation')
        # Never expose command lines, owner identities, exception text or task payloads.
        counts = {key: value[key] for key in ('queued', 'running', 'completed', 'failed')
                  if type(value.get(key)) is int and 0 <= value[key] <= 1000000}
        return {'status': 'observed', 'counts': counts}

    def inspect_source_diff(self, path):
        self._authorize()
        relative = self._relative(path)
        if relative not in self.approved:
            raise PermissionError('Exact task file approval required')
        target = self._path(relative, allow_missing=True)
        if target.exists() and target.stat().st_size > 262144:
            raise ValueError('File exceeds diagnostic limit')
        tracked = self._git(['ls-files', '--error-unmatch', '--', relative])
        if tracked['returncode'] not in (0, 1):
            raise ValueError('Git diagnostic failed')
        if tracked['returncode'] == 1:
            state = 'untracked' if target.exists() else 'absent'
        else:
            result = self._git(['diff', '--no-ext-diff', '--no-textconv', '--numstat',
                                'HEAD', '--', relative])
            if result['returncode'] != 0:
                raise ValueError('Git diagnostic failed')
            state = 'deleted' if not target.exists() else ('modified' if result['stdout'] else 'unmodified')
        return {'status': 'success', 'file_state': state,
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None,
                'content_exposed': False}

    def check_service_health(self, service='backend'):
        self._authorize()
        endpoints = {'backend': 'http://127.0.0.1:8080/health',
                     'coding_candidate': 'http://127.0.0.1:18780/health',
                     'browser': 'http://127.0.0.1:18773/'}
        if type(service) is not str or service not in endpoints:
            raise ValueError('Unknown service')
        import httpx
        try:
            with httpx.Client(trust_env=False, follow_redirects=False, timeout=2.0) as client:
                with client.stream('GET', endpoints[service]) as response:
                    code = response.status_code
            return {'status': 'success' if code == 200 else 'failed', 'service': service,
                    'http_status': code, 'scope': 'http_endpoint_observation'}
        except Exception:
            return {'status': 'unavailable', 'service': service}


bs_chat_bridge = BSChatToolBridge()
