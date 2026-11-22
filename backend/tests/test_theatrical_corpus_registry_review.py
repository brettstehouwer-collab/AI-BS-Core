"""Schema drift must fail before every registry mutation, including promotion."""
import unittest

from backend.security.theatrical_corpus_boundary import CorpusBoundaryError
from backend.tests import test_theatrical_corpus_registry as registry_fixture


class RegistrySchemaReviewTests(unittest.TestCase):
    setUp = registry_fixture.RegistryTests.setUp
    tearDown = registry_fixture.RegistryTests.tearDown
    publish = registry_fixture.RegistryTests.publish

    def test_unknown_schema_cannot_run_trigger_during_deactivation(self):
        scope = self.publish()
        self.connection.execute('CREATE TABLE unexpected_audit (value TEXT)')
        self.connection.execute("CREATE TRIGGER unexpected_mutation AFTER UPDATE ON corpus_heads "
                                "BEGIN INSERT INTO unexpected_audit VALUES ('triggered'); END")
        self.connection.commit()
        with self.assertRaisesRegex(CorpusBoundaryError, '^INVALID_REGISTRY_SCHEMA$'):
            self.registry.deactivate('local_admin', 'play', expected_revision=scope.revision)
        self.assertEqual(self.connection.execute('SELECT revision FROM corpus_heads').fetchone()[0], scope.revision)
        self.assertEqual(self.connection.execute('SELECT * FROM unexpected_audit').fetchall(), [])

    def test_schema_drift_during_store_write_cannot_promote_pending_revision(self):
        def drift(collection):
            self.connection.execute('CREATE TABLE unexpected_audit (value TEXT)')
            self.connection.execute("CREATE TRIGGER unexpected_mutation AFTER UPDATE ON corpus_heads "
                                    "BEGIN INSERT INTO unexpected_audit VALUES ('triggered'); END")
            self.connection.commit()

        self.store.after_create = drift
        with self.assertRaisesRegex(CorpusBoundaryError, '^INVALID_REGISTRY_SCHEMA$'):
            self.publish()
        self.assertIsNone(self.connection.execute('SELECT revision FROM corpus_heads').fetchone()[0])
        self.assertEqual(self.connection.execute('SELECT state FROM corpus_revisions').fetchall(), [('PENDING',)])
        self.assertEqual(self.connection.execute('SELECT * FROM unexpected_audit').fetchall(), [])
        self.assertEqual(len(self.store.collections), 1)  # Preserve the failed candidate.


if __name__ == '__main__':
    unittest.main()
