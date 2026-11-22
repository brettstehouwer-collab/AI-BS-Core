"""Private, immutable public-news evidence; no inference or trading effects."""
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile

DEFAULT_ARCHIVE = Path(__file__).resolve().parents[2] / 'trade' / 'market_news'


class NewsArchive:
    def __init__(self, root=DEFAULT_ARCHIVE, *, max_bytes=100 * 1024 * 1024):
        self.root = Path(root).absolute()
        self.max_bytes = max_bytes

    def _check(self, path):
        for part in (path, *path.parents):
            if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
                raise ValueError('Linked news archive path refused')

    def save(self, article, *, now):
        from backend.daemons.news_catalyst_daemon import article_url, clean_text
        source = article['source']
        url = article_url(article['url'], source)
        title = clean_text(article['title'], 512)
        if not title:
            raise ValueError('News title required')
        payload = dict(schema=1, source=source, url=url, title=title,
                       summary=clean_text(article.get('summary', ''), 400),
                       published_utc=article.get('published_utc'),
                       published_status=article.get('published_status', 'MISSING'),
                       evidence_type='untrusted_publisher_feed', advisory_only=True,
                       instructions_allowed=False, trading_authority=False)
        identity = hashlib.sha256((source + '\n' + url).encode()).hexdigest()
        version = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        target = self.root / 'records' / identity / (version + '.json')
        self._check(target)
        if target.exists():
            existing = json.loads(target.read_text(encoding='utf-8'))
            if {k: existing.get(k) for k in payload} != payload:
                raise ValueError('Archived news revision mismatch; original retained')
            return target
        payload['observed_utc'] = int(now)
        raw = (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        used = sum(p.stat().st_size for p in self.root.rglob('*.json'))
        if used + len(raw) > self.max_bytes:
            raise ValueError('News archive storage budget reached; retained records were not deleted')
        target.parent.mkdir(parents=True, exist_ok=True)
        self._check(target)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent, suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target)  # Atomic publication without overwriting an earlier observation.
        except FileExistsError:
            return self.save(article, now=now)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return target

    def context(self, query='', *, now, limit=5, max_age=7 * 86400):
        """Bounded advisory references, latest revision per publisher URL.

        Both publication and first observation must precede the evaluation time.
        This avoids treating late-discovered articles as historical foresight.
        """
        if type(limit) is not int or not 1 <= limit <= 20 or not 0 < max_age <= 30 * 86400:
            raise ValueError('Bounded context settings required')
        self._check(self.root)
        terms = set(re.findall(r'[a-z0-9_]+', query.lower()))
        latest = {}
        for path in self.root.glob('records/*/*.json'):
            self._check(path)
            if path.stat().st_size > 8192:
                continue
            try:
                row = json.loads(path.read_text(encoding='utf-8'))
                published, observed = row.get('published_utc'), row.get('observed_utc')
                if (type(published) is not int or type(observed) is not int
                        or not 0 <= now - published <= max_age or not observed <= now
                        or row.get('schema') != 1 or row.get('trading_authority') is not False):
                    continue
                key = (row['source'], row['url'])
                if key not in latest or observed > latest[key]['observed_utc']:
                    latest[key] = row
            except (ValueError, KeyError, UnicodeError):
                continue
        def relevance(row):
            words = set(re.findall(r'[a-z0-9_]+', (row['title'] + ' ' + row['summary']).lower()))
            return (len(terms & words), row['published_utc'], row['observed_utc'])
        rows = sorted(latest.values(), key=relevance, reverse=True)
        return [row for row in rows if not terms or relevance(row)[0]][:limit]
