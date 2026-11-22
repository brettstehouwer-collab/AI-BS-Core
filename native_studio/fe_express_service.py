"""FE Express client for the same service routes used by the web dashboard.

This module owns no databases, scrapers, financial engines or background loops.
Credentials come from an injected session provider; none are bundled.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Mapping
from urllib.parse import quote, urlsplit

import httpx
from native_studio.local_connection import LocalConnectionError, local_service_headers


class FEExpressServiceError(RuntimeError):
    pass


class FEExpressClient:
    PREFIX = '/api/v1/fe-express'

    def __init__(self, base_url: str = 'http://127.0.0.1:8080', *, headers_provider: Callable[[], Mapping[str, str]] | None = None, transport=None):
        parsed = urlsplit(base_url)
        if (parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/') or
                (parsed.scheme, parsed.netloc) not in {
                    ('http', '127.0.0.1:8080'), ('http', '127.0.0.1:8000'),
                    ('https', 'api.brettstehouwer.live')}):
            raise ValueError('An established AI-BS service origin is required')
        self.base_url = base_url.rstrip('/')
        self.headers_provider = headers_provider if headers_provider is not None else (lambda: local_service_headers(self.base_url))
        self.transport = transport

    def _request(self, method: str, path: str, *, params=None, payload=None) -> dict:
        try:
            with httpx.Client(base_url=self.base_url, timeout=12, trust_env=False, follow_redirects=False, transport=self.transport) as client:
                response = client.request(method, self.PREFIX + path, params=params, json=payload, headers=dict(self.headers_provider()))
            if response.status_code in (401, 403):
                raise FEExpressServiceError('The dispatch service rejected this connection. Desktop use does not require API key entry.')
            if response.status_code != 200:
                raise FEExpressServiceError(f'FE Express service returned HTTP {response.status_code}.')
            data = response.json()
            if not isinstance(data, dict) or data.get('success') is False:
                raise FEExpressServiceError('The FE Express service could not complete this request.')
            return data
        except FEExpressServiceError:
            raise
        except (httpx.HTTPError, ValueError, TypeError, LocalConnectionError):
            raise FEExpressServiceError('The FE Express service could not confirm the result. Refresh before retrying an action.') from None

    @staticmethod
    def _identifier(value) -> str:
        value = str(value or '').strip()
        if (not value or len(value) > 256 or value in ('.', '..') or
                any(char in value for char in '/\\') or any(ord(char) < 32 for char in value)):
            raise ValueError('A valid record identifier is required')
        return quote(value, safe='')

    def _rows(self, path: str, key: str, **params) -> list[dict]:
        data = self._request('GET', path, params=params or None)
        rows = data.get(key)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise FEExpressServiceError('The FE Express service returned an invalid data list.')
        return rows

    def get_active_dispatches(self):
        return self._rows('/active-dispatches', 'dispatches')

    def get_contractor_drivers(self):
        return self._rows('/drivers', 'drivers')

    def get_driver_settlements(self):
        return self._rows('/settlements', 'settlements')

    def _action(self, path, payload):
        data = self._request('POST', path, payload=payload)
        if data.get('success') is not True:
            raise FEExpressServiceError('The dispatch service did not confirm this action. Refresh before retrying.')
        return data

    def book_load(self, payload):
        return self._action('/book-load', payload)

    def update_load_accounting(self, dispatch_id, payload):
        return self._action(f'/dispatches/{self._identifier(dispatch_id)}/accounting', payload)

    def save_contractor_driver(self, payload):
        return self._action('/drivers', payload)

    def record_settlement(self, payload):
        return self._action('/settlements', payload)

    def find_backhauls(self, load_id, home_base):
        return self._rows(f'/loads/{self._identifier(load_id)}/backhauls', 'backhauls', home_base=home_base)

    def sync_public_loads(self, home_base):
        # Called only by the explicit Pull Live Loads action, never a timer.
        result = self._action('/scraper/sync-public-boards', {'home_base': home_base})
        count = result.get('loads_count')
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise FEExpressServiceError('The FE Express service did not confirm an imported load count.')
        return count

    def snapshot(self, home_base, quarter='2026-Q4') -> dict:
        """Read stored service state on workers; never scrape or mutate on refresh."""
        jobs = {
            'loads': lambda: self._rows('/loads', 'loads', limit=500),
            'dispatches': self.get_active_dispatches,
            'drivers': self.get_contractor_drivers,
            'settlements': self.get_driver_settlements,
            'status': lambda: self._request('GET', '/status'),
            'chains': lambda: self._rows('/triangulation-chains', 'chains', home=home_base),
            'ifta': lambda: self._request('GET', '/ifta/summary', params={'quarter': quarter}),
        }
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {key: pool.submit(fn) for key, fn in jobs.items()}
            result = {key: future.result() for key, future in futures.items()}
            names = sorted({row.get('broker_name', '') for row in result['loads'] if row.get('broker_name')})
            credits = {name: pool.submit(self._request, 'GET', '/brokers/credit', params={'broker_name': name}) for name in names}
            result['brokerCredits'] = {name: future.result().get('broker_credit', {}) for name, future in credits.items()}
        if any(not isinstance(profile, dict) for profile in result['brokerCredits'].values()):
            raise FEExpressServiceError('The FE Express service returned an invalid broker profile.')
        if not isinstance(result['ifta'].get('ifta_summary'), dict):
            raise FEExpressServiceError('The FE Express service did not provide an IFTA summary.')
        result['ifta'] = result['ifta']['ifta_summary']
        return result
