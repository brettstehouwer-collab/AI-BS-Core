"""Project-local writing snapshots and sprints; no Git, process or network actions.

The caller supplies the existing project-store lock, exact-byte reader and atomic
writer. SQLite and the canonical screenplay are separate commits: a retained
PREPARED operation requires explicit recovery, never a silent read-time rewrite.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
import unicodedata
import uuid

APP_ID = 0x41494257
SCHEMA_VERSION = 1
MAX_CONTENT_BYTES = 16 * 1024 * 1024
MAX_STORED_BYTES = 128 * 1024 * 1024
MAX_BRANCHES = 64
MAX_SPRINTS = 2048
MAX_OPERATIONS = 4096
TABLES = {'head', 'branches', 'sprints', 'operations'}


class WorkflowError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _refuse(message, status=409):
    raise WorkflowError(status, message)


def _name(value):
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > 80 or value in {'.', '..'}
            or any(char in '\\/:*?"<>|' or unicodedata.category(char).startswith('C') for char in value)):
        _refuse('Use a nonempty name of at most 80 characters without path or control characters.', 400)
    return value


def _utc():
    return datetime.now(timezone.utc).isoformat()


class WorkflowStore:
    def __init__(self, directory, snapshot, write, lock):
        self.directory = Path(directory)
        self.path = self.directory / '.writing-workflows.sqlite3'
        self._snapshot = snapshot
        self._write = write
        self._lock = lock

    def _paths(self):
        for suffix in ('', '-journal', '-wal', '-shm'):
            path = Path(str(self.path) + suffix)
            if (path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())
                    or path.resolve().parent != self.directory.resolve()):
                _refuse('Workflow storage must remain inside its project.', 400)

    @contextmanager
    def _connection(self, create=False):
        self._paths()
        exists = self.path.exists()
        if not exists and not create:
            yield None
            return
        connection = None
        try:
            if exists:
                # mode=rw refuses a missing file instead of accidentally creating it.
                connection = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=5)
            else:
                connection = sqlite3.connect(self.path, timeout=5)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA synchronous=FULL')
            if not exists:
                raw = self._snapshot()['content'].encode('utf-8')
                self._content(raw)
                connection.executescript('''
                    BEGIN IMMEDIATE;
                    CREATE TABLE head(id INTEGER PRIMARY KEY CHECK(id=1), epoch INTEGER NOT NULL, active TEXT NOT NULL);
                    CREATE TABLE branches(key TEXT PRIMARY KEY, name TEXT NOT NULL, content BLOB NOT NULL);
                    CREATE TABLE sprints(id TEXT PRIMARY KEY, name TEXT NOT NULL, branch TEXT NOT NULL,
                        target_pages INTEGER NOT NULL, baseline_words INTEGER NOT NULL, end_words INTEGER,
                        status TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT, elapsed_seconds REAL);
                    CREATE UNIQUE INDEX one_active_sprint ON sprints(status) WHERE status='ACTIVE';
                    CREATE TABLE operations(id TEXT PRIMARY KEY, status TEXT NOT NULL, kind TEXT NOT NULL,
                        base_epoch INTEGER NOT NULL, source_branch TEXT NOT NULL, target_branch TEXT NOT NULL,
                        before_revision TEXT NOT NULL, after_revision TEXT NOT NULL,
                        before_content BLOB NOT NULL, after_content BLOB NOT NULL, created_at TEXT NOT NULL);
                    CREATE UNIQUE INDEX one_pending_operation ON operations(status) WHERE status='PREPARED';
                ''')
                connection.execute(f'PRAGMA application_id={APP_ID}')
                connection.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
                connection.execute("INSERT INTO head VALUES(1,0,'main')")
                connection.execute("INSERT INTO branches VALUES('main','main',?)", (raw,))
                connection.commit()
            if (connection.execute('PRAGMA application_id').fetchone()[0] != APP_ID
                    or connection.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION
                    or connection.execute('PRAGMA journal_mode').fetchone()[0] != 'delete'
                    or {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")} != TABLES):
                _refuse('Unrecognized workflow database. Its existing bytes have been preserved.')
            connection.execute('BEGIN IMMEDIATE' if create else 'BEGIN')
            yield connection
            connection.commit()
        except sqlite3.Error as error:
            raise WorkflowError(409, 'Workflow storage could not be verified or committed. Preserve the project and inspect recovery status.') from error
        finally:
            if connection is not None:
                connection.close()  # Rolls back any unfinished transaction; never removes the retained database.

    def _content(self, raw):
        if not isinstance(raw, bytes) or len(raw) > MAX_CONTENT_BYTES:
            _refuse('A writing snapshot must be UTF-8 bytes within the 16 MiB limit.', 400)
        try:
            raw.decode('utf-8')
        except UnicodeError:
            _refuse('Writing snapshots must contain valid UTF-8. Original bytes are preserved.', 400)

    def _budget(self, connection, additional=0):
        branches = connection.execute('SELECT coalesce(sum(length(content)),0) FROM branches').fetchone()[0]
        journal = connection.execute('SELECT coalesce(sum(length(before_content)+length(after_content)),0) FROM operations').fetchone()[0]
        if branches + journal + additional > MAX_STORED_BYTES:
            _refuse('Retained writing history reached its content budget. Preserve/export history before extending it.')

    def _status(self, connection):
        if connection is None:
            return dict(initialized=False, workflow_revision=0, active_branch='main', branches=['main'],
                        active_sprint=None, sprints=[], pending_operation=None)
        head = connection.execute('SELECT epoch,active FROM head WHERE id=1').fetchone()
        branches = connection.execute('SELECT key,name FROM branches ORDER BY rowid').fetchall()
        if (head is None or type(head['epoch']) is not int or head['epoch'] < 0
                or head['active'] not in {row['key'] for row in branches}):
            _refuse('Workflow head is invalid. Preserve the database for recovery.')
        sprints = []
        for row in connection.execute('SELECT * FROM sprints ORDER BY rowid DESC'):
            item = dict(row)
            item['word_delta'] = None if item['end_words'] is None else item['end_words'] - item['baseline_words']
            sprints.append(item)
        pending = connection.execute('''SELECT id,kind,source_branch,target_branch,before_revision,after_revision
            FROM operations WHERE status='PREPARED' ''').fetchone()
        return dict(initialized=True, workflow_revision=head['epoch'],
                    active_branch=next(row['name'] for row in branches if row['key'] == head['active']),
                    branches=[row['name'] for row in branches], sprints=sprints,
                    active_sprint=next((row for row in sprints if row['status'] == 'ACTIVE'), None),
                    pending_operation=dict(pending) if pending else None)

    def status(self):
        with self._lock, self._connection() as connection:
            return self._status(connection)

    def _check(self, connection, revision, workflow_revision):
        state = self._status(connection)
        if state['pending_operation']:
            _refuse('An interrupted writing operation requires explicit recovery before any further change.')
        if type(workflow_revision) is not int:
            _refuse('Reload the project workflow revision before changing it.', 428)
        if workflow_revision != state['workflow_revision']:
            _refuse('The writing branch or sprint changed. Keep your local draft and reload workflow state.')
        if not isinstance(revision, str) or not revision:
            _refuse('An expected screenplay revision is required.', 428)
        if revision != self._snapshot()['revision']:
            _refuse('The screenplay changed. Keep your draft and reconcile the saved version first.')
        return state

    def assert_ready(self):
        state = self.status()
        if state['pending_operation']:
            _refuse('Explicit writing-operation recovery is required before changing or archiving this project.')
        return state

    def check_revision(self, revision, workflow_revision):
        with self._lock, self._connection() as connection:
            return self._check(connection, revision, workflow_revision)

    def create_branch(self, name, revision, workflow_revision):
        name = _name(name)
        with self._lock:
            # Validate CAS before first-time database creation as well.
            self.check_revision(revision, workflow_revision)
            with self._connection(create=True) as connection:
                state = self._check(connection, revision, workflow_revision)
                if len(state['branches']) >= MAX_BRANCHES:
                    _refuse('The project branch limit was reached.')
                if connection.execute('SELECT 1 FROM branches WHERE key=?', (name.casefold(),)).fetchone():
                    _refuse('A branch with this name already exists.')
                raw = self._snapshot()['content'].encode('utf-8')
                self._content(raw)
                self._budget(connection, len(raw))
                connection.execute('INSERT INTO branches VALUES(?,?,?)', (name.casefold(), name, raw))
                connection.execute('UPDATE head SET epoch=epoch+1 WHERE id=1')
                return self._status(connection)

    def _prepare(self, connection, kind, target, raw, revision, state):
        self._content(raw)
        before = self._snapshot()['content'].encode('utf-8')
        self._content(before)
        self._budget(connection, 2 * (len(before) + len(raw)))
        if connection.execute('SELECT count(*) FROM operations').fetchone()[0] >= MAX_OPERATIONS:
            _refuse('The retained writing operation limit was reached. Preserve/export history first.')
        operation = dict(id=uuid.uuid4().hex, status='PREPARED', kind=kind,
                         base_epoch=state['workflow_revision'], source_branch=state['active_branch'].casefold(),
                         target_branch=target, before_revision=revision,
                         after_revision=hashlib.sha256(raw).hexdigest(), before_content=before,
                         after_content=raw, created_at=_utc())
        columns = ','.join(operation)
        connection.execute(f"INSERT INTO operations({columns}) VALUES({','.join('?' for _ in operation)})", tuple(operation.values()))
        # Persist intent before touching the separate canonical file.
        connection.commit()
        return operation

    def _validate_operation(self, connection, operation):
        # A damaged retained journal must never become a manuscript write recipe.
        before, after = operation['before_content'], operation['after_content']
        self._content(before)
        self._content(after)
        before_hash = hashlib.sha256(before).hexdigest()
        valid_before = {before_hash, 'adaptation:' + before_hash}
        if before == b'':
            valid_before.add('missing')
        head = connection.execute('SELECT epoch,active FROM head WHERE id=1').fetchone()
        keys = {row[0] for row in connection.execute('SELECT key FROM branches')}
        if (operation['kind'] not in {'WRITE', 'SWITCH'}
                or operation['before_revision'] not in valid_before
                or operation['after_revision'] != hashlib.sha256(after).hexdigest()
                or head is None or head['epoch'] != operation['base_epoch']
                or head['active'] != operation['source_branch']
                or operation['source_branch'] not in keys or operation['target_branch'] not in keys
                or (operation['kind'] == 'WRITE' and operation['source_branch'] != operation['target_branch'])
                or (operation['kind'] == 'SWITCH' and operation['source_branch'] == operation['target_branch'])):
            _refuse('Retained writing operation failed its integrity checks. Preserve all recovery evidence.')
        if operation['kind'] == 'SWITCH':
            target = connection.execute('SELECT content FROM branches WHERE key=?', (operation['target_branch'],)).fetchone()[0]
            if target != after:
                _refuse('Retained switch target differs from its branch. Preserve all recovery evidence.')

    def _finish(self, connection, operation):
        connection.execute('BEGIN IMMEDIATE')
        self._validate_operation(connection, operation)
        current = connection.execute('SELECT epoch FROM head WHERE id=1').fetchone()
        pending = connection.execute("SELECT status FROM operations WHERE id=?", (operation['id'],)).fetchone()
        if current['epoch'] != operation['base_epoch'] or pending is None or pending['status'] != 'PREPARED':
            _refuse('The retained writing operation no longer matches the workflow head.')
        if self._snapshot()['revision'] != operation['after_revision']:
            _refuse('Canonical screenplay does not match the retained target. Recovery evidence is preserved.')
        connection.execute('UPDATE branches SET content=? WHERE key=?',
                           (operation['before_content'], operation['source_branch']))
        if operation['kind'] == 'WRITE':
            connection.execute('UPDATE branches SET content=? WHERE key=?',
                               (operation['after_content'], operation['target_branch']))
        connection.execute('UPDATE head SET active=?,epoch=epoch+1 WHERE id=1', (operation['target_branch'],))
        connection.execute("UPDATE operations SET status='COMPLETED' WHERE id=?", (operation['id'],))

    def write(self, raw, revision, workflow_revision):
        self._content(raw)
        with self._lock:
            self.check_revision(revision, workflow_revision)
            with self._connection(create=True) as connection:
                state = self._check(connection, revision, workflow_revision)
                operation = self._prepare(connection, 'WRITE', state['active_branch'].casefold(), raw, revision, state)
                self._write(raw)
                self._finish(connection, operation)
                return self._status(connection)

    def switch_branch(self, name, revision, workflow_revision):
        name = _name(name)
        with self._lock, self._connection() as connection:
            state = self._check(connection, revision, workflow_revision)
            if connection is None:
                _refuse('Create a project branch before switching branches.', 404)
            target = connection.execute('SELECT key,content FROM branches WHERE key=?', (name.casefold(),)).fetchone()
            if target is None:
                _refuse('The requested project branch does not exist.', 404)
            if target['key'] == state['active_branch'].casefold():
                return state
            if state['active_sprint']:
                _refuse('End the active writing sprint before switching branches.')
            operation = self._prepare(connection, 'SWITCH', target['key'], bytes(target['content']), revision, state)
            self._write(operation['after_content'])
            self._finish(connection, operation)
            return self._status(connection)

    def recover(self, operation_id, action):
        if action not in {'complete', 'abort'}:
            _refuse('Recovery requires an explicit complete or abort action.', 400)
        with self._lock, self._connection() as connection:
            if connection is None:
                _refuse('No writing recovery operation exists.', 404)
            operation = connection.execute("SELECT * FROM operations WHERE id=? AND status='PREPARED'", (operation_id,)).fetchone()
            if operation is None:
                _refuse('This operation is no longer pending. Reload project workflow state.')
            operation = dict(operation)
            self._validate_operation(connection, operation)
            head = connection.execute('SELECT epoch FROM head WHERE id=1').fetchone()[0]
            if head != operation['base_epoch']:
                _refuse('Recovery head differs from the retained operation; preserve both for review.')
            current = self._snapshot()['revision']
            if action == 'abort':
                if current != operation['before_revision']:
                    _refuse('Abort cannot overwrite an already changed screenplay. Preserve and review the pending operation.')
                connection.execute("UPDATE operations SET status='ABORTED' WHERE id=?", (operation_id,))
                connection.execute('UPDATE head SET epoch=epoch+1 WHERE id=1')
            else:
                self._content(bytes(operation['after_content']))
                if hashlib.sha256(operation['after_content']).hexdigest() != operation['after_revision']:
                    _refuse('Retained recovery content failed its hash check.')
                if current not in {operation['before_revision'], operation['after_revision']}:
                    _refuse('Unrelated edits prevent recovery. All existing bytes and journal evidence are preserved.')
                connection.commit()
                if current != operation['after_revision']:
                    self._write(bytes(operation['after_content']))
                self._finish(connection, operation)
            return self._status(connection)

    def start_sprint(self, name, target_pages, revision, workflow_revision):
        name = _name(name)
        if type(target_pages) is not int or not 1 <= target_pages <= 10000:
            _refuse('A sprint page target must be an integer between 1 and 10000.', 400)
        with self._lock:
            self.check_revision(revision, workflow_revision)
            with self._connection(create=True) as connection:
                state = self._check(connection, revision, workflow_revision)
                if state['active_sprint']:
                    _refuse('This project already has an active writing sprint.')
                if len(state['sprints']) >= MAX_SPRINTS:
                    _refuse('The retained project sprint limit was reached.')
                connection.execute('INSERT INTO sprints VALUES(?,?,?,?,?,?,?,?,?,?)',
                                   (uuid.uuid4().hex, name, state['active_branch'], target_pages,
                                    len(self._snapshot()['content'].split()), None, 'ACTIVE', _utc(), None, None))
                connection.execute('UPDATE head SET epoch=epoch+1 WHERE id=1')
                return self._status(connection)

    def end_sprint(self, sprint_id, revision, workflow_revision):
        with self._lock, self._connection() as connection:
            state = self._check(connection, revision, workflow_revision)
            sprint = state['active_sprint']
            if sprint is None or sprint['id'] != sprint_id:
                _refuse('The specified sprint is not active in this project.')
            ended = _utc()
            elapsed = (datetime.fromisoformat(ended) - datetime.fromisoformat(sprint['started_at'])).total_seconds()
            if elapsed < 0:
                _refuse('The system clock moved before the sprint start. Preserve the active sprint for review.')
            connection.execute("UPDATE sprints SET end_words=?,status='ENDED',ended_at=?,elapsed_seconds=? WHERE id=?",
                               (len(self._snapshot()['content'].split()), ended, elapsed, sprint_id))
            connection.execute('UPDATE head SET epoch=epoch+1 WHERE id=1')
            return self._status(connection)
