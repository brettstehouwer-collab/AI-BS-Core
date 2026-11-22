"""Write-once manuscript artifacts and atomic index commits.

The lexical check permits case and punctuation changes. Exact stored bytes have
separate fingerprints. This is application-level preservation, not OS-level WORM.
Importing the module never creates or opens the real manuscript vault.
"""
from contextlib import contextmanager
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from typing import Any, Dict, List
from core.subagent_coordinator import verify_immutable_transcription

MANUSCRIPTS_DIR = Path("C:/AI-BS/saved_data/manuscripts/fire_and_the_forge")
INDEX_FILE = MANUSCRIPTS_DIR / "chapters_index.json"
_WRITER_LOCK = threading.RLock()
_MAX_INDEX_BYTES = 8 * 1024 * 1024
_REQUIRED_FIELDS = {"chapter_id", "title", "author", "word_count", "verified_utc", "formatted_file", "raw_file", "status"}


class LexicalIntegrityError(Exception):
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(message)
        self.details = details


class PublishingStorageError(RuntimeError):
    """The vault cannot be safely read or committed; existing evidence remains."""


class ChapterConflictError(PublishingStorageError):
    """An identifier belongs to a sealed chapter or colliding filename."""


def _slug(chapter_id: str) -> str:
    if not isinstance(chapter_id, str) or not chapter_id.strip() or len(chapter_id) > 200:
        raise ValueError("Enter a chapter identifier of 1-200 characters.")
    slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", chapter_id).lower()[:96]
    if not slug.strip("_-"):
        raise ValueError("Chapter identifiers must contain a letter or digit.")
    return slug


def _plain_path(path: Path) -> None:
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise PublishingStorageError("Linked manuscript storage is not supported.")


def _paths() -> tuple[Path, Path]:
    root, index = Path(MANUSCRIPTS_DIR), Path(INDEX_FILE)
    _plain_path(root)
    _plain_path(index)
    if index.parent.resolve() != root.resolve():
        raise PublishingStorageError("The chapter index is outside its vault.")
    return root, index


