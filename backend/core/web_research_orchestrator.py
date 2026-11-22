"""Bounded, opt-in web research routing; retrieved pages never select tools."""
import ipaddress
import json
import os
import re
import time
from urllib.parse import urlsplit


def available_providers():
    enabled = {p.strip().lower() for p in os.environ.get(
        'AIBS_WEB_ENABLED_PROVIDERS', 'ddgs').split(',')}
    return {p for p in enabled if p in ('ddgs', 'local') or
            (p == 'firecrawl' and os.environ.get('FIRECRAWL_API_KEY', '').strip()) or
            (p == 'tavily' and os.environ.get('TAVILY_API_KEY', '').strip())}


def public_url(url):
    """Syntactic admission only; not a DNS/redirect isolation guarantee."""
    try:
        if len(url) > 2000 or any(ord(c) < 33 for c in url) or '\\' in url:
            return False
        p = urlsplit(url)
        host = (p.hostname or '').rstrip('.').lower()
        if (p.scheme not in ('http', 'https') or p.username or p.password or
                p.port not in (None, 80 if p.scheme == 'http' else 443)):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            if ('.' not in host or host.endswith(('.localhost', '.local', '.internal')) or
                    host == 'localhost' or re.fullmatch(r'[0-9.]+', host)):
                return False
            return bool(re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host)) and not any(
                label.startswith('0x') for label in host.split('.'))
    except (ValueError, TypeError):
        return False


def plan_web_request(query, providers=None):
    raw = str(query or '').strip()
    p = dict(status='ready', provider=None, operation='search', topic='general',
             reason='', query=raw[:500])
    providers = available_providers() if providers is None else set(providers)
    # Pasted prose/Markdown quotation marks delimit a URL; encoded URL data stays intact.
    urls = list(dict.fromkeys(u.rstrip('.,;!?)') for u in re.findall(
        r'https?://[^\s<>"\'\u2018\u2019\u201c\u201d\u00ab\u00bb`]+', raw)))
    if not raw or len(raw) > 500:
        p.update(status='unsupported', reason='Use a public research query of 1 to 500 characters.')
        return p
    if re.search(r'\b(crawl|entire site|whole site|every page|all pages)\b', raw, re.I) or len(urls) > 1:
        p.update(status='unsupported', reason='Bulk crawling and multiple-page requests are not enabled; request one page at a time.')
        return p
    if urls:
        p.update(operation='scrape', topic='page', url=urls[0])
        if not public_url(urls[0]):
            p.update(status='unsupported', reason='Only public HTTP(S) URLs without credentials or custom ports are accepted.')
            return p
        choices = ['local', 'firecrawl']
    elif re.search(r'\b(news|latest|breaking|today|current)\b', raw, re.I):
        p['topic'] = 'news'
        choices = ['tavily', 'firecrawl', 'ddgs']
    elif re.search(r'\b(api|documentation|docs|python|javascript|react|programming|sdk)\b', raw, re.I):
        p['topic'] = 'technical'
        choices = ['firecrawl', 'ddgs', 'tavily']
    elif re.search(r'\b(compare|comparison|research|papers|studies)\b', raw, re.I):
        p['topic'] = 'research'
        choices = ['firecrawl', 'tavily', 'ddgs']
    else:
        choices = ['ddgs', 'tavily', 'firecrawl']
    selected = next((name for name in choices if name in providers), None)
    p['provider'] = selected
    if selected is None:
        p.update(status='unavailable', reason='No enabled and configured provider supports this request.')
    elif selected != choices[0]:
        p['reason'] = 'Preferred provider unavailable; selected an enabled provider for this operation before retrieval.'
    else:
        p['reason'] = 'Selected the configured provider for this task category.'
    return p


def _post(url, key, payload):
    import httpx
    if not key:
        raise ValueError('Provider not configured')
    start = time.monotonic()
    with httpx.Client(timeout=httpx.Timeout(8, connect=3), trust_env=False,
                      follow_redirects=False) as client:
        with client.stream('POST', url, headers={'Authorization': 'Bearer ' + key},
                           json=payload) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                if len(content) + len(chunk) > 2 * 1024 * 1024:
                    raise ValueError('Response too large')
                if time.monotonic() - start > 10:
                    raise TimeoutError('Provider timed out')
                content.extend(chunk)
    result = json.loads(content)
    if not isinstance(result, dict):
        raise ValueError('Invalid response')
    return result


def _tavily(plan):
    result = _post('https://api.tavily.com/search', os.environ.get('TAVILY_API_KEY', '').strip(),
                   {'query': plan['query'], 'max_results': 3,
                    'topic': 'news' if plan['topic'] == 'news' else 'general',
                    'search_depth': 'basic', 'include_answer': False,
                    'include_raw_content': False, 'auto_parameters': False})
    rows = result.get('results')
    if not isinstance(rows, list):
        raise ValueError('Invalid search results')
    return [{'href': r.get('url', ''), 'title': r.get('title', ''),
             'body': r.get('content', '')} for r in rows[:3] if isinstance(r, dict)]


def _firecrawl(plan):
    if plan['operation'] == 'search':
        from .optional_web_search import _firecrawl_search
        return _firecrawl_search(plan['query'])
    if not public_url(plan.get('url', '')):
        raise ValueError('Invalid page URL')
    result = _post('https://api.firecrawl.dev/v2/scrape', os.environ.get('FIRECRAWL_API_KEY', '').strip(),
                   {'url': plan['url'], 'formats': ['markdown'],
                    'onlyMainContent': True, 'timeout': 8000})
    data = result.get('data')
    if result.get('success') is not True or not isinstance(data, dict):
        raise ValueError('Invalid page result')
    metadata = data.get('metadata') or {}
    if not isinstance(metadata, dict) or metadata.get('error') or int(metadata.get('statusCode', 200)) >= 400:
        raise ValueError('Page retrieval failed')
    body = data.get('markdown')
    if not isinstance(body, str) or not body.strip():
        return []
    url = metadata.get('sourceURL') or plan['url']
    if not public_url(url):
        raise ValueError('Invalid source URL')
    return [{'href': url, 'title': metadata.get('title', ''), 'body': body}]


def _ddgs(plan):
    from ddgs import DDGS
    return list(DDGS(timeout=8).text(plan['query'], max_results=3, backend='bing'))


def _local(plan):
    from .local_web_reader import read_page
    return read_page(plan['url'])


def execute_plan(plan, adapters=None):
    result = {k: plan[k] for k in ('status', 'provider', 'operation', 'topic', 'reason')}
    result['rows'] = []
    if plan['status'] != 'ready':
        return result
    try:
        adapters = adapters if adapters is not None else {'ddgs': _ddgs, 'local': _local, 'firecrawl': _firecrawl, 'tavily': _tavily}
        rows = adapters[plan['provider']](dict(plan))
        result['rows'] = [{'href': str(r.get('href', '')), 'title': str(r.get('title', ''))[:160],
                           'body': str(r.get('body', ''))[:1200]} for r in rows[:3]
                          if isinstance(r, dict) and public_url(str(r.get('href', '')))]
        result['status'] = 'ok' if result['rows'] else 'empty'
    except Exception:
        result.update(status='unavailable', rows=[], reason='Selected provider failed; no additional provider was called.')
    return result


def orchestrate(query):
    return execute_plan(plan_web_request(query))
