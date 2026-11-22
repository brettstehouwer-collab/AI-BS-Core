"""Create-only adaptation jobs and durable ownership fences for the screenplay store.

All mutations run under the editor's registered store mutex. No coroutine awaits
while holding that mutex. Job records, source bytes, states and chunk outputs are
retained so cancellation/reset never requires deleting an authored file.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import subprocess
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException

CONTRACT = 'create-only-v1'
ACTIVE = {'queued', 'processing'}
ADAPTATION_TASKS = {}
_root_provider = lambda: Path('C:/AI-BS/screenplay_projects')
_store_mutex = None
_parser_factory = None


def _process_identity():
    import psutil
    return {'pid': os.getpid(), 'created_at': psutil.Process(os.getpid()).create_time()}


def _process_is_alive(identity):
    """A reused PID never inherits the previous process's adaptation ownership."""
    if (not isinstance(identity, dict) or type(identity.get('pid')) is not int
            or identity['pid'] <= 0 or not isinstance(identity.get('created_at'), (int, float))):
        return False
    try:
        import psutil
        process = psutil.Process(identity['pid'])
        return process.is_running() and abs(process.create_time() - identity['created_at']) < 0.000001
    except (OSError, ValueError, psutil.Error):
        return False


def configure_adaptation_store(root_provider, mutex, parser_factory=None):
    global _root_provider, _store_mutex, _parser_factory
    _root_provider, _store_mutex = root_provider, mutex
    _parser_factory = parser_factory


def root():
    return Path(_root_provider())


def mutex():
    # Direct/background imports must never silently bypass the editor mutex.
    if _store_mutex is None:
        from routers import screenwriting_router  # registers its same-store mutex
    if _store_mutex is None:
        raise RuntimeError('Screenplay store mutex has not been registered')
    return _store_mutex


def project_directory(project_name, must_exist=False):
    if not isinstance(project_name, str):
        raise HTTPException(400, 'Invalid project name.')
    name = project_name.strip()
    if (not name or len(name) > 120 or name.endswith('.') or name in {'.', '..'}
            or any(c in name for c in '<>:"/\\|?*') or any(ord(c) < 32 for c in name)
            or name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                *[f'COM{i}' for i in range(1, 10)], *[f'LPT{i}' for i in range(1, 10)]}):
        raise HTTPException(400, 'Invalid project name.')
    store = root()
    if store.is_symlink() or getattr(store, 'is_junction', lambda: False)():
        raise HTTPException(400, 'Project store must be a real directory.')
    directory = store / name
    if (directory.is_symlink() or getattr(directory, 'is_junction', lambda: False)()
            or directory.resolve().parent != store.resolve()):
        raise HTTPException(400, 'Project must stay inside its project store.')
    if must_exist and not directory.is_dir():
        raise HTTPException(404, 'Project does not exist.')
    return directory


def artifact(directory, relative):
    candidate = directory / relative
    if not candidate.resolve().is_relative_to(directory.resolve()):
        raise HTTPException(400, 'Job artifact must stay inside its project.')
    for component in [candidate, *candidate.parents]:
        if component == directory.parent:
            break
        if component.is_symlink() or getattr(component, 'is_junction', lambda: False)():
            raise HTTPException(400, 'Linked job artifacts are not writable.')
    return candidate


