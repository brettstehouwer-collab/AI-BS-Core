"""Durable nonce claims on a caller-provisioned dedicated SQLite connection.

No path selection, account provision, ACL mutation or private-store discovery.
The deployment layer must supply its own private store, never a production DB.
Unknown nonempty schemas are refused before writes. Successful claims are never
deleted here, including expired ones; retention/pruning needs separate review.
"""
import hashlib,re,sqlite3

class ReplayStoreRejected(ValueError):pass

SCHEMA="CREATE TABLE integration_replay_v1 (worker TEXT NOT NULL, direction TEXT NOT NULL, nonce TEXT NOT NULL, packet_sha256 TEXT NOT NULL, expires INTEGER NOT NULL, PRIMARY KEY(worker,direction,nonce)) WITHOUT ROWID"

def _rows(connection):return connection.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name").fetchall()

def _persistent(connection):
 databases=connection.execute('PRAGMA database_list').fetchall()
 if len(databases)!=1 or databases[0][1]!='main' or not databases[0][2]:raise ReplayStoreRejected('PERSISTENT_DEDICATED_MAIN_REQUIRED')
 if connection.execute('PRAGMA journal_mode').fetchone()[0].lower() not in {'delete','truncate','persist','wal'}:raise ReplayStoreRejected('DURABLE_JOURNAL_REQUIRED')
 if connection.execute('PRAGMA synchronous').fetchone()[0]<2:raise ReplayStoreRejected('FULL_SYNCHRONOUS_REQUIRED')

class ReplayClaims:
 def __init__(self,connection,create=False):
  if not isinstance(connection,sqlite3.Connection) or connection.in_transaction:raise ReplayStoreRejected('DEDICATED_IDLE_CONNECTION_REQUIRED')
  self.connection=connection
  try:
   _persistent(connection)
   connection.execute('BEGIN IMMEDIATE')
   rows=_rows(connection)
   if create:
    if rows:raise ReplayStoreRejected('NONEMPTY_STORE_REFUSED')
    connection.execute(SCHEMA)
   elif rows!=[('table','integration_replay_v1',SCHEMA)]:raise ReplayStoreRejected('REPLAY_SCHEMA_MISMATCH')
   connection.commit()
  except Exception:
   connection.rollback();raise
 def claim(self,worker,direction,nonce,digest,expires):
  if not isinstance(worker,str) or not re.fullmatch('[A-Za-z0-9_:.-]{1,128}',worker) or direction not in {'host_to_guest','guest_to_host'} or not isinstance(nonce,str) or not re.fullmatch('[a-f0-9]{32}',nonce) or not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest) or type(expires) is not int or expires<=0:raise ReplayStoreRejected('CLAIM_FIELDS_REFUSED')
  c=self.connection
  if c.in_transaction:raise ReplayStoreRejected('IDLE_CONNECTION_REQUIRED')
  _persistent(c)
  try:
   c.execute('BEGIN IMMEDIATE')
   # Recheck the exact schema within the write transaction before each claim.
   if _rows(c)!=[('table','integration_replay_v1',SCHEMA)]:raise ReplayStoreRejected('REPLAY_SCHEMA_MISMATCH')
   prior=c.execute('SELECT 1 FROM integration_replay_v1 WHERE worker=? AND direction=? AND nonce=?',(worker,direction,nonce)).fetchone()
   if prior:c.rollback();return False
   c.execute('INSERT INTO integration_replay_v1 VALUES(?,?,?,?,?)',(worker,direction,nonce,digest,expires));c.commit();return True
  except Exception:
   c.rollback();raise
