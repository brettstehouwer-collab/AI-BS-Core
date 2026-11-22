"""Authenticated, project-scoped native writer I/O; no service startup or fallback data."""
from __future__ import annotations

import hashlib
import copy
import json
import os
import re
import uuid
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import httpx
from native_studio.local_connection import LocalConnectionError, local_service_headers
from native_studio.rich_screenplay_draft import (NativeRichDraft, RichDraftError,
    MAX_RICH_FIELD_BYTES, MAX_RECOVERY_FILE_BYTES)


class ScreenplayError(RuntimeError):
    pass


def project_name(value: str) -> str:
    name = value.strip()
    if (not name or name in {'.', '..'}
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or name.endswith(('.', ' '))
            or name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}):
        raise ScreenplayError('Choose a valid single Windows project folder name.')
    return name


class ScreenplayClient:
    """Credentials are supplied at request time; redirects/proxy environment are disabled."""
    def __init__(self, *, transport=None, creative_session=None):
        self._transport = transport
        self._creative_session = creative_session

    def _request(self, method, route, **kwargs):
        try:
            if self._creative_session is not None:
                from native_studio.creative_session import CreativeSessionError
                operations = {('GET','/api/screenwriting/read'):'read',
                    ('POST','/api/screenwriting/write'):'save',
                    ('GET','/api/screenwriting/export/fdx'):'export_fdx',
                    ('GET','/api/screenwriting/export/pdf'):'export_pdf'}
                operation=operations.get((method,route))
                if operation is None:
                    raise ScreenplayError('This delegated project connection does not authorize that operation.')
                payload=kwargs.get('params') if method=='GET' else kwargs.get('json')
                if not isinstance(payload,dict):
                    raise ScreenplayError('An explicit connected project is required.')
                try:
                    if self._creative_session.owned_channel:
                        response=self._creative_session.channel_request(method,route,payload)
                        if response.status_code>=300:
                            messages={409:'The project changed. Keep this draft and reload before saving again.',
                                428:'Reload the current screenplay revision before saving.'}
                            raise ScreenplayError(messages.get(response.status_code,
                                'The connected backend did not confirm the operation. Your draft is retained.'))
                        return response
                    headers=self._creative_session.headers(project=payload.get('project_name'),operation=operation)
                except CreativeSessionError:
                    raise ScreenplayError('Project authorization expired or was refused. Your draft is retained.') from None
            else:
                headers = local_service_headers()
        except LocalConnectionError as error:
            raise ScreenplayError(str(error)) from None
        if not headers:
            raise ScreenplayError('The private local connection is not ready. Start the local AI-BS service and try again; no API key entry is required.')
        try:
            with httpx.Client(base_url='http://127.0.0.1:8080', timeout=30,
                              trust_env=False, follow_redirects=False,
                              transport=self._transport) as client:
                response = client.request(method, route, headers=headers, **kwargs)
        except httpx.HTTPError:
            raise ScreenplayError('The local backend did not confirm this request. Your draft is retained.') from None
        if response.status_code >= 300:
            messages = {401: 'Native studio authentication was refused.',
                        403: 'Native studio access was refused.',
                        404: 'The requested project or backend feature was not found.',
                        409: 'The project changed or already exists. Retain this draft and reload before saving again.',
                        422: 'The backend rejected the request or project data.',
                        428: 'The backend requires a current screenplay revision.'}
            raise ScreenplayError(messages.get(response.status_code,
                                  f'The backend did not confirm success (HTTP {response.status_code}).'))
        return response

    def _json(self, method, route, **kwargs):
        try:
            value = self._request(method, route, **kwargs).json()
        except (ValueError, UnicodeError):
            raise ScreenplayError('The backend returned an invalid response.') from None
        if not isinstance(value, dict):
            raise ScreenplayError('The backend returned an invalid response.')
        return value

    def projects(self):
        data = self._json('GET', '/api/screenwriting/projects')
        names = data.get('projects')
        if not isinstance(names, list) or any(not isinstance(n, str) for n in names):
            raise ScreenplayError('The project catalog is invalid.')
        return {'projects': [project_name(n) for n in names], 'current': data.get('current')}

    def read(self, name):
        name = project_name(name)
        data = self._json('GET', '/api/screenwriting/read', params={'project_name': name})
        if (data.get('project') != name or not isinstance(data.get('content'), str)
                or not isinstance(data.get('revision'), str) or not data['revision']):
            raise ScreenplayError('The backend did not return a project-scoped revision. The editor was preserved.')
        _workflow_state(data)
        if data.get('fdx_document') is not None:
            try:
                NativeRichDraft(data)
            except RichDraftError as error:
                raise ScreenplayError(str(error)) from None
        return data

    def save(self, name, content, revision, *, expected_workflow_revision=None, fdx_document=None):
        name = project_name(name)
        if not revision:
            raise ScreenplayError('Load a confirmed project revision before saving.')
        payload = {'project_name': name, 'content': content, 'expected_revision': revision}
        if fdx_document is not None:
            payload['fdx_document'] = fdx_document
        if expected_workflow_revision is not None:
            if type(expected_workflow_revision) is not int or expected_workflow_revision < 0:
                raise ScreenplayError('Reload the project workflow revision before saving.')
            payload['expected_workflow_revision'] = expected_workflow_revision
        data = self._json('POST', '/api/screenwriting/write', json=payload)
        if (data.get('project') != name or not isinstance(data.get('revision'), str)
                or not data['revision'] or data.get('status') != 'success'):
            raise ScreenplayError('The backend did not confirm the saved project revision.')
        return data

    def create(self, name, author, template):
        name = project_name(name)
        data = self._json('POST', '/api/screenwriting/projects/create', json={
            'project_name': name, 'author': author, 'template': template})
        if data.get('status') != 'success' or (data.get('project') or data.get('current')) != name:
            raise ScreenplayError('Project creation was not confirmed. Refresh the catalog before retrying.')
        return name

    def create_rich_working_copy(self, name, new_name, content, revision):
        name,new_name=project_name(name),project_name(new_name)
        data=self._json('POST','/api/screenwriting/projects/fdx-working-copy',json={
            'project_name':name,'new_project_name':new_name,'content':content,
            'expected_revision':revision,'request_id':uuid.uuid4().hex})
        if (data.get('status')!='success' or data.get('project')!=new_name
                or data.get('revision')!=hashlib.sha256(content.encode('utf-8')).hexdigest()):
            raise ScreenplayError('The separate working copy was not confirmed. Your full draft and original source were retained.')
        return new_name

    def import_file(self, name, file_path, *, pdf_mode='preserved'):
        name = project_name(name)
        path = Path(file_path)
        if path.stat().st_size > 25 * 1024 * 1024:
            raise ScreenplayError('This import exceeds the 25 MB native import limit.')
        ext = path.suffix.lower()
        if ext in {'.fountain', '.txt'}:
            content = path.read_text(encoding='utf-8-sig')
        elif ext == '.fdx':
            raw = path.read_bytes()
            if not raw or len(raw) > 16 * 1024 * 1024:
                raise ScreenplayError('Preserved FDX import requires a nonempty file no larger than16 MiB.')
            declaration_probe = raw.upper().replace(b'\x00', b'')
            if b'<!DOCTYPE' in declaration_probe or b'<!ENTITY' in declaration_probe:
                raise ScreenplayError('FDX files with DTD or entity declarations cannot be imported.')
            root = ElementTree.fromstring(raw)
            if root.tag != 'FinalDraft' or root.find('Content') is None:
                raise ScreenplayError('This file is not a Final Draft screenplay.')
            expected = hashlib.sha256(raw).hexdigest()
            data = self._json('POST', '/api/screenwriting/projects/import-fdx-source',
                data={'project_name':name,'request_id':uuid.uuid4().hex,'source_sha256':expected},
                files={'file':(path.name,raw,'application/xml')})
            source = data.get('source',{})
            if (data.get('status')!='success' or data.get('project')!=name
                    or source.get('format')!='fdx' or source.get('sha256')!=expected or source.get('bytes')!=len(raw)):
                raise ScreenplayError('The backend did not confirm the original FDX identity. Refresh the catalog before retrying; the source file was retained.')
            return name
        elif ext == '.pdf':
            raw = path.read_bytes()
            if not raw.startswith(b'%PDF-') or len(raw) > 16 * 1024 * 1024:
                raise ScreenplayError('Choose a PDF no larger than16 MiB for retained source intake.')
            if pdf_mode not in {'preserved','text_working_copy'}:
                raise ScreenplayError('Choose a preserved PDF project or an explicit text working copy.')
            expected = hashlib.sha256(raw).hexdigest()
            attachment = self._json('POST','/api/chat/attach',files={'file':(path.name,raw,'application/pdf')})
            source = attachment.get('file',{})
            if (attachment.get('status') != 'success' or not isinstance(source,dict)
                    or source.get('source_sha256') != expected
                    or not isinstance(source.get('source_id'),str) or not re.fullmatch('[a-f0-9]{32}',source['source_id'])
                    or source.get('parsing_status') != 'complete'
                    or source.get('indexing_status') != 'lexical_chunks_indexed'
                    or source.get('retrieval_status') != 'source_passage_readback_verified'):
                raise ScreenplayError('PDF parsing, indexing and source readback were not confirmed. The input file was retained.')
            if pdf_mode == 'preserved':
                if source.get('source_layout_available') is not True:
                    raise ScreenplayError('The PDF source was retained and indexed, but its layout is unsupported. Choose PDF text working copy to import selectable text with new pagination.')
                data = self._json('POST','/api/screenwriting/projects/import-pdf-source',json={
                    'project_name':name,'source_id':source['source_id'],'source_sha256':expected,'request_id':uuid.uuid4().hex})
                if (data.get('status') != 'success' or data.get('project') != name
                        or not isinstance(data.get('source'),dict) or data['source'].get('sha256') != expected):
                    raise ScreenplayError('The preserved PDF project was not confirmed. Refresh projects before retrying; the source was retained.')
                return name
            from pypdf import PdfReader
            try:
                content = '\n\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(raw)).pages)
            except Exception:
                raise ScreenplayError('Selectable PDF text could not be read. The original file and retained source were preserved.') from None
            if not content.strip():
                raise ScreenplayError('No selectable PDF text was found. OCR is required for this file.')
        else:
            raise ScreenplayError('Import supports Fountain, UTF-8 text, Final Draft XML, or selectable-text PDF.')
        data = self._json('POST', '/api/screenwriting/projects/import', json={'project_name': name, 'content': content})
        if data.get('status') != 'success' or data.get('project') != name:
            raise ScreenplayError('Import was not confirmed. Refresh the catalog before retrying.')
        return name

    def adapt(self, file_path, name, format_target, config):
        name = project_name(name)
        contract = self._json('GET', '/api/screenplay/adapt/capabilities')
        if contract.get('contract') != 'create-only-v1' or contract.get('create_only') is not True:
            raise ScreenplayError('The backend must support protected, create-only adaptation before this action can run.')
        path = Path(file_path)
        if not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
            raise ScreenplayError('Choose an existing manuscript of at most 100 MB.')
        formats = {'feature': 'Feature Film (Spec Script)', 'tv_drama': 'TV Pilot (1-Hour Drama)',
                   'tv_comedy': 'TV Pilot (30-Minute Sitcom)', 'limited': 'Limited Series',
                   'director': "Director's Shooting Script", 'stage_play': 'Theatrical Stage Play',
                   'audio_drama': 'Audio Drama', 'short': 'Short Film'}
        with path.open('rb') as stream:
            data = self._json('POST', '/api/screenplay/adapt',
                files={'file': (path.name, stream, 'application/octet-stream')},
                data={'project_name': name, 'adaptation_type': formats.get(format_target, format_target),
                      'book_style': config.get('book_style', 'Fiction Novel / Narrative'), 'force': 'false'})
        if (data.get('status') != 'success' or data.get('contract') != 'create-only-v1'
                or (data.get('project_name') or data.get('project')) != name
                or not isinstance(data.get('job_id'), str)
                or not re.fullmatch(r'[0-9a-f]{32}', data['job_id'])):
            raise ScreenplayError('Adaptation acceptance was not confirmed. Check its status before retrying.')
        return data

    def adaptation_status(self, name):
        return self._json('GET', '/api/screenplay/adapt/status', params={'project_name': project_name(name)})

    def export(self, name, fmt, revision, *, layout=None):
        if (fmt not in {'fountain','pdf','fdx'} or layout not in (None,'source','professional','reflow','typed-professional')
                or layout=='typed-professional' and fmt!='pdf'
                or fmt=='fountain' and layout is not None
                or self._creative_session is not None and fmt=='fountain'):
            raise ScreenplayError('Choose an authorized export format and explicit layout.')
        before = self.read(name)
        if before['revision'] != revision:
            raise ScreenplayError('The screenplay changed before export. Your draft is retained.')
        if fmt == 'fountain':
            payload = before['content'].encode('utf-8')
        elif fmt in {'pdf', 'fdx'}:
            parameters={'project_name':name,'expected_revision':revision}
            if layout is not None:parameters['layout']=layout
            response = self._request('GET', '/api/screenwriting/export/' + fmt, params=parameters)
            payload = response.content
            if layout=='typed-professional':
                headers=response.headers
                if (headers.get('X-AI-BS-Layout')!='typed-professional'
                        or headers.get('X-AI-BS-Profile')!='typed-fdx-professional-courier12-v1'
                        or headers.get('X-AI-BS-Renderer')!='aibs_typed_fdx_pdf_v1'
                        or headers.get('X-AI-BS-Artifact-SHA256')!=hashlib.sha256(payload).hexdigest()
                        or not re.fullmatch(r'[1-9][0-9]{0,3}',headers.get('X-AI-BS-PDF-Page-Count',''))):
                    raise ScreenplayError('The typed professional PDF receipt was not confirmed; no export was written.')
            if fmt == 'pdf' and not payload.startswith(b'%PDF-'):
                raise ScreenplayError('The backend did not return a real PDF.')
            if fmt == 'fdx' and ElementTree.fromstring(payload).tag != 'FinalDraft':
                raise ScreenplayError('The backend did not return a Final Draft document.')
        else:
            raise ScreenplayError('Unsupported export format.')
        if self.read(name)['revision'] != revision:
            raise ScreenplayError('The screenplay changed during export. Retry after reviewing the host version.')
        return payload


