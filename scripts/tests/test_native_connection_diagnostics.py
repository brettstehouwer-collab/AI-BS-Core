import json,unittest
from unittest.mock import Mock
from native_studio.local_connection import LocalConnection,ServiceIdentity
from native_studio import local_connection as m


class ConnectionDiagnosticTests(unittest.TestCase):
    def connection(self):
        identity=ServiceIdentity(12,123.5,r'C:\Fixture\service.exe','S-1-5-21-100')
        vault=Mock();vault.read.return_value=json.dumps({'schema':1,'origin':m.ORIGIN,'secret':'fixture-private-value','service':m.asdict(identity)}).encode()
        return LocalConnection(vault=vault,current_identity=lambda:identity,listener_identity=lambda:identity)

    def test_report_contains_only_stage_booleans_never_credential_or_identity(self):
        client=self.connection();report=m.connection_diagnostics(connection=client)
        self.assertTrue(report['available'])
        encoded=json.dumps(report)
        for private in ['fixture-private-value','service.exe','S-1-5-21-100','X-Admin-Key']:
            self.assertNotIn(private,encoded)
        client.vault.write.assert_not_called()

    def test_failures_identify_stage_without_exception_message(self):
        for stage in ['vault_read','current_identity','listener_identity']:
            client=self.connection()
            error=PermissionError('fixture-private-value')
            if stage=='vault_read':client.vault.read.side_effect=error
            else:setattr(client,stage,Mock(side_effect=error))
            report=m.connection_diagnostics(connection=client)
            self.assertEqual(report['stage'],stage)
            self.assertEqual(report['errorType'],'PermissionError')
            self.assertFalse(report['available'])
            self.assertNotIn('fixture-private-value',json.dumps(report))
            client.vault.write.assert_not_called()


if __name__=='__main__':unittest.main()
