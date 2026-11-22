"""Twelve read-only live candidate checks; never starts services or inference."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


MAIN = 'http://127.0.0.1:8080'
COMPANION = 'http://127.0.0.1:18780'
BROWSER = 'http://127.0.0.1:18773'
CAPABILITIES = COMPANION + '/api/chat/coding-tasks/mode/capabilities'


def run_checks():
    import httpx

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    checks = []

    def check(name, operation):
        statuses = []

        def request(method, url, **kwargs):
            response = client.request(method, url, **kwargs)
            statuses.append(response.status_code)
            return response

        result = {'name': name, 'passed': False, 'http_statuses': statuses}
        try:
            result['passed'] = bool(operation(request))
        except Exception as error:
            result['error_class'] = type(error).__name__
        checks.append(result)

    auth = None
    auth_error = None
    try:
        from native_studio.local_connection import local_service_headers
        auth = local_service_headers(MAIN)
        if not auth:
            raise RuntimeError()
    except Exception as error:
        auth_error = error

    def authenticated():
        if auth_error is not None:
            raise auth_error
        return dict(auth)

    capability_response = None

    def existing_auth(request):
        nonlocal capability_response
        capability_response = request('GET', CAPABILITIES, headers=authenticated())
        return (capability_response.status_code == 200
                and capability_response.json().get('enabled') is True)

    def supported_backends(_request):
        if capability_response is None:
            authenticated()
            raise RuntimeError()
        return (capability_response.status_code == 200
                and capability_response.json().get('supported_execution_backends')
                == ['isolated', 'trusted_host'])

    def same_owner(request):
        response = request('GET', MAIN + '/api/chat/coding-tasks/preparations/identity',
                           headers=authenticated())
        if response.status_code != 200 or capability_response is None:
            return False
        owner = response.json().get('owner')
        return (capability_response.status_code == 200 and isinstance(owner, str)
                and bool(owner) and capability_response.json().get('owner') == owner)

    def module_route(request):
        response = request('GET', BROWSER + '/src/utils/codingModeClient.js')
        return (response.status_code == 200
                and 'http://127.0.0.1:18780/api/chat/coding-tasks/mode${suffix}' in response.text
                and "${selected.backendUrl.replace(/\\/$/, '')}/api/chat/coding-tasks/mode${suffix}" not in response.text)

    def preflight(request, origin, expected):
        response = request('OPTIONS', CAPABILITIES, headers={
            'Origin': origin, 'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'x-admin-key'})
        allowed = response.headers.get('access-control-allow-origin')
        return response.status_code == expected and (allowed == origin if expected == 200 else allowed is None)

    def cors_auth(request):
        headers = authenticated()
        headers['Origin'] = BROWSER
        response = request('GET', CAPABILITIES, headers=headers)
        return (response.status_code == 200
                and response.headers.get('access-control-allow-origin') == BROWSER)

    with httpx.Client(trust_env=False, follow_redirects=False, timeout=6.0) as client:
        check('main_health', lambda r: r('GET', MAIN + '/health').status_code == 200)
        check('candidate_health', lambda r: r('GET', COMPANION + '/health').status_code == 200)
        check('browser_root', lambda r: r('GET', BROWSER + '/').status_code == 200)
        check('browser_coding_mode_companion_route', module_route)
        check('anonymous_capabilities_forbidden', lambda r: r('GET', CAPABILITIES).status_code == 403)
        check('invalid_key_capabilities_forbidden', lambda r: r('GET', CAPABILITIES, headers={'X-Admin-Key': 'candidate-smoke-invalid-key'}).status_code == 403)
        check('existing_auth_capabilities_enabled', existing_auth)
        check('supported_execution_backends', supported_backends)
        # This check reuses the exact authenticated capability response.
        checks[-1]['http_statuses'] = ([capability_response.status_code]
                                      if capability_response is not None else [])
        check('candidate_owner_matches_main_identity', same_owner)
        check('allowed_browser_origin_preflight', lambda r: preflight(r, BROWSER, 200))
        check('unapproved_origin_preflight', lambda r: preflight(r, 'http://127.0.0.1:18774', 400))
        check('authenticated_browser_origin_capabilities', cors_auth)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = None
    try:
        # Reserve a new receipt before sending requests; never replace evidence.
        if args.output is not None:
            output = args.output.open('x', encoding='utf-8')
        checks = run_checks()
        passed = len(checks) == 12 and all(check['passed'] for check in checks)
        receipt = {'profile': 'coding_candidate_smoke', 'utc': datetime.now(timezone.utc).isoformat(),
                   'passed': passed, 'check_count': len(checks), 'checks': checks}
        code = 0 if passed else 1
    except Exception as error:
        receipt = {'profile': 'coding_candidate_smoke', 'passed': False,
                   'error_class': type(error).__name__}
        code = 1
    try:
        encoded = json.dumps(receipt, indent=2) + '\n'
        if output is not None:
            output.write(encoded)
            output.close()
    except Exception as error:
        encoded = json.dumps({'profile': 'coding_candidate_smoke', 'passed': False,
                              'error_class': type(error).__name__}) + '\n'
        code = 1
    sys.stdout.write(encoded)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
