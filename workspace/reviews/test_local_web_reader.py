import importlib
import socket
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))


class LocalReaderTests(unittest.TestCase):
    def setUp(self):
        self.m = importlib.import_module('core.local_web_reader')
        self.m._last_request.clear()

    def test_local_provider_needs_no_key_and_is_page_preference(self):
        from core import web_research_orchestrator as orch
        import os
        with patch.dict(os.environ, {'AIBS_WEB_ENABLED_PROVIDERS': 'ddgs,local'}, clear=True):
            self.assertEqual(orch.available_providers(), {'ddgs', 'local'})
            p = orch.plan_web_request('Read https://example.com/article')
            self.assertEqual((p['provider'], p['operation']), ('local', 'scrape'))
            self.assertEqual(orch.plan_web_request('latest news')['provider'], 'ddgs')

    def dns(self, *ips):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in ips]

    def test_dns_mixed_private_answers_block_entire_request(self):
        with patch.object(socket, 'getaddrinfo', return_value=self.dns('93.184.216.34', '127.0.0.1')):
            with self.assertRaises(ValueError):
                self.m.resolve_public('example.com', 443)

    def test_dns_private_metadata_and_multicast_blocked(self):
        for ip in ['169.254.169.254', '10.0.0.1', '224.0.0.1', '100.64.0.1']:
            with self.subTest(ip=ip), patch.object(socket, 'getaddrinfo', return_value=self.dns(ip)):
                with self.assertRaises(ValueError): self.m.resolve_public('example.com', 443)

    def test_connection_pins_numeric_address_and_tls_hostname(self):
        sock = Mock()
        sock.getpeername.return_value = ('93.184.216.34', 443)
        tls = Mock()
        with patch.object(socket, 'socket', return_value=sock), patch.object(self.m.ssl, 'create_default_context', return_value=tls):
            c = self.m.PinnedConnection('example.com', 443, self.dns('93.184.216.34')[0], True, time.monotonic()+8)
            c.connect()
            sock.connect.assert_called_once_with(('93.184.216.34', 443))
            self.assertEqual(tls.wrap_socket.call_args.kwargs['server_hostname'], 'example.com')

    def test_private_url_never_reaches_fetch(self):
        with patch.object(self.m, '_get') as get:
            with self.assertRaises(ValueError): self.m.read_page('http://127.0.0.1/admin')
            get.assert_not_called()

    def test_robots_denial_does_not_fetch_page(self):
        with patch.object(self.m, '_get', return_value=(200, 'text/plain', b'User-agent: *\nDisallow: /private')) as get:
            with self.assertRaises(ValueError): self.m.read_page('https://example.com/private')
            self.assertEqual(get.call_count, 1)

    def test_robots_error_and_redirect_fail_closed(self):
        for status in [301, 403, 429, 500]:
            with self.subTest(status=status), patch.object(self.m, '_get', return_value=(status, 'text/plain', b'')) as get:
                self.m._last_request.clear()
                with self.assertRaises(ValueError): self.m.read_page('https://example.com/article')
                self.assertEqual(get.call_count, 1)

    def test_page_text_excludes_scripts_forms_and_navigation(self):
        html = b'<html><title>Fixture article</title><nav>menu</nav><script>run code</script><style>css</style><form>password</form><main><h1>Article</h1><p>Useful evidence.</p></main></html>'
        with patch.object(self.m, '_get', side_effect=[(404, 'text/plain', b''), (200, 'text/html; charset=utf-8', html)]) as get, patch.object(self.m, '_pace'):
            rows = self.m.read_page('https://example.com/article')
        self.assertEqual(get.call_count, 2)
        self.assertEqual(rows[0]['href'], 'https://example.com/article')
        self.assertEqual(rows[0]['title'], 'Fixture article')
        self.assertIn('Useful evidence.', rows[0]['body'])
        for hidden in ['menu', 'run code', 'css', 'password']: self.assertNotIn(hidden, rows[0]['body'])

    def test_page_redirect_is_not_followed(self):
        with patch.object(self.m, '_get', side_effect=[(404, 'text/plain', b''), (302, 'text/html', b'')]) as get, patch.object(self.m, '_pace'):
            with self.assertRaises(ValueError): self.m.read_page('https://example.com/article')
            self.assertEqual(get.call_count, 2)

    def test_robots_wildcard_and_allow_order_cannot_bypass_disallow(self):
        policies = [b'User-agent: *\nDisallow: /private/*',
                    b'User-agent: *\nAllow: /\nDisallow: /private/',
                    b'User-agent: AIBSResearchBot\nDisallow: /*secret$']
        for policy in policies:
            with self.subTest(policy=policy), patch.object(self.m, '_get', return_value=(200, 'text/plain', policy)) as get, patch.object(self.m, '_pace'):
                with self.assertRaises(ValueError): self.m.read_page('https://example.com/private/secret')
                self.assertEqual(get.call_count, 1)

    def test_robots_other_agent_does_not_block_this_reader(self):
        policy = b'User-agent: AnotherBot\nDisallow: /\n\nUser-agent: *\nAllow: /'
        with patch.object(self.m, '_get', side_effect=[(200, 'text/plain', policy), (200, 'text/plain', b'evidence')]), patch.object(self.m, '_pace'):
            self.assertEqual(self.m.read_page('https://example.com/article')[0]['body'], 'evidence')

    def test_binary_page_rejected(self):
        with patch.object(self.m, '_get', side_effect=[(404, 'text/plain', b''), (200, 'application/pdf', b'PDF')]), patch.object(self.m, '_pace'):
            with self.assertRaises(ValueError): self.m.read_page('https://example.com/article')

    def test_response_limit_and_compression_rejected(self):
        for headers in [{'Content-Length': str(3*1024*1024)}, {'Content-Encoding': 'gzip'}]:
            with self.subTest(headers=headers):
                response = Mock(status=200)
                response.getheader.side_effect = lambda k, default=None: headers.get(k, default)
                conn = Mock()
                conn.getresponse.return_value = response
                with patch.object(self.m, 'resolve_public', return_value=self.dns('93.184.216.34')[0]), patch.object(self.m, 'PinnedConnection', return_value=conn):
                    with self.assertRaises(ValueError): self.m._get('https://example.com', time.monotonic()+8, 1024)
                    conn.close.assert_called_once()

    def test_declared_crawl_delay_is_respected(self):
        robots = b'User-agent: *\nAllow: /\nCrawl-delay: 5'
        with patch.object(self.m, '_get', side_effect=[(200, 'text/plain', robots), (200, 'text/plain', b'evidence')]), patch.object(self.m, '_pace') as pace:
            self.m.read_page('https://example.com/article')
        self.assertGreaterEqual(pace.call_args_list[-1].args[2], 5)

    def test_parallel_reader_is_refused(self):
        self.m._gate.acquire()
        try:
            with patch.object(self.m, '_get') as get:
                with self.assertRaises(ValueError): self.m.read_page('https://example.com')
                get.assert_not_called()
        finally:
            self.m._gate.release()

    def test_orchestrator_uses_reader_without_provider_fallback(self):
        from core import web_research_orchestrator as orch
        plan = orch.plan_web_request('Read https://example.com', providers={'local', 'ddgs'})
        with patch.object(self.m, 'read_page', return_value=[{'href': 'https://example.com', 'title': 'T', 'body': 'evidence'}]) as read:
            result = orch.execute_plan(plan)
        read.assert_called_once_with('https://example.com')
        self.assertEqual(result['status'], 'ok')


if __name__ == '__main__': unittest.main()
