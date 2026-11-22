"""Separate, bounded advisory news store. Never opens an execution ledger."""
from contextlib import closing, contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
NEWS_DB_PATH = ROOT / "state" / "crypto_news_telemetry.db"
SCOPES = {"LIVE_PUBLIC_NEWS", "OFFLINE_NEWS_FIXTURE"}
MAX_ARTICLES = 10000


class NewsIntegrityError(ValueError):
    pass


def safe_path(path, *, existing):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise NewsIntegrityError("linked news store forbidden")
    result = path.resolve()
    temporary = result.is_relative_to(Path(tempfile.gettempdir()).resolve()) and not result.is_relative_to(ROOT)
    if result != NEWS_DB_PATH or path != NEWS_DB_PATH:
        if not temporary:
            raise NewsIntegrityError("dedicated news database or OS-temporary fixture required")
    if existing and (not result.is_file() or result.stat().st_nlink != 1):
        raise NewsIntegrityError("news store missing or linked")
    if not existing and result.exists():
        raise NewsIntegrityError("never initialize an existing database")
    return result


class NewsStore:
    def __init__(self, path):
        self.path = safe_path(path, existing=True)
        try:
            with closing(self._connect()) as db:
                metadata = dict(db.execute("SELECT key,value FROM news_metadata"))
                if metadata.get("schema") != "1" or metadata.get("scope") not in SCOPES:
                    raise NewsIntegrityError("invalid news provenance")
                self.scope = metadata["scope"]
                db.execute("SELECT * FROM news_catalyst_signals LIMIT 1").fetchone()
                db.execute("SELECT * FROM news_feed_health LIMIT 1").fetchone()
        except sqlite3.Error as exc:
            raise NewsIntegrityError("invalid news store") from exc

    @classmethod
    def create(cls, path, *, scope):
        path = safe_path(path, existing=False)
        if scope not in SCOPES or (path == NEWS_DB_PATH and scope != "LIVE_PUBLIC_NEWS"):
            raise NewsIntegrityError("explicit nonfinancial news scope required")
        # Only this explicitly invoked operation may create a directory/database.
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb"):
            pass
        with closing(sqlite3.connect(path, isolation_level=None, timeout=2)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA journal_size_limit=1048576")
            db.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE news_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE news_catalyst_signals(
                    article_hash TEXT PRIMARY KEY,source TEXT NOT NULL,url TEXT NOT NULL,title TEXT NOT NULL,
                    summary TEXT NOT NULL,published_utc INTEGER,published_status TEXT NOT NULL,
                    first_seen_utc INTEGER NOT NULL,content_hash TEXT NOT NULL,status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,lease_token TEXT,lease_until INTEGER NOT NULL DEFAULT 0,
                    last_attempt_utc INTEGER NOT NULL DEFAULT 0,error_code TEXT NOT NULL DEFAULT '',
                    model TEXT,analysis TEXT,analyzed_utc INTEGER);
                CREATE INDEX news_recent ON news_catalyst_signals(first_seen_utc DESC);
                CREATE TABLE news_feed_health(source TEXT PRIMARY KEY,last_poll_utc INTEGER NOT NULL,
                    status TEXT NOT NULL,consecutive_failures INTEGER NOT NULL);
                COMMIT;
            """)
            db.execute("BEGIN IMMEDIATE")
            db.executemany("INSERT INTO news_metadata VALUES(?,?)", [("schema", "1"), ("scope", scope)])
            db.execute("COMMIT")
        return cls(path)

    def _connect(self, *, write=False):
        safe_path(self.path, existing=True)
        db = sqlite3.connect(self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"),
                             uri=True, isolation_level=None, timeout=2)
        db.row_factory = sqlite3.Row
        if write:
            db.execute("PRAGMA synchronous=FULL")
        else:
            db.execute("PRAGMA query_only=ON")
        return db

    @contextmanager
    def _write(self):
        with closing(self._connect(write=True)) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
            except BaseException:
                db.execute("ROLLBACK")
                raise
            else:
                db.execute("COMMIT")

    def register(self, article, *, now):
        """Normalized public article only; content is immutable on repeated fetch."""
        article_hash = hashlib.sha256((article["source"] + "\n" + article["url"]).encode()).hexdigest()
        content_hash = hashlib.sha256((article["title"] + "\n" + article["summary"]).encode()).hexdigest()
        published = article["published_utc"]
        state = "NEW" if published is not None and 0 <= now - published <= 3600 else "SKIPPED"
        with self._write() as db:
            db.execute("INSERT OR IGNORE INTO news_catalyst_signals(article_hash,source,url,title,summary,published_utc,"
                "published_status,first_seen_utc,content_hash,status) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (article_hash, article["source"], article["url"], article["title"], article["summary"], published,
                 article["published_status"], now, content_hash, state))
            count = db.execute("SELECT COUNT(*) FROM news_catalyst_signals").fetchone()[0]
            if count > MAX_ARTICLES:
                db.execute("DELETE FROM news_catalyst_signals WHERE article_hash IN "
                    "(SELECT article_hash FROM news_catalyst_signals WHERE status<>'PROCESSING' "
                    "ORDER BY first_seen_utc LIMIT ?)", (count - MAX_ARTICLES,))
        return article_hash

    def claim(self, article_hash, *, now):
        with self._write() as db:
            row = db.execute("SELECT * FROM news_catalyst_signals WHERE article_hash=?", (article_hash,)).fetchone()
            if not row or row["status"] in ("ANALYZED", "FAILED", "SKIPPED"):
                return None
            if row["status"] == "PROCESSING" and row["lease_until"] > now:
                return None
            if row["published_utc"] is None or not 0 <= now - row["published_utc"] <= 3600:
                db.execute("UPDATE news_catalyst_signals SET status='SKIPPED',error_code='STALE_NEWS',"
                           "lease_token=NULL,lease_until=0 WHERE article_hash=?", (article_hash,))
                return None
            if row["attempts"] >= 3:
                db.execute("UPDATE news_catalyst_signals SET status='FAILED',error_code='ATTEMPT_BUDGET_EXHAUSTED' WHERE article_hash=?", (article_hash,))
                return None
            if row["attempts"] and now - row["last_attempt_utc"] < 30 * 2 ** (row["attempts"] - 1):
                return None
            token = uuid4().hex
            db.execute("UPDATE news_catalyst_signals SET status='PROCESSING',attempts=attempts+1,lease_token=?,"
                "lease_until=?,last_attempt_utc=? WHERE article_hash=?", (token, now + 30, now, article_hash))
            return {**dict(row), "lease_token": token}

    def pending(self, *, now, limit=5):
        """Recovery is independent of the feed still listing the article."""
        with closing(self._connect()) as db:
            return [row[0] for row in db.execute("SELECT article_hash FROM news_catalyst_signals "
                "WHERE status IN ('NEW','RETRY','PROCESSING') AND lease_until<=? "
                "AND (attempts=0 OR last_attempt_utc+CASE attempts WHEN 1 THEN 30 ELSE 60 END<=?) "
                "ORDER BY first_seen_utc LIMIT ?", (now, now, limit))]

    def finish(self, article_hash, token, *, now, model, analysis=None, error_code=""):
        if error_code not in ("", "MODEL_UNAVAILABLE", "MODEL_INVALID_OUTPUT", "MODEL_TIMEOUT", "BODY_LIMIT", "CANCELLED"):
            raise NewsIntegrityError("invalid inference error code")
        with self._write() as db:
            row = db.execute("SELECT attempts FROM news_catalyst_signals WHERE article_hash=? AND lease_token=? "
                             "AND status='PROCESSING'", (article_hash, token)).fetchone()
            if not row:
                return False  # A stale worker cannot overwrite a newer claim.
            status = "ANALYZED" if analysis is not None else ("FAILED" if row[0] >= 3 else "RETRY")
            db.execute("UPDATE news_catalyst_signals SET status=?,error_code=?,model=?,analysis=?,analyzed_utc=?,"
                "lease_token=NULL,lease_until=0 WHERE article_hash=?", (status, error_code, model,
                json.dumps(analysis, sort_keys=True, allow_nan=False) if analysis is not None else None,
                now if analysis is not None else None, article_hash))
            return True

    def feed_status(self, source, *, now, status):
        if status not in ("OK", "FEED_HTTP_ERROR", "FEED_TIMEOUT", "FEED_INVALID", "BODY_LIMIT"):
            raise NewsIntegrityError("invalid feed status")
        with self._write() as db:
            old = db.execute("SELECT consecutive_failures FROM news_feed_health WHERE source=?", (source,)).fetchone()
            failures = 0 if status == "OK" else ((old[0] if old else 0) + 1)
            db.execute("INSERT INTO news_feed_health VALUES(?,?,?,?) ON CONFLICT(source) DO UPDATE SET "
                "last_poll_utc=excluded.last_poll_utc,status=excluded.status,consecutive_failures=excluded.consecutive_failures",
                (source, now, status, failures))
            return failures

    def recent(self, *, now, limit=10):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise NewsIntegrityError("invalid telemetry limit")
        with closing(self._connect()) as db:
            feeds = [dict(row) for row in db.execute("SELECT * FROM news_feed_health")]
            counts = dict(db.execute("SELECT status,COUNT(*) FROM news_catalyst_signals GROUP BY status"))
            items = []
            for row in db.execute("SELECT * FROM news_catalyst_signals WHERE status='ANALYZED' "
                    "AND published_utc BETWEEN ? AND ? ORDER BY published_utc DESC LIMIT 200", (now - 3600, now)):
                analysis = json.loads(row["analysis"])
                if (abs(analysis["sentiment_score"]) >= 0.6 and analysis["confidence"] >= 0.7
                        and analysis["detected_tokens"] and analysis["catalyst_category"] != "NOISE"):
                    items.append({key: row[key] for key in ("article_hash", "source", "url", "title", "published_utc", "analyzed_utc", "model")}
                                 | analysis | {"advisory_only": True, "confidence_calibrated": False})
                    if len(items) == limit:
                        break
            latest = max((r["last_poll_utc"] for r in feeds), default=None)
            return {"configured": True, "scope": self.scope, "advisory_only": True, "trading_enabled": False,
                "worker_state": "recent_poll_observed" if latest is not None and 0 <= now - latest <= 180 else "no_recent_poll",
                "feeds": feeds, "counts": counts, "items": items}
