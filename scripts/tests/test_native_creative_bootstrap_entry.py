"""Explicit bootstrap ordering fixtures; no Qt, credentials or real service."""
import unittest
from unittest.mock import Mock,patch
from native_studio.creative_session import bootstrap_native_session,CreativeSessionError

class BootstrapEntry(unittest.TestCase):
    def test_ordinary_launch_never_reads_pipe_or_creates_session(self):
        factory=Mock()
        with patch('native_studio.creative_session.read_bootstrap_pipe') as read:
            self.assertIsNone(bootstrap_native_session(['studio.exe'],object(),session_factory=factory))
        read.assert_not_called();factory.assert_not_called()

    def test_extra_arguments_are_denied_before_pipe_or_network(self):
        with patch('native_studio.creative_session.read_bootstrap_pipe') as read:
            with self.assertRaises(CreativeSessionError):bootstrap_native_session(['studio.exe','--native-creative-bootstrap','project'],object())
        read.assert_not_called()

    def test_pipe_then_sink_then_redemption_before_return(self):
        order=[];packet=object();session=Mock()
        session.redeem.side_effect=lambda value:order.append('redeem')
        with patch('native_studio.creative_session.read_bootstrap_pipe',side_effect=lambda stream:(order.append('pipe') or packet)),patch('native_studio.creative_session.silence_native_bootstrap_output',side_effect=lambda:order.append('sink')):
            result=bootstrap_native_session(['studio.exe','--native-creative-bootstrap'],object(),session_factory=lambda:session)
        self.assertEqual(order,['pipe','sink','redeem']);self.assertEqual(result,(session,packet))

    def test_failure_closes_session_and_sanitizes_error(self):
        session=Mock();session.redeem.side_effect=RuntimeError('private fixture detail')
        with patch('native_studio.creative_session.read_bootstrap_pipe',return_value=object()),patch('native_studio.creative_session.silence_native_bootstrap_output'):
            with self.assertRaises(CreativeSessionError) as error:bootstrap_native_session(['studio.exe','--native-creative-bootstrap'],object(),session_factory=lambda:session)
        session.close.assert_called_once();self.assertNotIn('private fixture detail',str(error.exception))

if __name__=='__main__':unittest.main()
