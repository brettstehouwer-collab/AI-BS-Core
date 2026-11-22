"""Actual disposable SQLite restart/concurrency tests, not guest acceptance."""
from pathlib import Path
import importlib.util,json,sqlite3,sys,threading,unittest,uuid,os,hashlib
spec=importlib.util.spec_from_file_location('replay_claims',Path(__file__).with_name('replay_claims.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
E=Path(r'C:\AI-BS\backups\scoped_transport_20261025_record111\storage_tests')

class ReplayTests(unittest.TestCase):
 def setUp(self):
  self.root=E/uuid.uuid4().hex;self.root.mkdir(parents=True);self.path=self.root/'disposable_replay.sqlite'
 def connect(self):return sqlite3.connect(self.path,timeout=3)
 def claim(self,store):return store.claim('worker-fixture','host_to_guest','a'*32,'b'*64,1100)
 def test_restart_refuses_previous_acceptance(self):
  c=self.connect();self.assertTrue(self.claim(module.ReplayClaims(c,create=True)));c.close()
  c=self.connect();self.assertFalse(self.claim(module.ReplayClaims(c)));self.assertEqual(c.execute('SELECT COUNT(*) FROM integration_replay_v1').fetchone()[0],1);c.close()
 def test_concurrent_connections_single_durable_acceptance(self):
  c=self.connect();module.ReplayClaims(c,create=True);c.close();results=[];errors=[]
  def claim():
   con=self.connect()
   try:results.append(self.claim(module.ReplayClaims(con)))
   except Exception as e:errors.append(type(e).__name__)
   finally:con.close()
  threads=[threading.Thread(target=claim) for _ in range(8)]
  for t in threads:t.start()
  for t in threads:t.join()
  self.assertEqual(errors,[]);self.assertEqual(sum(results),1)
 def test_unknown_existing_schema_refused_without_mutation(self):
  c=self.connect();c.execute('CREATE TABLE private_fixture (value TEXT)');c.execute("INSERT INTO private_fixture VALUES('synthetic')");c.commit()
  before=c.execute('SELECT * FROM sqlite_master').fetchall()
  for create in [True,False]:
   with self.assertRaises(module.ReplayStoreRejected):module.ReplayClaims(c,create=create)
  self.assertEqual(before,c.execute('SELECT * FROM sqlite_master').fetchall());self.assertEqual(c.execute('SELECT * FROM private_fixture').fetchall(),[('synthetic',)]);c.close()
 def test_added_trigger_refused_before_claim(self):
  c=self.connect();store=module.ReplayClaims(c,create=True);c.execute('CREATE TABLE extra_fixture (n)');c.commit()
  with self.assertRaises(module.ReplayStoreRejected):self.claim(store)
  self.assertEqual(c.execute('SELECT COUNT(*) FROM integration_replay_v1').fetchone()[0],0);c.close()
 def test_rolled_back_claim_can_be_retried_but_committed_claim_cannot(self):
  c=self.connect();store=module.ReplayClaims(c,create=True)
  c.execute('BEGIN IMMEDIATE');c.execute('INSERT INTO integration_replay_v1 VALUES(?,?,?,?,?)',('worker-fixture','host_to_guest','a'*32,'b'*64,1100));c.rollback()
  self.assertTrue(self.claim(store));self.assertFalse(self.claim(store));c.close()
 def test_open_transaction_refused_and_preserved(self):
  c=self.connect();module.ReplayClaims(c,create=True);c.execute('BEGIN IMMEDIATE')
  with self.assertRaises(module.ReplayStoreRejected):module.ReplayClaims(c)
  self.assertTrue(c.in_transaction);c.rollback();c.close()
 def test_closed_store_fails_closed(self):
  c=self.connect();store=module.ReplayClaims(c,create=True);c.close()
  with self.assertRaises(sqlite3.ProgrammingError):self.claim(store)
 def test_claim_contents_restricted_and_no_payload_or_keys_stored(self):
  c=self.connect();store=module.ReplayClaims(c,create=True)
  with self.assertRaises(module.ReplayStoreRejected):store.claim('worker-fixture','other','a'*32,'b'*64,1100)
  self.assertTrue(self.claim(store));columns=[r[1] for r in c.execute('PRAGMA table_info(integration_replay_v1)')]
  self.assertEqual(columns,['worker','direction','nonce','packet_sha256','expires']);self.assertEqual(c.execute('PRAGMA integrity_check').fetchall(),[('ok',)]);c.close()
 def test_authenticated_packet_rejected_after_receiver_restart(self):
  spec=importlib.util.spec_from_file_location('replay_fixture_exchange',Path(__file__).with_name('scoped_exchange.py'))
  codec=importlib.util.module_from_spec(spec);sys.modules[spec.name]=codec;spec.loader.exec_module(codec)
  key=os.urandom(32);p=codec.Policy('worker','owner','a'*64,'guest_to_host',frozenset({'outputs/result.txt'}),{})
  raw=codec.pack(key,p,'result','disposable bytes',{'outputs/result.txt':b'fixture'},'c'*32,1000,1100)
  c=self.connect();accepted=codec.unpack(raw,key,p,1001,module.ReplayClaims(c,create=True).claim);self.assertEqual(accepted.files[0].data,b'fixture');c.close()
  c=self.connect()
  with self.assertRaises(codec.Rejected):codec.unpack(raw,key,p,1002,module.ReplayClaims(c).claim)
  self.assertEqual(c.execute('SELECT packet_sha256 FROM integration_replay_v1').fetchone()[0],hashlib.sha256(raw).hexdigest());c.close()
 def test_memory_and_temporary_stores_refused(self):
  for path in [':memory:','']:
   c=sqlite3.connect(path)
   with self.assertRaises(module.ReplayStoreRejected):module.ReplayClaims(c,create=True)
   self.assertEqual(c.execute('SELECT * FROM sqlite_master').fetchall(),[]);c.close()
 def test_unsafe_journal_and_synchronous_refused(self):
  for pragma in ['journal_mode=MEMORY','journal_mode=OFF','synchronous=OFF','synchronous=NORMAL']:
   c=self.connect();c.execute('PRAGMA '+pragma)
   with self.assertRaises(module.ReplayStoreRejected):module.ReplayClaims(c,create=True)
   self.assertEqual(c.execute('SELECT * FROM sqlite_master').fetchall(),[]);c.close()
 def test_durability_drift_refused_before_claim(self):
  c=self.connect();store=module.ReplayClaims(c,create=True);c.execute('PRAGMA synchronous=OFF')
  with self.assertRaises(module.ReplayStoreRejected):self.claim(store)
  self.assertEqual(c.execute('SELECT COUNT(*) FROM integration_replay_v1').fetchone()[0],0);c.close()

if __name__=='__main__':unittest.main()
