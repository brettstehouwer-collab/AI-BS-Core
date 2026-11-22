"""Owner-scoped durable film plans. No inference or rendering on import."""
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
import uuid
from contextlib import contextmanager

ROOT = Path(os.environ.get('AI_BS_CHAT_FILM_ROOT', str(Path(__file__).resolve().parents[2] / 'saved_data' / 'chat_films')))


def owner_key(owner):
    if not isinstance(owner, str) or not (owner == 'local_admin' or owner.startswith('firebase:')):
        raise PermissionError('Verified identity required')
    return hashlib.sha256(owner.encode()).hexdigest()


class FilmStore:
    def __init__(self, root=ROOT):
        self.root = Path(root)

    @contextmanager
    def connect(self):
        self.root.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.root / 'films.sqlite3', timeout=5)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS films(id TEXT PRIMARY KEY, owner TEXT NOT NULL, revision INTEGER NOT NULL, updated REAL NOT NULL, record TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, film TEXT NOT NULL, revision INTEGER NOT NULL, record TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS selected(owner TEXT PRIMARY KEY, film TEXT NOT NULL)')
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, owner, script, seconds):
        key = owner_key(owner)
        if not isinstance(script, str) or not script.strip() or len(script) > 32000:
            raise ValueError('Provide a script or description of 1–32000 characters')
        if type(seconds) is not int or not 1 <= seconds <= 600:
            raise ValueError('Choose 1–600 seconds')
        beats = [line.strip() for line in script.splitlines() if line.strip()]
        count = max(math.ceil(seconds / 5), min(len(beats), seconds))
        count = min(count, 120)
        remaining = seconds
        shots = []
        for index in range(count):
            duration = math.ceil(remaining / (count-index))
            remaining -= duration
            shots.append({'number': index+1, 'seconds': duration,
                          'prompt': beats[min(index * len(beats)//count, len(beats)-1)],
                          'state': 'planned', 'prompt_id': None, 'output': None})
        record = {'id': uuid.uuid4().hex, 'revision': 1, 'script': script,
                  'seconds': seconds, 'shots': shots, 'state': 'planned',
                  'run_requested': False, 'assemble_requested': False,
                  'output': None, 'error': None}
        raw = json.dumps(record)
        with self.connect() as db:
            db.execute('INSERT INTO films VALUES(?,?,?,?,?)', (record['id'],key,1,time.time(),raw))
            db.execute('INSERT INTO events(film,revision,record) VALUES(?,?,?)',(record['id'],1,raw))
            db.execute('INSERT OR REPLACE INTO selected VALUES(?,?)',(key,record['id']))
        return record

    def get(self, owner, film_id=None):
        with self.connect() as db:
            if film_id:
                row = db.execute('SELECT record FROM films WHERE owner=? AND id=?',(owner_key(owner),film_id)).fetchone()
            else:
                row = db.execute('SELECT record FROM films WHERE owner=? AND id=(SELECT film FROM selected WHERE owner=?)',(owner_key(owner),owner_key(owner))).fetchone()
        if row is None:
            raise ValueError('No saved film found for this account')
        return json.loads(row[0])

    def select(self, owner, film_id):
        self.get(owner,film_id)
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO selected VALUES(?,?)',(owner_key(owner),film_id))

    def save(self, owner, record):
        previous = record['revision']
        updated = dict(record, revision=previous+1)
        raw = json.dumps(updated)
        with self.connect() as db:
            changed = db.execute('UPDATE films SET revision=?,updated=?,record=? WHERE id=? AND owner=? AND revision=?',
                                 (previous+1,time.time(),raw,record['id'],owner_key(owner),previous)).rowcount
            if changed != 1:
                raise ValueError('Film changed concurrently; read status before retrying')
            db.execute('INSERT INTO events(film,revision,record) VALUES(?,?,?)',(record['id'],previous+1,raw))
        record.update(revision=previous+1)
        return record

    def directory(self, owner, film_id):
        if len(film_id) != 32 or any(c not in '0123456789abcdef' for c in film_id):
            raise ValueError('Invalid film ID')
        path = self.root / owner_key(owner) / film_id
        path.mkdir(parents=True, exist_ok=True)
        return path