def _sync_directory(root: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


@contextmanager
def _vault_lock(root: Path):
    """Serialize threads and processes; never delete the lock inode."""
    with _WRITER_LOCK:
        root.mkdir(parents=True, exist_ok=True)
        _plain_path(root)
        lock_path = root / ".publishing.lock"
        _plain_path(lock_path)
        with lock_path.open("a+b") as lock:
            if lock.seek(0, os.SEEK_END) == 0:
                lock.write(b"\0")
                lock.flush()
                os.fsync(lock.fileno())
            deadline = time.monotonic() + 5.0
            while True:
                try:
                    lock.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError as error:
                    if time.monotonic() >= deadline:
                        raise PublishingStorageError("Another manuscript writer is busy; retry later.") from error
                    time.sleep(0.02)
            try:
                yield
            finally:
                lock.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _write_once(path: Path, data: bytes) -> None:
    """Publish complete bytes without overwriting an existing artifact."""
    _plain_path(path)
    descriptor, temporary = tempfile.mkstemp(prefix=".publishing-content-", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            _plain_path(path)
            if path.read_bytes() != data:
                raise PublishingStorageError("An existing manuscript artifact failed its fingerprint check.")
    finally:
        temporary_path.unlink(missing_ok=True)


def _serialize_index(index: List[Dict[str, Any]]) -> bytes:
    data = (json.dumps(index, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(data) > _MAX_INDEX_BYTES:
        raise PublishingStorageError("The chapter index would exceed its supported size; existing chapters were preserved.")
    return data


class ImmutablePublishingEngine:
    """Keep legacy listings and create exact write-once artifacts for new IDs.

    Changed content needs a distinct identifier. Exact retries are idempotent.
    The atomic index is the publication commit point. Complete files left by an
    interrupted index commit are retained and safely reused on exact retry.
    """

    @staticmethod
    def _read_index() -> List[Dict[str, Any]]:
        root, index_path = _paths()
        if not index_path.exists():
            if root.exists() and (any(root.glob("*.md")) or any(root.glob("*.raw.txt"))):
                raise PublishingStorageError("The index is missing while manuscript artifacts exist.")
            return []
        try:
            if index_path.stat().st_size > _MAX_INDEX_BYTES:
                raise ValueError("index size")
            index = json.loads(index_path.read_text(encoding="utf-8-sig"))
            if not isinstance(index, list):
                raise ValueError("index shape")
            identifiers, slugs = set(), set()
            for row in index:
                if not isinstance(row, dict) or not _REQUIRED_FIELDS.issubset(row):
                    raise ValueError("record shape")
                if any(not isinstance(row[key], str) for key in _REQUIRED_FIELDS - {"word_count"}):
                    raise ValueError("record types")
                if not isinstance(row["word_count"], int) or row["word_count"] < 0:
                    raise ValueError("word count")
                identifier, slug = row["chapter_id"], _slug(row["chapter_id"])
                if identifier in identifiers or slug in slugs:
                    raise ValueError("duplicate identity")
                identifiers.add(identifier)
                slugs.add(slug)
                if "content_sha256" in row:
                    for field in ("content_sha256", "raw_sha256", "formatted_sha256"):
                        if not re.fullmatch(r"[0-9a-f]{64}", row.get(field, "")):
                            raise ValueError("fingerprint")
            return index
        except (OSError, ValueError, TypeError) as error:
            raise PublishingStorageError("The chapter index is unreadable or invalid; original files were preserved.") from error

    @staticmethod
    def _write_index(index: List[Dict[str, Any]]) -> None:
        root, index_path = _paths()
        data = _serialize_index(index)
        descriptor, temporary = tempfile.mkstemp(prefix=".publishing-index-", dir=root)
        temporary_path = Path(temporary)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, index_path)
            _sync_directory(root)
        finally:
            temporary_path.unlink(missing_ok=True)

    @classmethod
    def list_chapters(cls) -> List[Dict[str, Any]]:
        return cls._read_index()

    @staticmethod
    def _verify_record(record: Dict[str, Any], root: Path) -> None:
        for field, fingerprint in (("raw_file", "raw_sha256"), ("formatted_file", "formatted_sha256")):
            path = Path(record[field])
            _plain_path(path)
            if path.parent.resolve() != root.resolve():
                raise PublishingStorageError("A manuscript artifact is outside its vault.")
            try:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as error:
                raise PublishingStorageError("A sealed manuscript artifact is unavailable.") from error
            if actual != record[fingerprint]:
                raise PublishingStorageError("A sealed manuscript artifact failed its fingerprint check.")

    @classmethod
    def save_verified_chapter(cls, chapter_id: str, title: str, raw_text: str,
                              formatted_text: str, author: str = "Brett Adam Stehouwer") -> Dict[str, Any]:
        slug = _slug(chapter_id)
        if slug in {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1, 10)),
                    *(f'lpt{i}' for i in range(1, 10))}:
            raise ValueError("Chapter identifiers cannot use reserved Windows device names.")
        if not all(isinstance(value, str) for value in (title, raw_text, formatted_text, author)):
            raise ValueError("Chapter title, author and manuscript fields must be text.")
        check = verify_immutable_transcription(raw_text, formatted_text)
        if not check.get("verified_verbatim"):
            raise LexicalIntegrityError("The formatted chapter changed the normalized word sequence.", check)
        payload = json.dumps(dict(chapter_id=chapter_id, title=title, author=author,
                                  raw_text=raw_text, formatted_text=formatted_text),
                             ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        content_hash = hashlib.sha256(payload).hexdigest()
        initial_index = cls._read_index()  # Reject corruption before any write.
        # Refusals must not alter legacy vaults even by creating a lock file.
        # Successful/new publication rechecks the complete index under the lock.
        for existing in initial_index:
            if existing['chapter_id'] == chapter_id and existing.get('content_sha256') != content_hash:
                raise ChapterConflictError('This chapter is already sealed. Use a distinct identifier for a new revision.')
            if existing['chapter_id'] != chapter_id and _slug(existing['chapter_id']) == slug:
                raise ChapterConflictError('This identifier conflicts with an existing chapter filename.')
        root, _ = _paths()
        try:
            with _vault_lock(root):
                index = cls._read_index()
                for existing in index:
                    if existing["chapter_id"] == chapter_id:
                        if existing.get("content_sha256") == content_hash:
                            cls._verify_record(existing, root)
                            return {"status": "success", "record": existing, "verification": check, "idempotent": True}
                        raise ChapterConflictError("This chapter is already sealed. Use a distinct identifier for a new revision.")
                    if _slug(existing["chapter_id"]) == slug:
                        raise ChapterConflictError("This identifier conflicts with an existing chapter filename.")
                raw_data = raw_text.encode("utf-8")
                document = (f"# {title}\n\n*Author: {author}*\n"
                            "*Lexical check: normalized word-token equality*\n\n---\n\n"
                            f"{formatted_text}").encode("utf-8")
                raw_path = root / f"{slug}.{content_hash}.raw.txt"
                chapter_path = root / f"{slug}.{content_hash}.md"
                record = dict(chapter_id=chapter_id, title=title, author=author,
                              word_count=check.get("raw_word_count", 0),
                              verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                              formatted_file=str(chapter_path), raw_file=str(raw_path),
                              status="SEALED_IMMUTABLE", storage_policy="write_once_v1",
                              verification_policy="case_insensitive_word_tokens_v1",
                              content_sha256=content_hash,
                              raw_sha256=hashlib.sha256(raw_data).hexdigest(),
                              formatted_sha256=hashlib.sha256(document).hexdigest())
                # The reader and writer share the same byte limit. Refuse an
                # oversized aggregate before publishing any manuscript bytes.
                _serialize_index([*index, record])
                if not Path(INDEX_FILE).exists():
                    cls._write_index([])
                _write_once(raw_path, raw_data)
                _write_once(chapter_path, document)
                _sync_directory(root)
                cls._write_index([*index, record])
                return {"status": "success", "record": record, "verification": check, "idempotent": False}
        except OSError as error:
            raise PublishingStorageError("The chapter could not be committed; existing evidence was preserved.") from error
