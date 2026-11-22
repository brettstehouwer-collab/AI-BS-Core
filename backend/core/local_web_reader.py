"""Credential-free, single-page public IPv4 reader. No browser or link traversal."""
import http.client
from fnmatch import fnmatchcase
from html.parser import HTMLParser
import ipaddress
import re
import socket
import ssl
import threading
import time
from urllib.parse import unquote, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

AGENT = 'AIBSResearchBot'
_gate = threading.Lock()
_last_request = {}


def _remaining(deadline):
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError('Page reader deadline reached')
    return min(left, 3.0)


def resolve_public(host, port):
    # IPv4 only for now: avoid IPv6 translation/tunnelling and scoped addresses.
    rows = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    if not rows:
        raise ValueError('No public address')
    for family, kind, protocol, canonical, address in rows:
        ip = ipaddress.ip_address(address[0])
        if (family != socket.AF_INET or ip.version != 4 or not ip.is_global or
                ip.is_multicast or ip.is_reserved or address[1] != port):
            raise ValueError('Non-public address rejected')
    return rows[0]


class PinnedConnection(http.client.HTTPConnection):
    def __init__(self, host, port, address, secure, deadline):
        super().__init__(host, port, timeout=_remaining(deadline))
        self.address, self.secure, self.deadline = address, secure, deadline

    def connect(self):
        family, kind, protocol, _, address = self.address
        sock = socket.socket(family, kind, protocol)
        try:
            sock.settimeout(_remaining(self.deadline))
            # Numeric sockaddr from the validated DNS answer: no second lookup.
            sock.connect(address)
            if sock.getpeername()[0] != address[0]:
                raise ValueError('Connection address changed')
            if self.secure:
                context = ssl.create_default_context()
                context.set_alpn_protocols(['http/1.1'])
                sock = context.wrap_socket(sock, server_hostname=self.host)
            self.sock = sock
        except BaseException:
            sock.close()
            raise


def _get(url, deadline, limit):
    from .web_research_orchestrator import public_url
    if not public_url(url):
        raise ValueError('Public URL required')
    parts = urlsplit(url)
    port = 443 if parts.scheme == 'https' else 80
    address = resolve_public(parts.hostname, port)
    conn = PinnedConnection(parts.hostname, port, address, parts.scheme == 'https', deadline)

    def abort():
        try:
            if conn.sock:
                conn.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()

    timer = threading.Timer(max(0.001, deadline - time.monotonic()), abort)
    timer.daemon = True
    timer.start()
    try:
        _remaining(deadline)
        path = urlunsplit(('', '', parts.path or '/', parts.query, ''))
        conn.request('GET', path, headers={'User-Agent': AGENT + '/1.0',
                     'Accept': 'text/html,text/plain,application/xhtml+xml',
                     'Accept-Encoding': 'identity', 'Connection': 'close'})
        response = conn.getresponse()
        if response.getheader('Content-Encoding', 'identity').lower() not in ('', 'identity'):
            raise ValueError('Compressed responses are not supported')
        length = response.getheader('Content-Length')
        if length is not None and (int(length) < 0 or int(length) > limit):
            raise ValueError('Page too large')
        content = bytearray()
        while True:
            if conn.sock:
                conn.sock.settimeout(_remaining(deadline))
            chunk = response.read1(min(16384, limit + 1 - len(content)))
            _remaining(deadline)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > limit:
                raise ValueError('Page too large')
        return response.status, response.getheader('Content-Type', ''), bytes(content)
    finally:
        timer.cancel()
        conn.close()


def _pace(origin, deadline, interval=2):
    delay = _last_request.get(origin, 0) + max(2, interval) - time.monotonic()
    if delay > 0:
        if delay >= deadline - time.monotonic():
            raise TimeoutError('Site pacing exceeds this request budget')
        time.sleep(delay)
    _remaining(deadline)
    # One admitted reader holds the gate; bounded bookkeeping, no disk storage.
    if len(_last_request) >= 256 and origin not in _last_request:
        del _last_request[min(_last_request, key=_last_request.get)]
    _last_request[origin] = time.monotonic()