def write_new_export(path, payload):
    """An export must never overwrite a manuscript, an earlier export, or a link target."""
    with Path(path).open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _no_reparse_components(path):
    """Reject redirected roots before any recovery directory or file is created."""
    for component in (path, *path.parents):
        if component.is_symlink() or getattr(component, 'is_junction', lambda: False)():
            raise ScreenplayError('Recovery storage cannot contain symbolic links or junctions.')


def _private_recovery_directory(path, store):
    path, store = Path(path).absolute(), Path(store).absolute()
    _no_reparse_components(path)
    if path.parent != store:
        raise ScreenplayError('Recovery must stay directly inside its intended store.')
    store.mkdir(parents=True, exist_ok=True)
    _no_reparse_components(path)
    if path.resolve().parent != store.resolve():
        raise ScreenplayError('Recovery storage resolved outside its intended store.')
    if os.name != 'nt':
        raise ScreenplayError('Private native recovery requires Windows filesystem permissions.')

    # Create the new per-profile directory with its DACL already applied. Existing
    # folders are inspected only; never take ownership or rewrite their permissions.
    import ctypes
    from ctypes import wintypes
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    advapi.GetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR), ctypes.c_void_p]

    class SecurityAttributes(ctypes.Structure):
        _fields_ = [('nLength', wintypes.DWORD), ('lpSecurityDescriptor', ctypes.c_void_p), ('bInheritHandle', wintypes.BOOL)]
    kernel.CreateDirectoryW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(SecurityAttributes)]
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ScreenplayError('Could not inspect the current Windows recovery identity.')
    try:
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token, 1, buffer, size.value, ctypes.byref(size)):
            raise ScreenplayError('Could not inspect the current Windows recovery identity.')
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p)).contents.value
        sid_string = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(sid_string)):
            raise ScreenplayError('Could not inspect the current Windows recovery identity.')
        try:
            user_sid = sid_string.value
        finally:
            kernel.LocalFree(ctypes.cast(sid_string, ctypes.c_void_p))
    finally:
        kernel.CloseHandle(token)
    allowed_aces = {f'A;OICI;FA;;;{identity}' for identity in ('SY', 'BA', user_sid)}
    desired = 'D:P' + ''.join(f'({ace})' for ace in sorted(allowed_aces))
    descriptor = ctypes.c_void_p()
    if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(desired, 1, ctypes.byref(descriptor), None):
        raise ScreenplayError('Could not prepare private recovery permissions.')
    try:
        # Windows canonicalizes well-known account SIDs (for example the local
        # Administrator SID becomes LA). Compare both descriptors in the same
        # canonical representation, retaining the exact protected allowlist.
        canonical = wintypes.LPWSTR()
        if not advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 4, ctypes.byref(canonical), None):
            raise ScreenplayError('Could not verify expected private recovery permissions.')
        try:
            allowed_aces = set(re.findall(r'\(([^()]*)\)', canonical.value))
        finally:
            kernel.LocalFree(ctypes.cast(canonical, ctypes.c_void_p))
        attributes = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
        if not kernel.CreateDirectoryW(str(path), ctypes.byref(attributes)):
            if ctypes.get_last_error() != 183:  # ERROR_ALREADY_EXISTS
                raise ScreenplayError('Could not create the private recovery folder.')
    finally:
        kernel.LocalFree(descriptor)
    _no_reparse_components(path)
    if not path.is_dir() or path.resolve().parent != store.resolve():
        raise ScreenplayError('Recovery folder did not stay inside its intended store.')
    size = wintypes.DWORD()
    advapi.GetFileSecurityW(str(path), 4, None, 0, ctypes.byref(size))
    security = ctypes.create_string_buffer(size.value)
    if not advapi.GetFileSecurityW(str(path), 4, security, size.value, ctypes.byref(size)):
        raise ScreenplayError('Could not verify private recovery permissions.')
    actual = wintypes.LPWSTR()
    if not advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW(security, 1, 4, ctypes.byref(actual), None):
        raise ScreenplayError('Could not verify private recovery permissions.')
    try:
        sddl = actual.value
    finally:
        kernel.LocalFree(ctypes.cast(actual, ctypes.c_void_p))
    aces = re.findall(r'\(([^()]*)\)', sddl)
    if not sddl.startswith('D:P') or len(aces) != len(allowed_aces) or set(aces) != allowed_aces:
        raise ScreenplayError('The existing recovery folder is not private. Its permissions were left unchanged; choose a protected folder before closing.')


