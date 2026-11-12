"""Import explicit historical references into AI-BS's owned retrieval vault.

Local only. Does not train weights, execute source code, import model thoughts,
change activation flags, or call an embedding/provider service.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from core.personal_memory_scope import is_sensitive_memory_text

COLLECTION = 'historical_knowledge_v1'
MAX_FILE = 32 * 1024 * 1024
UUID = re.compile(r'^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$')
PRIVATE_FILE = re.compile(r'credential|oauth|token|password|client.secret|google_accounts|invoice|transaction|direct.deposit|income.breakdown|property.records|medical|medication|clinical|CPTSD|ADHD|leads|dennis|fiscal|financial|partisan|revenue.maximization|economic.and.energy|resume|résumé|\bcv\b|contact.list|signed|contract|agreement|^to[ _:]|^dear[ _:]', re.I)
SECRET = re.compile(r'''(?ix)
    -----BEGIN\s+(?:[A-Z]+\s+)*PRIVATE\s+KEY-----
    |\b(?:sk-|ghp_|github_pat_|AIzaSy)[A-Za-z0-9_\-]{12,}
    |\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+
    |\bbearer\s+[A-Za-z0-9._~+/\-]{8,}=*
    |\b(?:password|passwd|api[_ -]?key|access[_ -]?token|refresh[_ -]?token|client[_ -]?secret|authorization|private[_ -]?key)\s*["']?\s*[:=]\s*\S+
''')
PRIVATE_TEXT = re.compile(r'\b(?:social security|SSN|date of birth|routing number|account number|credit card|patient|diagnosis|prescription|medication|medical|therapy|CPTSD|ADHD|mental health|private key|seed phrase|mnemonic phrase)\b', re.I)
EMAIL = re.compile(r'[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}')
PHONE = re.compile(r'(?<!\w)(?:\+?1[- .]?)?(?:\(?\d{3}\)?[- .]\d{3}[- .]\d{4}|[2-9]\d{2}[2-9]\d{6})(?!\w)')
ADDRESS = re.compile(r'\b\d{1,6}\s+(?:[A-Za-z]+\s+){1,5}(?:Street|St|Road|Rd|Drive|Dr|Avenue|Ave|Lane|Ln|Boulevard|Blvd)\b(?:\s+(?:SE|SW|NE|NW))?', re.I)
URL = re.compile(r'https?://[^\s<>\)\]]+')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sanitize(text):
    """Reject secret/private passages, remove personal contacts and URL capabilities."""
    if not isinstance(text, str):
        return None, 'not_text'
    if SECRET.search(text) or is_sensitive_memory_text(text):
        return None, 'credential_pattern'
    if PRIVATE_TEXT.search(text):
        return None, 'private_personal_topic'
    # Do not retain prose presented as private model reasoning.
    if re.search(r'<(?:think|analysis)>|\b(?:internal thinking process|hidden chain.of.thought)\s*:', text, re.I):
        return None, 'private_reasoning_marker'
    text = EMAIL.sub('[contact removed]', text)
    text = PHONE.sub('[phone removed]', text)
    text = ADDRESS.sub('[address removed]', text)
    text = URL.sub(lambda m: m.group(0).split('?')[0].split('#')[0], text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text).strip()
    if len(text) < 80:
        return None, 'too_short'
    return text, None


class VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'head'):
            self.skip += 1
        if tag in ('p', 'div', 'br', 'h1', 'h2', 'h3', 'li') and not self.skip:
            self.out.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'head') and self.skip:
            self.skip -= 1

    def handle_data(self, text):
        if not self.skip:
            self.out.append(text)


def plain_parts(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(p['text'] for p in value if isinstance(p, dict)
                         and isinstance(p.get('text'), str)
                         and not any(k in p for k in ('thought', 'thoughts', 'functionCall', 'functionResponse')))
    return ''


def chunks(text, size=1800):
    # Every character of admitted text survives; deterministic bounded records.
    for start in range(0, len(text), size):
        yield start, text[start:start + size]


def prose_chunks(text, size=1800):
    """Prefer paragraph/word boundaries for new curated cards; preserve all text."""
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            paragraph = text.rfind('\n\n', start + 1, end)
            word = text.rfind(' ', start + 1, end)
            end = paragraph + 2 if paragraph >= 0 else (word + 1 if word >= 0 else end)
        yield start, text[start:end]
        start = end


class Corpus:
    def __init__(self):
        self.records = {}
        self.files = []
        self.counts = Counter()
        self.diagnostics = []

    def add(self, text, path, kind, locator, digest, *, splitter=chunks):
        cleaned, reason = sanitize(text)
        if reason:
            self.counts['excluded_' + reason] += 1
            return
        for offset, part in splitter(cleaned):
            fingerprint = sha(re.sub(r'\s+', ' ', part).strip().encode('utf-8'))
            ref = {'path': str(path), 'sha256': digest, 'locator': str(locator), 'char_offset': offset, 'kind': kind}
            if fingerprint in self.records:
                if ref not in self.records[fingerprint]['sources']:
                    self.records[fingerprint]['sources'].append(ref)
                self.counts['duplicate_chunks'] += 1
                continue
            title = re.sub(r'\s+', ' ', part.splitlines()[0]).strip('# ')[:130]
            self.records[fingerprint] = {'id': fingerprint, 'title': title or kind, 'text': part,
                                         'kind': kind, 'sources': [ref], 'verification': 'historical_unverified'}
            self.counts['admitted_chunks'] += 1

    def read(self, path, kind):
        row = {'path': str(path), 'kind': kind}
        self.files.append(row)
        if PRIVATE_FILE.search(path.name):
            row['disposition'] = 'excluded_private_filename'
            return None
        if path.stat().st_size > MAX_FILE:
            row['disposition'] = 'excluded_oversize'
            return None
        raw = path.read_bytes()
        row.update(bytes=len(raw), sha256=sha(raw), disposition='assessed')
        try:
            return raw.decode('utf-8-sig'), row['sha256']
        except UnicodeDecodeError:
            row['disposition'] = 'excluded_non_utf8'
            return None

    def artifact(self, path, kind):
        data = self.read(path, kind)
        if data:
            text, digest = data
            if path.suffix.lower() in ('.html', '.htm'):
                parser = VisibleHTML()
                parser.feed(text)
                text = '\n'.join(line.strip() for line in ''.join(parser.out).splitlines() if line.strip())
            self.add(text, path, kind, 'visible_document', digest)

    def antigravity(self, brain):
        for path in sorted(brain.glob('*/.system_generated/logs/transcript.jsonl')):
            data = self.read(path, 'antigravity_visible_transcript')
            if not data:
                continue
            text, digest = data
            for line_no, line in enumerate(text.splitlines(), 1):
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    self.counts['invalid_json_lines'] += 1
                    self.diagnostics.append({'path': str(path), 'line': line_no, 'error': 'invalid_json'})
                    continue
                if obj.get('type') not in ('USER_INPUT', 'PLANNER_RESPONSE'):
                    self.counts['excluded_nonvisible_events'] += 1
                    continue
                # Explicit key allowlist: never serialize whole events or thoughts.
                self.add(obj.get('content'), path, 'antigravity_' + obj['type'].lower(), f'line:{line_no}', digest)
        for path in sorted(brain.glob('*/*.md')):
            self.artifact(path, 'antigravity_explicit_artifact')

    def gemini(self, root):
        for path in sorted(root.rglob('session-*.jsonl')):
            data = self.read(path, 'gemini_cli_visible_transcript')
            if not data:
                continue
            text, digest = data
            messages = {}
            for line_no, line in enumerate(text.splitlines(), 1):
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    self.counts['invalid_json_lines'] += 1
                    self.diagnostics.append({'path': str(path), 'line': line_no, 'error': 'invalid_json'})
                    continue
                for msg in obj.get('$set', {}).get('messages', []):
                    if isinstance(msg, dict) and msg.get('type') in ('user', 'gemini'):
                        visible = plain_parts(msg.get('content'))
                        if visible:
                            messages[msg.get('id') or sha(visible.encode())] = visible
            for key, visible in sorted(messages.items()):
                self.add(visible, path, 'gemini_cli_visible_message', f'message:{key}', digest)

    def memory_dump(self, path):
        data = self.read(path, 'historical_memory_dump')
        if not data:
            return
        text, digest = data
        for i, obj in enumerate(json.loads(text)):
            if not isinstance(obj, dict):
                continue
            source = (obj.get('metadata') or {}).get('source')
            if source not in ('mobile_chat_stehouwer', 'desktop_ide_chat'):
                self.counts['excluded_telemetry_or_unknown_memory'] += 1
                continue
            self.add(obj.get('text'), path, 'historical_chat_memory', f'item:{i}', digest)


def build(corpus):
    corpus.antigravity(Path(r'C:\Users\footb\.gemini\antigravity\brain'))
    for root in (Path(r'C:\Users\footb\.gemini\tmp'), Path(r'E:\.gemini\tmp')):
        corpus.gemini(root)
    for root in (ROOT / 'Agent_Handoff_Summaries', ROOT / 'Agent_Implementation_Plans_History', ROOT / 'Agent_Tasks_History', ROOT / 'Gemini_Takeout_Dataparrent'):
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix.lower() in ('.md', '.html', '.htm', '.txt'):
                corpus.artifact(path, 'historical_document')
    takeout = Path(r'C:\Users\footb\Downloads\takeout-20261027T184532Z-1-001\Takeout\Drive')
    for path in sorted(takeout.rglob('*')):
        if path.is_file() and path.suffix.lower() in ('.html', '.txt'):
            corpus.artifact(path, 'google_takeout_drive_site')
    for path in (Path(r'D:\AI-BS_Master_Memory\master_memory_dump.json'),):
        if path.exists():
            corpus.memory_dump(path)
    downloads = Path(r'C:\Users\footb\Downloads')
    for path in sorted(downloads.glob('gemini-code-*.py')):
        corpus.artifact(path, 'gemini_code_reference_unexecuted')
    for path in (downloads / 'GEMINI_HANDOFF_2026-10-27.md', ROOT / 'learning/QWEN_CODER_PROBLEM_SOLVING_CARD_2026-10-30.md', ROOT / 'docs/engineering_ledger/2026-10-30_Historical_Build_Transcript_Learnings.md'):
        if path.exists():
            corpus.artifact(path, 'curated_engineering_reference')


def build_source_card(corpus, path):
    """Read one explicitly chosen prose card without scanning the historical archive."""
    path = path.resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in ('.md', '.txt'):
        raise ValueError('A source card must be an existing .md or .txt file')
    data = corpus.read(path, 'curated_public_guidance')
    if data:
        text, digest = data
        corpus.add(text, path, 'curated_public_guidance', 'visible_document', digest, splitter=prose_chunks)
    if not corpus.records:
        raise ValueError('The source card contains no admissible reference text')
    return str(path)


def record_content(record):
    # Source attribution travels in the retrieved excerpt, independently of tags.
    ref = record['sources'][0]
    return ('Historical reference; claims and dated instructions require current verification.\n'
            f"Source: {ref['path']} ({ref['locator']}); SHA256 {ref['sha256']}.\n"
            f"Kind: {record['kind']}.\n\n{record['text']}")


def import_records(records, db, owner):
    from core.owned_vault import store_record, read_record
    receipts = []
    for record in records:
        content = record_content(record)
        tags = {'corpus': COLLECTION, 'id': record['id'], 'sources': record['sources'], 'verification': record['verification']}
        actual = store_record(db, owner, record['title'], content, collection=COLLECTION, tags=tags)
        confirmed = read_record(db, owner, actual['id'], include_legacy=False)
        if confirmed['content'] != content or confirmed['owner'] != owner:
            raise RuntimeError('Imported record readback mismatch')
        receipts.append({'id': actual['id'], 'corpus_id': record['id'], 'content_sha256': actual['content_sha256']})
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--apply-local-admin', action='store_true', help='Import for the local operator principal only')
    parser.add_argument('--reviewed-manifest', type=Path, help='Require byte-identical records to a reviewed dry run before import')
    parser.add_argument('--source-card', type=Path, help='Import only this explicit .md/.txt card instead of rescanning historical sources')
    args = parser.parse_args()
    if args.apply_local_admin and args.reviewed_manifest is None:
        parser.error('--apply-local-admin requires --reviewed-manifest')
    args.output.mkdir(parents=True, exist_ok=False)
    corpus = Corpus()
    source_card = build_source_card(corpus, args.source_card) if args.source_card else None
    if not args.source_card:
        build(corpus)
    records = list(corpus.records.values())
    with (args.output / 'records.jsonl').open('w', encoding='utf-8', newline='\n') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'collection': COLLECTION,
                'source_mode': 'single_card' if source_card else 'historical_archive', 'source_card': source_card,
                'files': corpus.files, 'counts': dict(corpus.counts), 'records': len(records),
                'diagnostics': corpus.diagnostics,
                'records_sha256': sha((args.output / 'records.jsonl').read_bytes()),
                'excluded_source_groups': {'conversation_db_blobs': 'use visible JSONL counterparts',
                    'full_and_chunk_transcripts': 'duplicate and nonvisible fields excluded',
                    'account_and_oauth_config': 'credential material',
                    'ide_extensions': 'software dependencies rather than user history',
                    'dummy_takeout.json': 'synthetic fixture',
                    'Dennis and i chat transcripts.md': 'private third-party conversation; use curated engineering abstractions',
                    'learning_master_raw_archive': 'use primary visible records instead of reasoning-bearing derived archive',
                    'media_and_binary_attachments': 'catalogued source only; no media interpretation performed'}}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    if args.apply_local_admin:
        reviewed = json.loads(args.reviewed_manifest.read_text(encoding='utf-8'))
        if (reviewed.get('collection') != COLLECTION or reviewed.get('records') != len(records)
                or reviewed.get('records_sha256') != manifest['records_sha256']
                or sha((args.reviewed_manifest.parent / 'records.jsonl').read_bytes()) != reviewed['records_sha256']):
            raise ValueError('Source corpus changed since review; vault was not modified')
        import os
        from security.firebase_auth import get_admin_principal
        if get_admin_principal(key=os.environ.get('AI_BS_ADMIN_KEY', '')) != 'local_admin':
            raise PermissionError('Configured operator credentials are required for local-admin import')
        db = ROOT / 'backend/stehouwer_vault.db'
        # SQLite online backup includes WAL state; never copy only the live DB file.
        with closing(sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(args.output / 'vault_before.sqlite3')) as backup:
                source.backup(backup)
        receipt = {'owner_scope': 'local_admin', 'weight_training': False,
                   'reviewed_records_sha256': manifest['records_sha256'],
                   'records': import_records(records, db, 'local_admin')}
        (args.output / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'records': len(records), 'counts': dict(corpus.counts),
                      'applied_local_admin': args.apply_local_admin}, sort_keys=True))


if __name__ == '__main__':
    main()
