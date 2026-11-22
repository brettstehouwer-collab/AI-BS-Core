"""Bounded authenticated coding API client; never executes project code locally."""
from __future__ import annotations
import re
from native_studio.local_connection import local_service_headers

ORIGIN = 'http://127.0.0.1:8080'
ROOT = '/api/chat/coding-tasks'


def coding_mode_enabled(environ):
    return environ.get('AI_BS_CODING_MODE', '').lower() in {'1', 'true'}


def identifier(value):
    if not isinstance(value, str) or re.fullmatch('[a-f0-9]{32}', value) is None:
        raise ValueError('Select a valid retained record ID.')
    return value


def preparation_payload(request_id, repository_id, objective, files, checks):
    """Build structured operator scope without interpreting shell text."""
    identifier(request_id)
    selected = []
    for role, text in files.items():
        for name in text.splitlines():
            name = name.strip().replace('\\', '/')
            if name:
                if role not in {'editable', 'verification', 'dependency'}:
                    raise ValueError('Invalid source role.')
                selected.append({'relative_path': name, 'role': role})
    if not objective.strip() or not 1 <= len(selected) <= 20 or not isinstance(checks, list) or not checks:
        raise ValueError('Enter an objective, selected files and checks.')
    return {'request_id': request_id, 'repository_id': repository_id, 'objective': objective.strip(),
            'files': selected, 'checks': checks}


class CodingModeService:
    def __init__(self, *, headers_provider=None, transport=None):
        self.headers_provider = headers_provider or local_service_headers
        self.transport = transport

    def request(self, method, suffix, payload=None):
        import httpx
        query_ok = re.fullmatch(r'/mode/executions\?limit=20(?:&cursor=[a-f0-9]{32})?', suffix) is not None
        if method not in {'GET', 'POST'} or not suffix.startswith('/') or '..' in suffix or '#' in suffix or ('?' in suffix and not query_ok):
            raise ValueError('Invalid coding API operation.')
        headers = dict(self.headers_provider())
        if not headers:
            raise RuntimeError('The private local connection is not ready.')
        with httpx.Client(base_url=ORIGIN, headers=headers, transport=self.transport,
                          trust_env=False, follow_redirects=False, timeout=httpx.Timeout(110, connect=5)) as client:
            with client.stream(method, ROOT + suffix, json=payload) as response:
                if response.status_code >= 400:
                    raise RuntimeError(f'Coding service returned HTTP{response.status_code}. Retained work was not replayed.')
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 2 * 1024 * 1024:
                        raise RuntimeError('Coding response exceeded the display bound; inspect retained records.')
        import json
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise RuntimeError('Coding service returned an invalid record.')
        return value
