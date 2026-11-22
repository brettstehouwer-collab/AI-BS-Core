"""Private create-only PDF intake and source-layout screenplay handoff.

The PDF is retained independently from extracted text, RAG receipts and editable
Fountain. No source text is executed and importing this module opens no store.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import tempfile
import uuid

from core.owned_vault import _owner, read_record, VaultEvidenceError, VaultRecordNotFound
from core.owned_rag_sources import ingest_source, retrieve_source_chunks
from core.personal_memory_scope import current_memory_principal

ROOT = Path(__file__).resolve().parents[2]
CACHE_ROOT = ROOT / 'state/chat_pdf_sources'
VAULT_DB_PATH = ROOT / 'backend/stehouwer_vault.db'
MAX_UPLOAD_BYTES = 16 * 1024 * 1024
MAX_PACKET_BYTES = 32 * 1024 * 1024
CONTRACT = 'owned-pdf-source-v1'
FDX_RENDERER_VERSION = 'screenplay_fdx_relative_indent_v2'


class PDFSourceError(RuntimeError):
    def __init__(self, message, status=503, *, source_id=None, source_sha256=None):
        super().__init__(message)
        self.status = status
        self.source_id = source_id
        self.source_sha256 = source_sha256


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def _plain(path):
    if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
        raise PDFSourceError('Linked PDF source storage is not supported.', 409)


def _scope(owner):
    owner = _owner(owner)
    root = CACHE_ROOT / _sha(owner.encode('utf-8'))
    for path in (CACHE_ROOT.parent, CACHE_ROOT, root):
        _plain(path)
    return root


def _source_directory(owner, source_id):
    if not isinstance(source_id, str) or not re.fullmatch(r'[a-f0-9]{32}', source_id):
        raise PDFSourceError('Invalid retained PDF source identifier.', 422)
    directory = _scope(owner) / source_id
    _plain(directory)
    return directory


def _read(path, maximum):
    _plain(path)
    try:
        with path.open('rb') as stream:
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise PDFSourceError('Retained PDF evidence exceeds its supported size.', 409)
        return raw
    except FileNotFoundError:
        raise PDFSourceError('Retained PDF source was not found for this account.', 404) from None


def _write_once(path, raw):
    for component in (path, *path.parents):
        _plain(component)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    published = False
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, prefix='.pdf-publish-', suffix='.tmp', delete=False) as stream:
            temporary_path = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            if _read(path, max(len(raw), MAX_PACKET_BYTES)) != raw:
                raise PDFSourceError('Retained PDF/import evidence conflicts; existing bytes were preserved.', 409) from None
        published = True
    finally:
        # Failed/partial temporary bytes remain evidence outside the target;
        # a complete retry can still publish the never-created final artifact.
        if published and temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass  # Complete target is committed; retained temp is evidence.


def _validate_packet(packet):
    if packet.get('schema') == 'aibs_screenplay_pdf_v1':
        from core.screenplay_pdf import validate_packet
        validate_packet(packet)
        return True
    if packet.get('schema') == 'aibs_pdf_text_source_v1':
        from core.pdf_text_source import validate_packet
        validate_packet(packet)
        return False
    raise ValueError('Unsupported retained PDF packet type')


def _parse_packet(raw):
    from core.screenplay_pdf import parse_pdf
    try:
        packet = parse_pdf(raw)
    except ValueError:
        # Ordinary text PDFs retain their established text/RAG intake without
        # claiming screenplay roles, Courier layout or faithful FDX export.
        from core.pdf_text_source import parse_pdf_text
        packet = parse_pdf_text(raw)
    preserved = _validate_packet(packet)
    return packet, preserved


def stage_pdf(raw, owner, filename):
    """Commit a complete owner source only after parse/index/retrieval readback."""
    owner = _owner(owner)
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise PDFSourceError('PDF is empty or exceeds16MiB.', 413)
    if (not isinstance(filename, str) or not 1 <= len(filename) <= 200
            or PureWindowsPath(filename).name != filename or any(ord(char) < 32 for char in filename)):
        raise PDFSourceError('PDF filename must be a basename of1-200characters.', 422)
    source_id, digest = uuid.uuid4().hex, _sha(raw)
    directory = _source_directory(owner, source_id)
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir()
    _write_once(directory / 'original.pdf', raw)
    try:
        packet, preserved = _parse_packet(raw)
        if packet['source_sha256'] != digest or packet['source_bytes'] != len(raw):
            raise ValueError('PDF source evidence mismatch')
        packet_bytes = _json(packet)
        if len(packet_bytes) > MAX_PACKET_BYTES:
            raise ValueError('PDF page packet exceeds supported size')
        derived = packet['rag_text'].encode('utf-8')
        fountain = packet['fountain_text'].encode('utf-8')
        _write_once(directory / 'packet.json', packet_bytes)
        _write_once(directory / 'derived.txt', derived)
        _write_once(directory / 'source.fountain', fountain)
        # A derived UTF-8 source uses the existing lexical contract. Its hash is
        # distinct from the original PDF fingerprint and never replaces it.
        index = ingest_source(VAULT_DB_PATH, owner, packet['rag_text'],
            source_name='context_' + source_id + '.txt', source_sha256=_sha(derived))
        hits = retrieve_source_chunks(VAULT_DB_PATH, owner, 'context_' + source_id + '.txt', limit=2)
        matching = [hit for hit in hits if hit['id'] == index['vault_item_id']
                    and hit['source_sha256'] == _sha(derived)
                    and _sha(derived[hit['byte_start']:hit['byte_end']]) == hit['chunk_sha256']]
        if not matching:
            raise VaultEvidenceError('Derived source retrieval was not confirmed')
        manifest = dict(contract=CONTRACT, owner=owner, source_id=source_id,
            source_sha256=digest, source_bytes=len(raw), filename=filename,
            packet_sha256=_sha(packet_bytes), derived_sha256=_sha(derived),
            canonical_sha256=_sha(fountain), page_count=packet['page_count'],
            body_page_count=packet['body_page_count'], title_page_count=packet['title_page_count'],
            source_layout_available=preserved, profile='preserved_screenplay' if preserved else 'generic_pdf_text',
            unclassified_page_count=packet.get('unclassified_page_count', 0),
            printed_page_labels=[page.get('printed_label') for page in packet['pages'] if not page.get('is_title')],
            created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            rag_receipt=dict(vault_item_id=index['vault_item_id'], derived_source_sha256=_sha(derived),
                source_name='context_' + source_id + '.txt',
                chunk_count=index['chunk_count'], retrieval_hits=len(matching), search_type='lexical_scan',
                model_context_expanded=False))
        # One final create-only marker commits all independently retained files.
        _write_once(directory / 'manifest.json', _json(manifest))
        return attachment_receipt(manifest)
    except Exception as error:
        _write_once(directory / 'failure.json', _json(dict(source_id=source_id, source_sha256=digest,
            original_retained=True, error_type=type(error).__name__, committed=False)))
        status = 422 if isinstance(error, (ValueError, KeyError, UnicodeError)) else 503
        raise PDFSourceError('PDF parsing/indexing was not confirmed; the original upload was retained.', status,
                             source_id=source_id, source_sha256=digest) from error


def attachment_receipt(manifest):
    return dict(name=manifest['filename'], size=manifest['source_bytes'], ext='.pdf', is_image=False, path='',
        content='[RETAINED_PDF_SOURCE source_id=' + manifest['source_id'] +
                ' sha256=' + manifest['source_sha256'] + ']\n'
                'Original PDF and extracted text are retained privately. This attachment reference is not the full PDF text.',
        source_id=manifest['source_id'], source_sha256=manifest['source_sha256'],
        rag_source_name='context_' + manifest['source_id'] + '.txt',
        page_count=manifest['page_count'], body_page_count=manifest['body_page_count'],
        profile=manifest['profile'], unclassified_page_count=manifest['unclassified_page_count'],
        title_page_count=manifest['title_page_count'], parsing_status='complete',
        indexing_status='lexical_chunks_indexed', retrieval_status='source_passage_readback_verified',
        rag_receipt=manifest['rag_receipt'], source_layout_available=manifest['source_layout_available'])


def read_source(owner, source_id, expected_sha256):
    owner = _owner(owner)
    directory = _source_directory(owner, source_id)
    try:
        manifest = json.loads(_read(directory / 'manifest.json', 65536))
        if (manifest.get('contract') != CONTRACT or manifest.get('owner') != owner or
                manifest.get('source_id') != source_id):
            raise PDFSourceError('Retained PDF source was not found for this account.', 404)
        if not re.fullmatch(r'[a-f0-9]{64}', expected_sha256 or '') or manifest['source_sha256'] != expected_sha256:
            raise PDFSourceError('The PDF source fingerprint changed; existing source was preserved.', 409)
        original = _read(directory / 'original.pdf', MAX_UPLOAD_BYTES)
        packet_raw = _read(directory / 'packet.json', MAX_PACKET_BYTES)
        derived = _read(directory / 'derived.txt', 16 * 1024 * 1024)
        fountain = _read(directory / 'source.fountain', 16 * 1024 * 1024)
        for raw, expected in ((original, expected_sha256), (packet_raw, manifest['packet_sha256']),
                              (derived, manifest['derived_sha256']), (fountain, manifest['canonical_sha256'])):
            if _sha(raw) != expected:
                raise PDFSourceError('Retained PDF evidence changed; source-layout use was stopped.', 409)
        packet = json.loads(packet_raw)
        preserved = _validate_packet(packet)
        if preserved != manifest.get('source_layout_available', True):
            raise PDFSourceError('Retained PDF source profile evidence changed.', 409)
        if (packet['source_sha256'] != expected_sha256 or packet['rag_text'].encode('utf-8') != derived
                or packet['fountain_text'].encode('utf-8') != fountain
                or len(original) != manifest['source_bytes'] or len(original) != packet['source_bytes']
                or any(manifest[key] != packet[key] for key in ('page_count', 'body_page_count', 'title_page_count'))):
            raise PDFSourceError('Retained PDF packet does not match its source.', 409)
        record = read_record(VAULT_DB_PATH, owner, manifest['rag_receipt']['vault_item_id'], include_legacy=False)
        if record['content_sha256'] != manifest['derived_sha256'] or record['content'].encode('utf-8') != derived:
            raise PDFSourceError('Derived PDF index readback did not match retained source.', 409)
        return manifest, packet, original
    except (ValueError, KeyError, TypeError, UnicodeError, VaultEvidenceError, VaultRecordNotFound) as error:
        raise PDFSourceError('Retained PDF source evidence is invalid; existing files were preserved.', 409) from error


def project_fence(directory):
    path = directory / 'source_pdf.json'
    if not path.exists() and not path.is_symlink():
        return None
    try:
        fence = json.loads(_read(path, 65536))
        if fence.get('contract') != CONTRACT or not isinstance(fence.get('owner'), str):
            raise ValueError('Invalid source project fence')
        return fence
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        raise PDFSourceError('Source project ownership evidence is invalid; files were preserved.', 409) from error


def require_project_owner(directory, owner=None):
    fence = project_fence(directory)
    if fence is not None and fence['owner'] != (owner or current_memory_principal()):
        raise PDFSourceError('This source-backed project is not available for the signed-in account.', 403)
    return fence


def import_project(directory, owner, source_id, source_sha256, request_id):
    """Caller holds the existing same-store project lock; publish by rename."""
    owner = _owner(owner)
    if not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9]{32}', request_id):
        raise PDFSourceError('A32-character import request identifier is required.', 422)
    manifest, packet, original = read_source(owner, source_id, source_sha256)
    if not manifest.get('source_layout_available', True):
        raise PDFSourceError('This PDF supports text/RAG intake but has no qualified source-layout screenplay profile. Use explicit book adaptation or another import workflow.', 422)
    request = dict(contract=CONTRACT, owner=owner, project=directory.name,
                   source_id=source_id, source_sha256=source_sha256, request_id=request_id)
    operation = _scope(owner) / 'imports' / request_id
    for path in (operation.parent, operation):
        _plain(path)
    operation.mkdir(parents=True, exist_ok=True)
    _write_once(operation / 'request.json', _json(request))
    if directory.exists():
        fence = require_project_owner(directory, owner)
        if fence is None or any(fence.get(key) != value for key, value in request.items()):
            raise PDFSourceError('A project with that name already exists. Choose a new import name.', 409)
        _verify_project_artifacts(directory, fence)
        return _import_receipt(directory, fence, True)
    stage = operation / 'project'
    _plain(stage)
    stage.mkdir(exist_ok=True)
    from core.screenplay_pdf import to_fdx, to_preserved_pdf
    fdx, rendered_pdf = to_fdx(packet), to_preserved_pdf(packet)
    outputs = {'screenplay.fountain': packet['fountain_text'].encode('utf-8'),
               'original.pdf': original, 'source_packet.json': _json(packet),
               directory.name + '.fdx': fdx,
               'source_exports/layout.fdx': fdx, 'source_exports/layout.pdf': rendered_pdf}
    artifact_sha256 = {name: _sha(raw) for name, raw in outputs.items()}
    fence = dict(**request, canonical_revision=manifest['canonical_sha256'],
        packet_sha256=manifest['packet_sha256'], page_count=manifest['page_count'],
        body_page_count=manifest['body_page_count'], title_page_count=manifest['title_page_count'],
        printed_page_labels=manifest['printed_page_labels'],
        artifact_sha256=artifact_sha256, source_layout_preserved=True)
    for name, raw in outputs.items():
        _write_once(stage / name, raw)
    _write_once(stage / 'source_pdf.json', _json(fence))
    _write_once(stage / 'project.json', _json(dict(title=directory.name, author='Source PDF',
        created=manifest['created_utc'], current_branch='main', characters=[], beat_videos={},
        source_pdf={key: fence[key] for key in ('source_id', 'source_sha256', 'page_count',
            'body_page_count', 'title_page_count', 'canonical_revision')}, source_layout_preserved=True)))
    _verify_project_artifacts(stage, fence)
    try:
        os.rename(stage, directory)
    except FileExistsError:
        raise PDFSourceError('A project with that name already exists. Prepared PDF import was retained.', 409) from None
    return _import_receipt(directory, fence, False)


def _verify_project_artifacts(directory, fence):
    for filename, digest in fence['artifact_sha256'].items():
        if _sha(_read(_project_artifact(directory, filename), MAX_PACKET_BYTES)) != digest:
            raise PDFSourceError('Source-backed project artifacts changed; original evidence was retained.', 409)


def _project_artifact(directory, filename):
    relative = Path(filename)
    if relative.is_absolute() or any(part in ('', '.', '..') for part in relative.parts):
        raise PDFSourceError('Project artifact must remain inside its project.', 409)
    target = directory / relative
    if not target.resolve().is_relative_to(directory.resolve()):
        raise PDFSourceError('Project artifact must remain inside its project.', 409)
    for component in (target, *target.parents):
        _plain(component)
        if component == directory:
            break
    return target


def _import_receipt(directory, fence, idempotent):
    from urllib.parse import quote
    query = '?project_name=' + quote(directory.name, safe='') + '&expected_revision=' + fence['canonical_revision']
    return dict(status='success', project=directory.name, current=directory.name,
        revision=fence['canonical_revision'], idempotent=idempotent, source_layout_preserved=True,
        source=dict(source_id=fence['source_id'], sha256=fence['source_sha256'],
                    page_count=fence['page_count'], body_page_count=fence['body_page_count']),
        exports=dict(fdx_url='/api/screenwriting/export/fdx' + query + '&layout=source',
                     pdf_url='/api/screenwriting/export/pdf' + query + '&layout=source'))


def source_project_view(directory, revision, owner=None):
    fence = require_project_owner(directory, owner)
    if fence is None:
        return {}
    _verify_preserved_artifacts(directory, fence)
    preserved = revision == fence['canonical_revision']
    result = dict(metadata=dict(source_pdf=dict(source_id=fence['source_id'], sha256=fence['source_sha256'],
        page_count=fence['page_count'], body_page_count=fence['body_page_count'],
        title_page_count=fence['title_page_count'], canonical_revision=fence['canonical_revision'],
        printed_page_labels=fence['printed_page_labels'])),
        source_layout_preserved=preserved)
    if preserved:
        packet_raw = _read(directory / 'source_packet.json', MAX_PACKET_BYTES)
        if _sha(packet_raw) != fence['packet_sha256']:
            raise PDFSourceError('Saved PDF page packet changed; source layout was not used.', 409)
        packet = json.loads(packet_raw)
        from core.screenplay_pdf import validate_packet
        validate_packet(packet)
        result['body_ast'] = [dict(id='pdf-' + str(index), type=row['type'], text=row['text'],
            startsNewPage=row.get('starts_new_page', False), sourcePage=row['page'])
            for index, row in enumerate(packet['paragraphs'])]
        result['title_page'] = packet['title_paragraphs']
    return result


def _verify_preserved_artifacts(directory, fence):
    for filename in ('original.pdf', 'source_packet.json', 'source_exports/layout.fdx', 'source_exports/layout.pdf'):
        if _sha(_read(_project_artifact(directory, filename), MAX_PACKET_BYTES)) != fence['artifact_sha256'][filename]:
            raise PDFSourceError('Preserved source artifacts changed; source-layout qualification was stopped.', 409)


def source_export(directory, revision, kind, layout, owner=None, watermark=None, expected_revision=None,
                  return_receipt=False):
    fence = require_project_owner(directory, owner)
    if fence is None:
        if layout == 'professional':
            raise PDFSourceError('Professional export currently requires an unchanged validated PDF-source project. Existing projects can use explicit legacy reflow.', 422)
        return None
    if not expected_revision:
        raise PDFSourceError('Source-backed export requires the loaded screenplay revision.', 428)
    if expected_revision != revision:
        raise PDFSourceError('The screenplay changed since export was requested. Reload or save your draft before exporting.', 409)
    _verify_preserved_artifacts(directory, fence)
    if layout == 'reflow':
        return None  # Existing renderer is explicitly requested; no fidelity claim.
    if layout not in (None, 'source', 'professional'):
        raise PDFSourceError('Choose archival source, professional, or explicit legacy reflow export.', 422)
    if revision != fence['canonical_revision']:
        raise PDFSourceError('This screenplay was edited. Source/professional packet export would omit those edits; choose explicit layout=reflow for the edited screenplay.', 409)
    if watermark:
        raise PDFSourceError('Watermarking is unavailable in archival/professional export. Choose explicit layout=reflow.', 422)

    def artifact(raw, profile, renderer, *, receipt=None, pdf_pages=None):
        if not return_receipt:
            return raw
        return dict(content=raw, layout='professional' if layout == 'professional' else 'preserved-source',
                    profile_id=profile, renderer_id=renderer, output_sha256=_sha(raw),
                    pdf_page_count=pdf_pages, profile_receipt=receipt)

    if layout == 'professional':
        try:
            from core.screenplay_pdf import validate_unchanged_fountain
            packet = json.loads(_read(_project_artifact(directory, 'source_packet.json'), MAX_PACKET_BYTES))
            canonical = _read(_project_artifact(directory, 'screenplay.fountain'), MAX_PACKET_BYTES).decode('utf-8')
            validate_unchanged_fountain(packet, canonical)
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            raise PDFSourceError('Source screenplay evidence changed; professional export was stopped.', 409) from error
        try:
            from core.screenplay_professional import to_professional_fdx, to_professional_pdf, professional_profile_receipt
            receipt = professional_profile_receipt(packet)
            renderer = receipt.get(kind + '_renderer_id') or receipt.get('renderer_id')
            if (receipt.get('profile_id') != 'us-spec-courier12-v1' or not isinstance(renderer, str)
                    or not renderer or len(renderer) > 100 or any(ord(char) < 32 for char in renderer)):
                raise ValueError('Professional profile receipt is invalid')
            raw = to_professional_fdx(packet) if kind == 'fdx' else to_professional_pdf(packet)
            if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_PACKET_BYTES:
                raise ValueError('Professional export is empty or oversized')
            pages = None
            if kind == 'pdf':
                import fitz
                with fitz.open(stream=raw, filetype='pdf') as document:
                    pages = document.page_count
                if pages < 1:
                    raise ValueError('Professional PDF contains no pages')
            elif b'<FinalDraft' not in raw[:512]:
                raise ValueError('Professional FDX document header is invalid')
            return artifact(raw, receipt['profile_id'], renderer, receipt=receipt, pdf_pages=pages)
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            raise PDFSourceError('Professional output could not be qualified. Original source and earlier exports were retained.', 422) from error
    if kind == 'fdx':
        # Immutable v01 exports remain evidence of their original generation.
        # Corrected renderer output is returned without replacing that evidence.
        try:
            from core.screenplay_pdf import to_fdx, validate_unchanged_fountain
            packet = json.loads(_read(_project_artifact(directory, 'source_packet.json'), MAX_PACKET_BYTES))
            canonical = _read(_project_artifact(directory, 'screenplay.fountain'), MAX_PACKET_BYTES).decode('utf-8')
            validate_unchanged_fountain(packet, canonical)
            return artifact(to_fdx(packet), 'source-faithful-v1', FDX_RENDERER_VERSION)
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            raise PDFSourceError('Source screenplay evidence changed; current FDX export was stopped.', 409) from error
    filename = 'source_exports/layout' + ('.fdx' if kind == 'fdx' else '.pdf')
    raw = _read(_project_artifact(directory, filename), MAX_PACKET_BYTES)
    if _sha(raw) != fence['artifact_sha256'][filename]:
        raise PDFSourceError('Preserved PDF export evidence changed; existing files were retained.', 409)
    return artifact(raw, 'source-faithful-v1', 'preserved-source-pdf-v1')
