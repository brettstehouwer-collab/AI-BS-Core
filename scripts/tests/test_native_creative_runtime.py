"""Optional startup publication and owned shutdown; no API/process activation."""
from types import SimpleNamespace
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from security import native_creative_runtime as runtime


class NativeCreativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.router=SimpleNamespace(_NATIVE_CREATIVE_CONTROLLER=None,_NATIVE_CREATIVE_ADAPTER=None,
            _issue_native_creative_grant=Mock())
        self.addCleanup(runtime._retained_controllers.clear)

    def test_disabled_configuration_leaves_globals_unconfigured(self):
        with patch('security.native_creative_config.load_reviewed_candidate',return_value=None), \
                patch.object(runtime.NativeCreativeController,'create')as create:
            self.assertIsNone(runtime.configure_native_creative(self.router))
        create.assert_not_called();self.assertIsNone(self.router._NATIVE_CREATIVE_CONTROLLER)
        self.assertIsNone(self.router._NATIVE_CREATIVE_ADAPTER)

    def test_invalid_configuration_never_publishes_partial_controller(self):
        with patch('security.native_creative_config.load_reviewed_candidate',side_effect=ValueError('invalid')):
            with self.assertRaises(ValueError):runtime.configure_native_creative(self.router)
        self.assertIsNone(self.router._NATIVE_CREATIVE_CONTROLLER)
        self.assertIsNone(self.router._NATIVE_CREATIVE_ADAPTER)

    def test_reviewed_candidate_uses_actual_router_and_bounded_capacity(self):
        candidate=object();controller=Mock();controller.adapter=object()
        with patch('security.native_creative_config.load_reviewed_candidate',return_value=candidate), \
                patch.object(runtime.NativeCreativeController,'create',return_value=controller)as create:
            self.assertIs(runtime.configure_native_creative(self.router),controller)
        args,kwargs=create.call_args
        self.assertIs(args[0],candidate);self.assertIs(args[2],self.router._issue_native_creative_grant)
        self.assertEqual(kwargs['capacity'],1);self.assertIs(kwargs['services'],self.router)
        self.assertIs(self.router._NATIVE_CREATIVE_CONTROLLER,controller)
        self.assertIs(self.router._NATIVE_CREATIVE_ADAPTER,controller.adapter)

    def test_existing_controller_cannot_be_replaced(self):
        old=object();self.router._NATIVE_CREATIVE_CONTROLLER=old
        with patch('security.native_creative_config.load_reviewed_candidate')as load:
            with self.assertRaises(RuntimeError):runtime.configure_native_creative(self.router)
        load.assert_not_called();self.assertIs(self.router._NATIVE_CREATIVE_CONTROLLER,old)

    def test_shutdown_unpublishes_before_drain_retains_failure_and_supports_explicit_retry(self):
        controller=Mock();controller.adapter=object()
        self.router._NATIVE_CREATIVE_CONTROLLER=controller;self.router._NATIVE_CREATIVE_ADAPTER=controller.adapter
        def incomplete():
            self.assertIsNone(self.router._NATIVE_CREATIVE_CONTROLLER)
            self.assertIsNone(self.router._NATIVE_CREATIVE_ADAPTER)
            return {'complete':False,'retained_resources':1,'pending_launches':0}
        controller.shutdown.side_effect=incomplete
        self.assertFalse(runtime.stop_native_creative(self.router,controller)['complete'])
        self.assertIn(controller,runtime._retained_controllers)
        controller.shutdown.side_effect=lambda:{'complete':True,'retained_resources':0,'pending_launches':0}
        self.assertTrue(runtime.stop_native_creative(self.router,controller)['complete'])
        self.assertNotIn(controller,runtime._retained_controllers)

    def test_shutdown_exception_retains_owner_and_does_not_unpublish_another_controller(self):
        controller=Mock();controller.adapter=object();other=Mock();other.adapter=object()
        self.router._NATIVE_CREATIVE_CONTROLLER=other;self.router._NATIVE_CREATIVE_ADAPTER=other.adapter
        controller.shutdown.side_effect=RuntimeError('Synthetic incomplete drain')
        with self.assertRaises(RuntimeError):runtime.stop_native_creative(self.router,controller)
        self.assertIn(controller,runtime._retained_controllers)
        self.assertIs(self.router._NATIVE_CREATIVE_CONTROLLER,other)
        self.assertIs(self.router._NATIVE_CREATIVE_ADAPTER,other.adapter)


if __name__=='__main__':unittest.main()
