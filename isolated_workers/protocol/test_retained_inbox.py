"""Actual disposable SQLite inbox tests; no VM, builds or project execution."""
import hashlib
import importlib
from pathlib import Path
import sqlite3
import sys
import threading
import unittest
import uuid

R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R))
from isolated_workers.protocol import scoped_exchange as codec
E=R/'backups/durable_packet_inbox_20261026_record122/inbox_tests'


class UncertainCommit(sqlite3.Connection):
    fail_after_commit=False
    def commit(self):
        super().commit()
        if self.fail_after_commit:
            self.fail_after_commit=False
            raise OSError('synthetic lost commit acknowledgement')


class UncommittedConnection(sqlite3.Connection):
    suppress_commit=False
    def commit(self):
        if not self.suppress_commit:super().commit()


class InboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module=importlib.import_module('isolated_workers.protocol.retained_inbox')

    def setUp(self):
        self.root=E/uuid.uuid4().hex;self.root.mkdir(parents=True)
        self.path=self.root/'synthetic_inbox.sqlite'
        self.key=b'k'*32
        self.policy=codec.Policy('worker-fixture','owner-fixture','a'*64,'host_to_guest',
                                 frozenset({'inputs/part.bin'}),{})
        self.connections=[]

    def tearDown(self):
        for connection in self.connections:
            try:connection.close()
            except sqlite3.Error:pass

    def connect(self,**kwargs):
        connection=sqlite3.connect(self.path,timeout=3,**kwargs)
        self.connections.append(connection);return connection

    def packet(self,nonce='1'*32,data=b'synthetic selected bytes'):
        return codec.pack(self.key,self.policy,'message','',{'inputs/part.bin':data},nonce,1000,1100)

    def inbox(self,connection=None,**kwargs):
        return self.module.RetainedInbox(connection or self.connect(),create=True,**kwargs)

    def test_retention_reopen_inspection_and_replay_refusal(self):
        connection=self.connect();store=self.inbox(connection);raw=self.packet()
        accepted=store.receive(raw,self.key,self.policy,1001)
        self.assertEqual(accepted.bundle.files[0].data,b'synthetic selected bytes')
        receipt=accepted.receipt
        self.assertEqual(receipt.packet_sha256,hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt.packet_bytes,len(raw))
        self.assertEqual(receipt.state,'RETAINED')
        self.assertFalse(receipt.worker_admitted);self.assertFalse(receipt.execution_authorized)
        self.assertFalse(receipt.apply_authorized);self.assertEqual(receipt.verification_status,'not_run')
        connection.close()
        recovered=self.module.RetainedInbox(self.connect())
        self.assertEqual(recovered.inspect('worker-fixture','host_to_guest','1'*32),receipt)
        self.assertEqual(recovered.read_packet('worker-fixture','host_to_guest','1'*32,receipt.packet_sha256),raw)
        with self.assertRaises(codec.Rejected):recovered.receive(raw,self.key,self.policy,1001)
        self.assertEqual(recovered.usage()['packets'],1)

    def test_bad_authentication_expiry_and_malformed_packet_do_not_write(self):
        store=self.inbox();raw=self.packet()
        for packet,key,now in [(raw,b'x'*32,1001),(raw,self.key,1200),(b'{}',self.key,1001),
                               (b'x'*(self.module.MAX_PACKET_BYTES+1),self.key,1001)]:
            with self.assertRaises((codec.Rejected,self.module.InboxRejected)):
                store.receive(packet,key,self.policy,now)
        self.assertEqual(store.usage()['packets'],0)

    def test_row_and_payload_quotas_are_durable_and_rejected_without_new_claim(self):
        store=self.inbox(packet_limit=2,payload_limit=10000)
        for number in range(2):store.receive(self.packet(f'{number:032x}'),self.key,self.policy,1001)
        with self.assertRaises(codec.Rejected):store.receive(self.packet('f'*32),self.key,self.policy,1001)
        self.assertEqual(store.usage()['packets'],2)
        self.assertIsNone(store.inspect('worker-fixture','host_to_guest','f'*32))
        reopened=self.module.RetainedInbox(self.connect(),packet_limit=2,payload_limit=10000)
        self.assertEqual(reopened.usage()['packets'],2)
        with self.assertRaises(self.module.InboxRejected):self.module.RetainedInbox(self.connect())
        other=self.root/'byte_quota.sqlite';connection=sqlite3.connect(other);self.connections.append(connection)
        packet=self.packet();limited=self.module.RetainedInbox(connection,create=True,payload_limit=len(packet))
        limited.receive(packet,self.key,self.policy,1001)
        with self.assertRaises(codec.Rejected):limited.receive(self.packet('2'*32),self.key,self.policy,1001)
        self.assertEqual(limited.usage()['payload_bytes'],len(packet))

    def test_uncertain_commit_keeps_packet_and_blocks_replay(self):
        connection=self.connect(factory=UncertainCommit);store=self.inbox(connection)
        raw=self.packet();connection.fail_after_commit=True
        with self.assertRaises(codec.Rejected):store.receive(raw,self.key,self.policy,1001)
        receipt=store.inspect('worker-fixture','host_to_guest','1'*32)
        self.assertIsNotNone(receipt)
        self.assertEqual(store.read_packet('worker-fixture','host_to_guest','1'*32,receipt.packet_sha256),raw)
        with self.assertRaises(codec.Rejected):store.receive(raw,self.key,self.policy,1001)
        self.assertEqual(store.usage()['packets'],1)

    def test_concurrent_connections_have_one_atomic_packet_claim(self):
        self.inbox();raw=self.packet();results=[];errors=[]
        def receive():
            connection=sqlite3.connect(self.path,timeout=5)
            try:
                store=self.module.RetainedInbox(connection)
                try:store.receive(raw,self.key,self.policy,1001);results.append(True)
                except codec.Rejected:results.append(False)
            except Exception as error:errors.append(type(error).__name__)
            finally:connection.close()
        threads=[threading.Thread(target=receive) for _ in range(8)]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertEqual(errors,[]);self.assertEqual(sum(results),1)
        reopened=self.module.RetainedInbox(self.connect())
        self.assertEqual(reopened.usage()['packets'],1)

    def test_unknown_store_and_schema_changes_are_preserved_and_refused(self):
        connection=self.connect();connection.execute('CREATE TABLE private_fixture(value TEXT)')
        connection.execute("INSERT INTO private_fixture VALUES('synthetic only')");connection.commit()
        before=connection.execute('SELECT * FROM sqlite_master').fetchall()
        with self.assertRaises(self.module.InboxRejected):self.inbox(connection)
        self.assertEqual(connection.execute('SELECT * FROM sqlite_master').fetchall(),before)
        self.assertEqual(connection.execute('SELECT * FROM private_fixture').fetchall(),[('synthetic only',)])
        other=sqlite3.connect(self.root/'changed_schema.sqlite');self.connections.append(other)
        store=self.module.RetainedInbox(other,create=True)
        other.execute('CREATE TABLE unexpected(value)');other.commit()
        with self.assertRaises(codec.Rejected):store.receive(self.packet(),self.key,self.policy,1001)

    def test_unsafe_durability_memory_and_open_transaction_refused(self):
        memory=sqlite3.connect(':memory:');self.connections.append(memory)
        with self.assertRaises(self.module.InboxRejected):self.inbox(memory)
        connection=self.connect();connection.execute('PRAGMA synchronous=OFF')
        with self.assertRaises(self.module.InboxRejected):self.inbox(connection)
        connection.execute('PRAGMA synchronous=FULL');store=self.inbox(connection)
        connection.execute('BEGIN IMMEDIATE')
        with self.assertRaises(codec.Rejected):store.receive(self.packet(),self.key,self.policy,1001)
        self.assertTrue(connection.in_transaction);connection.rollback()
        self.assertEqual(store.usage()['packets'],0)
        connection.execute('PRAGMA synchronous=OFF')
        with self.assertRaises(codec.Rejected):store.receive(self.packet(),self.key,self.policy,1001)

    def test_wrong_scope_digest_and_corruption_never_return_payload(self):
        connection=self.connect();store=self.inbox(connection);raw=self.packet()
        receipt=store.receive(raw,self.key,self.policy,1001).receipt
        self.assertIsNone(store.inspect('different-worker','host_to_guest','1'*32))
        with self.assertRaises(self.module.InboxRejected):store.read_packet('worker-fixture','host_to_guest','1'*32,'0'*64)
        connection.execute('UPDATE retained_packets_v1 SET packet=?',(b'corrupt synthetic packet',));connection.commit()
        with self.assertRaises(self.module.InboxRejected):store.inspect('worker-fixture','host_to_guest','1'*32)
        with self.assertRaises(self.module.InboxRejected):store.read_packet('worker-fixture','host_to_guest','1'*32,receipt.packet_sha256)

    def test_expired_packet_is_retained_as_data_without_reexecution(self):
        store=self.inbox();raw=self.packet();receipt=store.receive(raw,self.key,self.policy,1001).receipt
        with self.assertRaises(codec.Rejected):store.receive(raw,self.key,self.policy,5000)
        self.assertEqual(store.read_packet('worker-fixture','host_to_guest','1'*32,receipt.packet_sha256),raw)
        self.assertFalse(store.inspect('worker-fixture','host_to_guest','1'*32).execution_authorized)

    def test_full_project_parts_use_atomic_inbox_and_original_reassembly(self):
        from isolated_workers.protocol.test_task_transfer import fixture
        from backend.core.coding_vm_transfer import prepare_vm_transfer,restore_vm_transfer
        admission,contents=fixture({'src/日本語.json':b'x'*(2*1024*1024),'.config/settings.json':b'{}'})
        plan=prepare_vm_transfer(admission,contents,admission,direction='host_to_guest')
        connection=self.connect();store=self.inbox(connection)
        received={};retained=[]
        for number,(path,data) in enumerate(plan.transport_files.items()):
            policy=codec.Policy('worker-fixture','owner-fixture',admission['base_image_sha256'],
                                'host_to_guest',frozenset({path}),{path:hashlib.sha256(data).hexdigest()})
            raw=codec.pack(self.key,policy,'message','',{path:data},f'{number:032x}',1000,1100)
            delivery=store.receive(raw,self.key,policy,1001)
            received[delivery.bundle.files[0].path]=delivery.bundle.files[0].data
            retained.append((policy,raw,delivery.receipt))
        header=received.pop(plan.manifest_path)
        self.assertEqual(restore_vm_transfer(header,received,admission,direction='host_to_guest').contents,contents)
        self.assertEqual(store.usage()['payload_bytes'],sum(len(raw) for _,raw,_ in retained))
        connection.close();reopened=self.module.RetainedInbox(self.connect())
        for policy,raw,receipt in retained:
            self.assertEqual(reopened.read_packet(receipt.worker,receipt.direction,receipt.nonce,receipt.packet_sha256),raw)
            with self.assertRaises(codec.Rejected):reopened.receive(raw,self.key,policy,1001)
        self.assertEqual(reopened.usage()['packets'],len(plan.transport_files))

    def test_legacy_replay_store_is_not_adopted_or_migrated(self):
        from isolated_workers.protocol.replay_claims import ReplayClaims
        connection=self.connect();ReplayClaims(connection,create=True)
        before=connection.execute('SELECT * FROM sqlite_master').fetchall()
        for create in (False,True):
            with self.assertRaises(self.module.InboxRejected):
                self.module.RetainedInbox(connection,create=create)
        self.assertEqual(connection.execute('SELECT * FROM sqlite_master').fetchall(),before)

    def test_read_apis_refuse_caller_transaction_and_schema_drift_without_rollback(self):
        connection=self.connect();store=self.inbox(connection);raw=self.packet()
        receipt=store.receive(raw,self.key,self.policy,1001).receipt
        calls=[lambda:store.inspect('worker-fixture','host_to_guest','1'*32),
               lambda:store.read_packet('worker-fixture','host_to_guest','1'*32,receipt.packet_sha256),
               lambda:store.usage(), lambda:self.module.RetainedInbox(connection)]
        connection.execute('BEGIN IMMEDIATE')
        for call in calls:
            with self.assertRaises(self.module.InboxRejected):call()
            self.assertTrue(connection.in_transaction)
        connection.rollback()
        connection.execute('CREATE TABLE unexpected(value)');connection.commit()
        for call in calls:
            with self.assertRaises(self.module.InboxRejected):call()

    def test_persisted_quota_changes_and_invalid_limits_are_refused(self):
        for values in [dict(packet_limit=True),dict(packet_limit=0),dict(packet_limit=257),
                       dict(payload_limit=True),dict(payload_limit=0),dict(payload_limit=32*1024*1024+1)]:
            with self.assertRaises(self.module.InboxRejected):self.inbox(self.connect(),**values)
        connection=self.connect();store=self.inbox(connection,packet_limit=2,payload_limit=10000)
        connection.execute('UPDATE retained_inbox_config_v1 SET packet_limit=3');connection.commit()
        with self.assertRaises(self.module.InboxRejected):store.usage()
        with self.assertRaises(codec.Rejected):store.receive(self.packet(),self.key,self.policy,1001)

    def test_commit_return_without_terminal_transaction_never_accepts_packet(self):
        connection=self.connect(factory=UncommittedConnection);store=self.inbox(connection)
        connection.suppress_commit=True
        with self.assertRaises(codec.Rejected):store.receive(self.packet(),self.key,self.policy,1001)
        self.assertFalse(connection.in_transaction)
        connection.suppress_commit=False
        self.assertEqual(store.usage()['packets'],0)

    def test_explicit_autocommit_mode_refuses_unconfirmed_initialization_without_leaving_transaction(self):
        if not hasattr(sqlite3.Connection,'autocommit'):
            self.skipTest('Explicit SQLite connection autocommit requires Python3.12')
        connection=self.connect(autocommit=True)
        with self.assertRaises(self.module.InboxRejected):self.inbox(connection)
        self.assertFalse(connection.in_transaction)
        self.assertEqual(connection.execute('SELECT * FROM sqlite_master').fetchall(),[])


if __name__=='__main__':unittest.main()