class PageText(HTMLParser):
    excluded = {'script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'noscript', 'svg', 'template'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = []
        self.in_title = False
        self.title = []
        self.text = []
        self.size = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.excluded:
            self.hidden.append(tag)
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in self.hidden:
            del self.hidden[self.hidden.index(tag):]
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.hidden or self.size >= 12000:
            return
        data = data.strip()[:12000 - self.size]
        if data:
            (self.title if self.in_title else self.text).append(data)
            self.size += len(data)


def _robots_denied(lines, url):
    """Conservative supplement to stdlib robots parsing for wildcards/order.

    Applicable Disallow rules win even over Allow exceptions. This can refuse
    an allowed page, but avoids stdlib's first-match/wildcard limitations.
    """
    groups = []
    agents, rules = [], []
    for line in list(lines) + ['User-agent: __end__']:
        key, sep, value = line.split('#', 1)[0].partition(':')
        key, value = key.strip().lower(), value.strip()
        if not sep:
            continue
        if key == 'user-agent':
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
        elif agents:
            rules.append((key, value))
    named = [(a, r) for a, r in groups if any(x != '*' and x in AGENT.lower() for x in a)]
    selected = named or [(a, r) for a, r in groups if '*' in a]
    parsed = urlsplit(url)
    target = unquote((parsed.path or '/') + ('?' + parsed.query if parsed.query else ''))
    for agents, rules in selected:
        for key, value in rules:
            if key != 'disallow' or not value:
                continue
            value = unquote(value)
            end = value.endswith('$')
            # fnmatch's atomic star handling avoids backtracking-heavy patterns.
            pattern = (value[:-1] if end else value).replace('[', '[[]')
            if fnmatchcase(target, pattern + ('' if end else '*')):
                return True
    return False


def read_page(url):
    from .web_research_orchestrator import public_url
    if not public_url(url):
        raise ValueError('Public URL required')
    if not _gate.acquire(blocking=False):
        raise ValueError('Local page reader is busy')
    try:
        deadline = time.monotonic() + 10
        parsed = urlsplit(url)
        origin = urlunsplit((parsed.scheme, parsed.netloc, '', '', ''))
        _pace(origin, deadline)
        status, content_type, raw = _get(origin + '/robots.txt', deadline, 128 * 1024)
        interval = 2
        if status == 200:
            if 'text/plain' not in content_type.lower():
                raise ValueError('Robots policy unavailable')
            robots = RobotFileParser()
            lines = raw.decode('utf-8', errors='replace').splitlines()
            robots.parse(lines)
            if not robots.can_fetch(AGENT, url) or _robots_denied(lines, url):
                raise ValueError('Robots policy disallows this page')
            interval = max(interval, robots.crawl_delay(AGENT) or 0)
            rate = robots.request_rate(AGENT)
            if rate:
                if rate.requests <= 0:
                    raise ValueError('Robots rate disallows requests')
                interval = max(interval, rate.seconds / rate.requests)
        elif status not in (404, 410):
            raise ValueError('Robots policy unavailable')
        _pace(origin, deadline, interval)
        status, content_type, raw = _get(url, deadline, 2 * 1024 * 1024)
        if status != 200:
            raise ValueError('Page unavailable; redirects are not followed')
        mime = content_type.split(';')[0].strip().lower()
        if mime not in ('text/html', 'application/xhtml+xml', 'text/plain'):
            raise ValueError('Only text pages are supported')
        charset = re.search(r'charset=["\']?([\w-]+)', content_type, re.I)
        text = raw.decode(charset.group(1) if charset else 'utf-8', errors='replace')
        title = parsed.hostname
        if mime != 'text/plain':
            parser = PageText()
            parser.feed(text)
            parser.close()
            title = ' '.join(parser.title) or title
            text = ' '.join(parser.text)
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            return []
        return [{'href': url, 'title': title[:160], 'body': text[:1200]}]
    finally:
        _gate.release()
