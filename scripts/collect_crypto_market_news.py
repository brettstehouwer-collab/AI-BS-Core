"""Public RSS archival only. No model loading, credentials or order dispatch."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.daemons.news_catalyst_daemon import FEEDS, BODY_LIMIT, parse_feed
from backend.trading.news_archive import NewsArchive, DEFAULT_ARCHIVE


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def collect():
    archive = NewsArchive()
    archive._check(archive.root)
    if sum(p.stat().st_size for p in archive.root.rglob('*.json')) + 4096 > archive.max_bytes:
        print(json.dumps({'status': 'storage_budget_reached', 'trading_enabled': False}))
        return 2
    now = int(time.time())
    results = []
    opener = build_opener(ProxyHandler({}), NoRedirect())
    for source, url in FEEDS.items():
        try:
            request = Request(url, headers={'User-Agent': 'AI-BS-Public-News-Archive/1', 'Accept': 'application/rss+xml, application/atom+xml, application/xml'})
            with opener.open(request, timeout=15) as response:
                raw = response.read(BODY_LIMIT + 1)
            articles = parse_feed(raw, source)
            for article in articles:
                archive.save(article, now=now)
            results.append({'source': source, 'status': 'saved', 'items': len(articles)})
        except Exception as error:
            results.append({'source': source, 'status': 'unavailable', 'error_type': type(error).__name__,
                            **({'http_status': error.code} if isinstance(error, HTTPError) else {})})
    archive.root.mkdir(parents=True, exist_ok=True)
    receipt = {'observed_utc': now, 'advisory_only': True, 'trading_enabled': False, 'feeds': results}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    runs = archive.root / 'runs'
    archive._check(runs)
    runs.mkdir(exist_ok=True)
    if sum(p.stat().st_size for p in archive.root.rglob('*.json')) + len(json.dumps(receipt).encode()) > archive.max_bytes:
        print(json.dumps({'status': 'storage_budget_reached', 'trading_enabled': False}))
        return 2
    with (runs / (stamp + '.json')).open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt))
    return 0 if any(row['status'] == 'saved' and row['items'] for row in results) else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', help='Read bounded retained advisory context instead of fetching feeds')
    args = parser.parse_args()
    if args.query is not None:
        print(json.dumps(NewsArchive().context(args.query, now=int(time.time())), ensure_ascii=False))
    else:
        raise SystemExit(collect())