def _exclusive(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _atomic(path, raw):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, prefix='.adapt-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()  # only our uncommitted temporary file


def _read(directory):
    path = artifact(directory, 'adaptation_state.json')
    try:
        state = json.loads(path.read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        raise HTTPException(404, 'Adaptation job does not exist.')
    except (OSError, ValueError, UnicodeError):
        raise HTTPException(409, 'Adaptation state is invalid; original bytes preserved.')
    if not isinstance(state, dict):
        raise HTTPException(409, 'Adaptation state is invalid; original bytes preserved.')
    return state


def _persist(directory, state):
    """Archive the exact previous state before replacing the current pointer."""
    path = artifact(directory, 'adaptation_state.json')
    history_id = state.get('job_id') or 'legacy'
    if not isinstance(history_id, str) or not (history_id == 'legacy' or len(history_id) == 32 and all(c in '0123456789abcdef' for c in history_id)):
        raise HTTPException(409, 'Invalid adaptation job identity.')
    folder = artifact(directory, f'adaptation_history/{history_id}/states')
    folder.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _exclusive(artifact(directory, f'adaptation_history/{history_id}/states/{uuid.uuid4().hex}.json'), path.read_bytes())
    updated = dict(state, updated_at=datetime.now(timezone.utc).isoformat())
    _atomic(path, json.dumps(updated, ensure_ascii=False, indent=2).encode('utf-8'))
    ADAPTATION_TASKS[directory.name] = updated
    return updated


def _derived_outputs(directory, raw):
    """Use the real Fountain parser without initializing a global matrix project."""
    parser_factory = _parser_factory
    if parser_factory is None:
        from core.matrix_docs import FountainParser
        parser_factory = FountainParser
    path = artifact(directory, 'project.json')
    try:
        metadata_raw = path.read_bytes()
        metadata = json.loads(metadata_raw.decode('utf-8-sig'))
    except (OSError, ValueError, UnicodeError) as error:
        raise HTTPException(409, 'Project metadata is invalid; existing bytes preserved.') from error
    if not isinstance(metadata, dict):
        raise HTTPException(409, 'Project metadata is invalid; existing bytes preserved.')
    content = raw.decode('utf-8')
    parser = parser_factory(content)
    parser.estimate_pages()
    metadata.update(word_count=len(content.split()),
                    page_count=int(parser.elements[-1].page_estimate) if parser.elements else 0)
    fdx = parser.to_fdx(metadata.get('title', directory.name), metadata.get('author', 'Unknown'))
    return {'screenplay.fountain': raw,
            f'{directory.name}.fdx': fdx.encode('utf-8'),
            'project.json': json.dumps(metadata, ensure_ascii=False, indent=2).encode('utf-8')}, metadata_raw


def _transaction(directory, job_id, outputs, expected_originals=None):
    """Replace screenplay, derivatives, metadata and state as a recoverable unit.

    Same-store mutex must be held. A durable journal and byte-for-byte predecessor
    copies allow manual recovery after a process/OS failure between replacements.
    Runtime failures restore only our own replacements; attempted outputs survive.
    """
    transaction_id = uuid.uuid4().hex
    relative = f'adaptation_history/{job_id}/transactions/{transaction_id}'
    folder = artifact(directory, relative)
    folder.mkdir(parents=True, exist_ok=False)
    originals, targets = {}, {}
    for name, raw in outputs.items():
        if Path(name).name != name or not isinstance(raw, bytes):
            raise ValueError('Transactions require named project files and raw bytes.')
        target = artifact(directory, name)
        targets[name] = target
        originals[name] = target.read_bytes() if target.exists() else None
        if expected_originals is not None and name in expected_originals and originals[name] != expected_originals[name]:
            raise HTTPException(409, 'A project file changed during derivative generation; existing bytes preserved.')
        if originals[name] is not None:
            _exclusive(artifact(directory, f'{relative}/previous/{name}'), originals[name])
        _exclusive(artifact(directory, f'{relative}/attempted/{name}'), raw)
    journal = {'transaction_id': transaction_id, 'status': 'prepared',
               'files': {name: {'previous_sha256': hashlib.sha256(raw).hexdigest() if raw is not None else None,
                                'next_sha256': hashlib.sha256(outputs[name]).hexdigest()}
                         for name, raw in originals.items()}}
    journal_path = artifact(directory, f'{relative}/journal.json')
    _exclusive(journal_path, json.dumps(journal, indent=2).encode('utf-8'))
    completed = []
    try:
        for name, raw in outputs.items():
            current = targets[name].read_bytes() if targets[name].exists() else None
            if current != originals[name]:
                raise HTTPException(409, 'A project file changed outside this transaction; existing bytes preserved.')
            completed.append(name)
            _atomic(targets[name], raw)
        journal['status'] = 'committed'
        _atomic(journal_path, json.dumps(journal, indent=2).encode('utf-8'))
    except BaseException as failure:
        errors = []
        for name in reversed(completed):
            try:
                current = targets[name].read_bytes() if targets[name].exists() else None
                if current == originals[name]:
                    continue  # write failed before replacing this target
                if current != outputs[name]:
                    raise RuntimeError('External file revision preserved; predecessor remains in transaction history.')
                if originals[name] is None:
                    retained = artifact(directory, f'{relative}/retained_after_rollback/{name}')
                    retained.parent.mkdir(parents=True, exist_ok=True)
                    os.rename(targets[name], retained)
                else:
                    _atomic(targets[name], originals[name])
            except BaseException as error:
                errors.append(f'{name}: {error}')
        journal.update(status='recovery_required' if errors else 'rolled_back', rollback_errors=errors)
        try:
            _atomic(journal_path, json.dumps(journal, indent=2).encode('utf-8'))
        except BaseException:
            pass  # original prepared journal and all predecessor bytes are durable
        if errors:
            raise HTTPException(503, 'Project save needs recovery; original and attempted bytes retained in adaptation history.') from failure
        raise


def _git_checkpoint(directory, job_id, paths, message):
    """Commit only these project files without including an unrelated Git index."""
    git_dir = artifact(directory, '.git')
    if git_dir.exists() and not git_dir.is_dir():
        raise RuntimeError('Linked/worktree Git directories require separate review.')
    hooks = artifact(directory, f'adaptation_history/{job_id}/git_hooks_disabled')
    hooks.mkdir(parents=True, exist_ok=True)
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
    environment['GIT_TERMINAL_PROMPT'] = '0'
    command = ['git', '-c', f'core.hooksPath={hooks}', '-c', 'core.fsmonitor=false',
               '-c', 'commit.gpgsign=false', '-c', 'core.autocrlf=false',
               '-c', 'user.name=AI-BS', '-c', 'user.email=matrix@ai-bs.local']
    def run(*arguments, check=True):
        return subprocess.run([*command, *arguments], cwd=directory, env=environment,
                              capture_output=True, timeout=30, check=check)
    # Never let git walk up into C:/AI-BS (or another ancestor repository).
    if not git_dir.exists():
        run('init', '--initial-branch=main')
    top = Path(run('rev-parse', '--show-toplevel').stdout.decode('utf-8').strip()).resolve()
    if top != directory.resolve():
        raise RuntimeError('Git repository root does not match this screenplay project.')
    for name in paths:
        artifact(directory, name)
    run('add', '--', *paths)
    changed = run('diff', '--cached', '--quiet', '--', *paths, check=False)
    if changed.returncode not in (0, 1):
        raise RuntimeError('Git could not inspect the screenplay checkpoint.')
    if changed.returncode:
        run('commit', '--only', '-m', message, '--', *paths)
    return run('rev-parse', 'HEAD').stdout.decode('ascii').strip()


def _record_checkpoint(directory, state, paths, message):
    """A Git failure is reported separately from an already successful disk save."""
    try:
        commit = _git_checkpoint(directory, state['job_id'], paths, message)
        state.update(git_status='saved', git_commit=commit)
        state.pop('git_error', None)
    except (OSError, RuntimeError, subprocess.SubprocessError, HTTPException) as error:
        state.update(git_status='failed', git_error=str(error))
        state.pop('git_commit', None)
    return _persist(directory, state)


def reserve_adaptation(project_name, content, suffix, adaptation_type, book_style):
    if not isinstance(content, bytes) or not content:
        raise HTTPException(400, 'Source content cannot be empty.')
    if suffix not in {'.pdf', '.epub', '.docx', '.doc', '.txt', '.md', '.markdown', '.fountain', '.fdx', '.rtf'}:
        raise HTTPException(400, 'Unsupported adaptation source format.')
    if not all(isinstance(value, str) and value.strip() for value in [adaptation_type, book_style]):
        raise HTTPException(400, 'Adaptation format and source style are required.')
    with mutex():
        directory = project_directory(project_name)
        root().mkdir(parents=True, exist_ok=True)
        # Match Windows case-insensitivity even in fixtures on another platform.
        if any(p.name.casefold() == directory.name.casefold() for p in root().iterdir()):
            raise HTTPException(409, 'Project already exists. Choose a new project name to preserve its manuscripts.')
        directory.mkdir(exist_ok=False)
        job_id = uuid.uuid4().hex
        source_relative = f'adaptation_history/{job_id}/source{suffix}'
        source = artifact(directory, source_relative)
        _exclusive(source, content)
        screenplay = f'Title: {directory.name}\n\n'.encode('utf-8')
        _exclusive(artifact(directory, 'screenplay.fountain'), screenplay)
        _exclusive(artifact(directory, 'project.json'), json.dumps({
            'title': directory.name, 'author': 'Screenwriter', 'characters': [], 'beat_videos': {},
            'adaptation_job_id': job_id}, indent=2).encode('utf-8'))
        state = _persist(directory, {
            'contract': CONTRACT, 'project_name': directory.name, 'job_id': job_id,
            'owner_process': _process_identity(),
            'status': 'queued', 'progress': 0, 'current_chunk': 0, 'total_chunks': 0,
            'source_path': source_relative, 'source_sha256': hashlib.sha256(content).hexdigest(),
            'screenplay_revision': hashlib.sha256(screenplay).hexdigest(),
            'previous_summary': 'This is the very beginning of the story.',
            'adaptation_type': adaptation_type, 'book_style': book_style,
        })
        try:
            outputs, metadata_raw = _derived_outputs(directory, screenplay)
            _transaction(directory, job_id, outputs, {'screenplay.fountain': screenplay, 'project.json': metadata_raw})
            state = _record_checkpoint(directory, state, list(outputs), 'Initialize retained screenplay adaptation')
        except Exception as failure:
            try:
                _persist(directory, dict(state, status='error', error=f'Initial project save failed; retained files preserved: {failure}'))
            except Exception:
                pass
            raise
        return directory, source, state


class OwnershipLost(Exception):
    """An invalidated worker must stop without touching current state."""


def _owned(directory, job_id, worker_id):
    state = _read(directory)
    if (not job_id or state.get('job_id') != job_id or state.get('worker_id') != worker_id
            or state.get('status') != 'processing' or state.get('owner_process') != _process_identity()):
        raise OwnershipLost()
    return state


def claim_job(project_name, job_id):
    with mutex():
        directory = project_directory(project_name, True)
        state = _read(directory)
        if (not job_id or state.get('job_id') != job_id or state.get('status') != 'queued'
                or state.get('owner_process') != _process_identity()):
            raise OwnershipLost()
        source = artifact(directory, state['source_path'])
        if hashlib.sha256(source.read_bytes()).hexdigest() != state['source_sha256']:
            _persist(directory, dict(state, status='error', error='Retained source changed; adaptation was not started.'))
            raise HTTPException(409, 'Retained source changed; adaptation was not started.')
        state.update(status='processing', worker_id=uuid.uuid4().hex)
        return directory, source, _persist(directory, state)


def check_owned(project_name, job_id, worker_id):
    with mutex():
        directory = project_directory(project_name, True)
        return _owned(directory, job_id, worker_id)


def update_job(project_name, job_id, worker_id, **changes):
    with mutex():
        directory = project_directory(project_name, True)
        state = _owned(directory, job_id, worker_id)
        # Callers can update progress/status, never transfer ownership.
        if any(key in changes for key in ('job_id', 'worker_id', 'owner_process', 'source_path', 'source_sha256', 'screenplay_revision')):
            raise ValueError('Job ownership is immutable.')
        state.update(changes)
        return _persist(directory, state)


def retain_chunks(project_name, job_id, worker_id, chunks):
    with mutex():
        directory = project_directory(project_name, True)
        state = _owned(directory, job_id, worker_id)
        _exclusive(artifact(directory, f'adaptation_history/{job_id}/chunks.json'), json.dumps(chunks, ensure_ascii=False).encode('utf-8'))
        state['total_chunks'] = len(chunks)
        return _persist(directory, state)


def commit_chunk(project_name, job_id, worker_id, index, content, summary):
    with mutex():
        directory = project_directory(project_name, True)
        state = _owned(directory, job_id, worker_id)
        if state.get('current_chunk') != index:
            raise OwnershipLost()
        original_state = artifact(directory, 'adaptation_state.json').read_bytes()
        target = artifact(directory, 'screenplay.fountain')
        previous = target.read_bytes()
        if hashlib.sha256(previous).hexdigest() != state['screenplay_revision']:
            raise HTTPException(409, 'Screenplay changed outside this adaptation; all existing bytes preserved.')
        # Retain output and predecessor before changing the canonical screenplay.
        _exclusive(artifact(directory, f'adaptation_history/{job_id}/outputs/{index:06d}-{uuid.uuid4().hex}.fountain'), content.encode('utf-8'))
        _exclusive(artifact(directory, f'adaptation_history/{job_id}/screenplays/{index:06d}-{uuid.uuid4().hex}.fountain'), previous)
        combined = previous + b'\n\n' + content.encode('utf-8')
        state.update(current_chunk=index + 1, previous_summary=summary,
                     progress=int((index + 1) / state['total_chunks'] * 100),
                     screenplay_revision=hashlib.sha256(combined).hexdigest())
        state.update(git_status='pending', previous_git_commit=state.pop('git_commit', None))
        outputs, metadata_raw = _derived_outputs(directory, combined)
        _owned(directory, job_id, worker_id)
        state['updated_at'] = datetime.now(timezone.utc).isoformat()
        outputs['adaptation_state.json'] = json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8')
        _transaction(directory, job_id, outputs, {'screenplay.fountain': previous,
            'project.json': metadata_raw, 'adaptation_state.json': original_state})
        ADAPTATION_TASKS[directory.name] = state
        return _record_checkpoint(directory, state, list(outputs)[:-1], f'Adapt screenplay chunk {index + 1}')


def invalidate_job(project_name, status, job_id=None):
    with mutex():
        directory = project_directory(project_name, True)
        try:
            state = _read(directory)
        except HTTPException as exc:
            if exc.status_code == 404:
                return False
            raise
        if job_id is not None and job_id != state.get('job_id'):
            raise HTTPException(409, 'This job changed; reload its current status.')
        state.update(status=status, error='Adaptation canceled by user' if status == 'canceled' else 'Job ownership reset; retained files are preserved.')
        state.pop('worker_id', None)
        _persist(directory, state)
        return True


def get_all_adaptation_tasks():
    tasks = {}
    with mutex():
        if not root().exists():
            return tasks
        for entry in root().iterdir():
            if not entry.is_dir():
                continue
            try:
                directory = project_directory(entry.name, True)
                tasks[entry.name] = _read(directory)
            except HTTPException:
                continue
        ADAPTATION_TASKS.clear()
        ADAPTATION_TASKS.update(tasks)
    return tasks


def load_all_states(projects_dir=None):
    # A new API worker must preserve another verified live process's ownership.
    if projects_dir is not None and Path(projects_dir).resolve() != root().resolve():
        raise ValueError('Loading a different store requires explicit store configuration.')
    with mutex():
        for name, state in get_all_adaptation_tasks().items():
            if state.get('status') in ACTIVE and not _process_is_alive(state.get('owner_process')):
                directory = project_directory(name, True)
                state.update(status='interrupted', error='Backend restarted; retained files preserved. Start a new project for another adaptation.')
                state.pop('worker_id', None)
                _persist(directory, state)


def cancel_adaptation(project_name, job_id=None):
    return invalidate_job(project_name, 'canceled', job_id)


def reset_adaptation(project_name, job_id=None):
    return invalidate_job(project_name, 'reset', job_id)