def _workflow_state(data, *, required=False):
    fields = ('initialized', 'workflow_revision', 'active_branch', 'pending_operation')
    if not any(field in data for field in fields):
        if required:
            raise ScreenplayError('The backend omitted the workflow revision. Retain this draft and reload.')
        return None, None, None, None
    initialized, epoch, branch, pending = (data.get(field) for field in fields)
    if (type(initialized) is not bool or type(epoch) is not int or epoch < 0
            or not isinstance(branch, str) or not branch.strip() or branch != branch.strip()
            or 'pending_operation' not in data
            or (not initialized and (epoch != 0 or pending is not None))):
        raise ScreenplayError('Invalid project workflow metadata. Your draft is retained.')
    if pending is not None and (not isinstance(pending, dict)
            or pending.get('kind') not in {'WRITE', 'SWITCH'}
            or any(not isinstance(pending.get(key), str) or not pending[key]
                   for key in ('id', 'source_branch', 'target_branch', 'before_revision', 'after_revision'))):
        raise ScreenplayError('Invalid pending workflow operation. Preserve the project for recovery.')
    return initialized, epoch, branch, dict(pending) if pending is not None else None


class DraftSession:
    def __init__(self, recovery_root=None):
        self.project = None
        self.revision = None
        self.initialized = None
        self.workflow_revision = None
        self.active_branch = None
        self.pending_operation = None
        self.rich = None
        self._content = ''
        self.baseline = ''
        self.uncertain = False
        if recovery_root is None:
            # The default store retains its existing per-home profile partition.
            if os.name == 'nt':
                from native_studio.windows_profile import current_user_profile_directory, WindowsProfileError
                try:
                    profile_path = current_user_profile_directory()
                except WindowsProfileError:
                    raise ScreenplayError('The Windows recovery profile could not be confirmed. Keep the current draft.') from None
            else:
                profile_path = Path.home()
            profile = hashlib.sha256(str(profile_path).casefold().encode('utf-8')).hexdigest()[:16]
            self.recovery_root = Path(r'C:\AI-BS\saved_data\native_screenplay_recovery') / profile
        else:
            # Explicit isolated roots must not need, inherit or fall back to home.
            try:
                explicit_root = os.fspath(recovery_root)
            except TypeError:
                raise ScreenplayError('An explicit recovery path must be a nonempty string or path.') from None
            if not isinstance(explicit_root, str) or not explicit_root.strip():
                raise ScreenplayError('An explicit recovery path must be a nonempty string or path.')
            self.recovery_root = Path(explicit_root)
        self._recovery_store = self.recovery_root.parent
        self.recovery_path = None
        self._recovery_fingerprint = None
        self._recovery_payload_hash = None
        self.recovery_scope = None
        self._confirmed_data = None

    @property
    def dirty(self):
        return self.content != self.baseline

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        if self.rich is not None:
            self.rich.edit(value)
        self._content = value

    def capture_rich_snapshot(self):
        try:
            return self.rich.capture() if self.rich is not None else None
        except RichDraftError as error:
            raise ScreenplayError(str(error)) from None

    def load(self, data):
        workflow = _workflow_state(data)
        try:
            rich = NativeRichDraft(data) if data.get('fdx_document') is not None else None
        except RichDraftError as error:
            raise ScreenplayError(str(error)) from None
        self.project = data['project']
        self.revision = data['revision']
        self.rich = rich
        self._content = self.baseline = data['content']
        (self.initialized, self.workflow_revision, self.active_branch, self.pending_operation) = workflow
        self.uncertain = False

        self._confirmed_data = copy.deepcopy(data)

    def saved(self, submitted, data, submitted_document=None):
        try:
            if (data.get('status') != 'success' or data.get('project') != self.project
                    or not isinstance(data.get('revision'), str) or not data['revision']):
                raise ScreenplayError('The backend did not confirm this project save. Your draft is retained.')
            workflow = _workflow_state(data, required=self.workflow_revision is not None)
            initialized, epoch, branch, pending = workflow
            if pending is not None or self.pending_operation is not None:
                raise ScreenplayError('An interrupted workflow requires explicit recovery before saving.')
            unchanged = data.get('unchanged') is True
            normalize = lambda value: value.replace('\r\n', '\n').replace('\r', '\n')
            if unchanged and (data['revision'] != self.revision
                              or normalize(submitted) != normalize(self.baseline)):
                raise ScreenplayError('The unchanged save acknowledgment does not match this draft.')
            if (self.rich is None and normalize(submitted) != normalize(self.baseline)
                    and data['revision'] == self.revision):
                raise ScreenplayError('The backend did not confirm a new saved revision. Your draft is retained.')
            if self.workflow_revision is not None:
                expected = self.workflow_revision + (1 if self.initialized and not unchanged else 0)
                if (epoch != expected or branch != self.active_branch or initialized != self.initialized):
                    raise ScreenplayError('The save acknowledgment has an unexpected workflow revision or branch.')
            elif initialized:
                raise ScreenplayError('Reload the initialized workflow before saving again.')
            if self.rich is not None:
                if submitted_document is None or data.get('content') != submitted:
                    raise ScreenplayError('The backend omitted the saved rich snapshot. Your draft is retained.')
                self.rich.acknowledge(data, submitted_document)
            elif data.get('fdx_document') is not None or submitted_document is not None:
                raise ScreenplayError('The project document format changed during this save. Retain this draft and reload.')
        except (ScreenplayError, RichDraftError) as error:
            self.uncertain = True
            raise ScreenplayError(str(error)) from None
        self.revision = data['revision']
        self.baseline = submitted
        (self.initialized, self.workflow_revision, self.active_branch, self.pending_operation) = workflow
        self.uncertain = False

        self._confirmed_data = copy.deepcopy({**(self._confirmed_data or {}), **data, 'content': submitted})

    def restore(self, path):
        """Restore locally against a fresh confirmed host snapshot; never save/replay."""
        if (not isinstance(self.recovery_scope, str)
                or not re.fullmatch(r'[a-f0-9]{64}', self.recovery_scope)
                or self._confirmed_data is None or self.pending_operation is not None
                or self.uncertain):
            raise ScreenplayError('Open the verified connected project before restoring a recovery copy.')
        try:
            target = Path(path).absolute()
        except (TypeError, ValueError, OSError):
            raise ScreenplayError('Choose a valid private recovery file.') from None
        root = self.recovery_root.absolute()
        if target.parent != root or target.suffix != '.json':
            raise ScreenplayError('Choose a JSON copy directly inside this private recovery folder.')
        _private_recovery_directory(root, self._recovery_store)
        _no_reparse_components(target)
        try:
            expected_path = str(target.resolve(strict=True))
            with target.open('rb') as stream:
                info = os.fstat(stream.fileno())
                # Check the opened handle's actual path, not just its input name.
                if os.name == 'nt':
                    import ctypes
                    import msvcrt
                    from ctypes import wintypes
                    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
                    buffer = ctypes.create_unicode_buffer(32768)
                    size = kernel.GetFinalPathNameByHandleW(msvcrt.get_osfhandle(stream.fileno()), buffer, len(buffer), 0)
                    actual = buffer.value.removeprefix('\\\\?\\')
                    if not size or size >= len(buffer) or os.path.normcase(actual) != os.path.normcase(expected_path):
                        raise ScreenplayError('Recovery file resolved outside the selected private location.')
                current = target.stat(follow_symlinks=False)
                if (info.st_size > MAX_RECOVERY_FILE_BYTES or info.st_nlink != 1
                        or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino)
                        or getattr(current, 'st_file_attributes', 0) & 0x400):
                    raise ScreenplayError('Recovery copy is oversized, linked or redirected.')
                raw = stream.read(MAX_RECOVERY_FILE_BYTES + 1)
            if len(raw) > MAX_RECOVERY_FILE_BYTES:
                raise ValueError('large')
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('duplicate')
                    result[key] = value
                return result
            def invalid_constant(value):
                raise ValueError('non-finite')
            record = json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=invalid_constant)
        except (OSError, ValueError, UnicodeError, RecursionError):
            raise ScreenplayError('The recovery copy could not be safely read. Existing work was retained.') from None
        expected = {'schema','project','revision','content','rich_draft','saved_at',
                    'recovery_scope','baseline','workflow'}
        workflow = [self.initialized,self.workflow_revision,self.active_branch,self.pending_operation]
        if (type(record) is not dict or set(record) != expected or type(record.get('schema')) is not int
                or record['schema'] != 3 or record['recovery_scope'] != self.recovery_scope
                or record['project'] != self.project or record['revision'] != self.revision
                or record['baseline'] != self.baseline
                or json.dumps(record['workflow'], sort_keys=True) != json.dumps(workflow, sort_keys=True)
                or not isinstance(record['content'], str)
                or not isinstance(record['saved_at'], str)
                or not re.fullmatch(r'\d{8}T\d{6}\.\d{6}Z', record['saved_at'])):
            raise ScreenplayError('This copy does not match the verified owner, source, project or host revision. It was retained unchanged.')
        try:
            record['content'].encode('utf-8', errors='strict')
        except UnicodeError:
            raise ScreenplayError('The recovery text is not valid Unicode. Existing work was retained.') from None
        try:
            if self.rich is None:
                if record['rich_draft'] is not None:
                    raise RichDraftError('The recovery document format does not match the host.')
                rich = None
            else:
                rich = NativeRichDraft.from_recovery(record['rich_draft'], self._confirmed_data, allow_large_legacy=True)
                if rich.content != record['content']:
                    raise RichDraftError('The recovery text does not match its rich document.')
        except RichDraftError as error:
            raise ScreenplayError(str(error)) from None
        # Validation must finish before preserving/replacing the current draft.
        if self.dirty:
            self.preserve()
        self.rich = rich
        self._content = record['content']
        self.recovery_path = target
        self._recovery_fingerprint = None
        self._recovery_payload_hash = None
        return target

    def preserve(self):
        _private_recovery_directory(self.recovery_root, self._recovery_store)
        try:
            rich_state = self.rich.recovery_payload() if self.rich is not None else None
            if rich_state is not None and len(json.dumps(rich_state, ensure_ascii=False).encode('utf-8')) > MAX_RICH_FIELD_BYTES:
                rich_state = self.rich.recovery_payload(compact=True)
        except (RichDraftError, ValueError, UnicodeError, RecursionError, OverflowError):
            raise ScreenplayError('This recovery copy exceeds the supported rich history limits. Keep the draft open and save or export it separately.') from None
        if self.recovery_scope is not None and (type(self.recovery_scope) is not str or not re.fullmatch(r'[a-f0-9]{64}',self.recovery_scope)):
            raise ScreenplayError('The recovery ownership scope is invalid. Keep this draft open.')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        target = self.recovery_root / f'{stamp}_{uuid.uuid4().hex}.json'
        record={'schema': 1, 'project': self.project, 'revision': self.revision,
                'content': self.content, 'rich_draft': rich_state, 'saved_at': stamp}
        if self.recovery_scope is not None:
            record.update(schema=3,recovery_scope=self.recovery_scope,baseline=self.baseline,
                          workflow=[self.initialized,self.workflow_revision,self.active_branch,self.pending_operation])
        try:
            payload = json.dumps(record, ensure_ascii=False, indent=2).encode('utf-8')
            if len(payload) > MAX_RECOVERY_FILE_BYTES and self.rich is not None and 'format' not in rich_state:
                rich_state = self.rich.recovery_payload(compact=True)
                record['rich_draft'] = rich_state
                payload = json.dumps(record, ensure_ascii=False, indent=2).encode('utf-8')
            if len(payload) > MAX_RECOVERY_FILE_BYTES:
                raise ScreenplayError('This recovery copy exceeds 32 MiB. Keep the draft open and save or export it separately.')
            fingerprint = hashlib.sha256(json.dumps([self.project, self.revision, self.content, rich_state,
                self.recovery_scope,self.baseline,self.initialized,self.workflow_revision,self.active_branch,
                self.pending_operation], ensure_ascii=False).encode('utf-8')).hexdigest()
        except (RichDraftError, ValueError, UnicodeError, RecursionError, OverflowError):
            raise ScreenplayError('This recovery copy could not be encoded safely. Keep the draft open.') from None
        if fingerprint == self._recovery_fingerprint and self.recovery_path and self.recovery_path.is_file():
            if (not self.recovery_path.is_symlink()
                    and not getattr(self.recovery_path, 'is_junction', lambda: False)()
                    and self.recovery_path.stat().st_size <= MAX_RECOVERY_FILE_BYTES
                    and hashlib.sha256(self.recovery_path.read_bytes()).hexdigest() == self._recovery_payload_hash):
                return self.recovery_path
        # Replay only for a new receipt, never for an unchanged verified copy.
        if rich_state is not None:
            try:
                NativeRichDraft.from_recovery(rich_state, self._confirmed_data)
            except RichDraftError as error:
                raise ScreenplayError(str(error)) from None
        write_new_export(target, payload)
        self._recovery_fingerprint = fingerprint
        self._recovery_payload_hash = hashlib.sha256(payload).hexdigest()
        self.recovery_path = target
        return target
