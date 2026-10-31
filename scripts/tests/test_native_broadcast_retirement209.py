"""Offline retirement checks: no external bridge probes or pretend dispatch."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[2]

class NativeBroadcastRetirement209Tests(unittest.TestCase):
    def test_active_probe_matrix_never_contacts_retired_bridge(self):
        from native_studio import engine
        with patch.object(engine,'_probe',return_value=False) as probe,patch.object(engine,'_listen_owners',return_value={}):
            states=engine.probe_ports()
        self.assertNotIn(4455,states)
        self.assertNotIn(4455,[call.args[0] for call in probe.call_args_list])

    def test_telemetry_keeps_old_bit_positions_without_an_active_bridge(self):
        from native_studio.engine import PORT_MATRIX
        from native_studio.telemetry_shm import PORT_ORDER
        self.assertEqual([p for p,_ in PORT_ORDER].index(8005),8)
        self.assertEqual(tuple(p for p,_ in PORT_ORDER if p!=4455),tuple(PORT_MATRIX))

    def test_published_mask_uses_legacy_slots_and_active_count_without_reserved_bit(self):
        from native_studio import telemetry_hub as module
        gpu=Mock();gpu.sample.return_value={'detected':False}
        hub=module.TelemetryHub(gpu)
        writer=Mock()
        hub._stop.wait=lambda _:hub._stop.set()
        values={'cpu_pct':0,'ram_pct':0,'ram_used_gb':0,'ram_total_gb':1}
        with patch.object(module,'TelemetryWriter',return_value=writer),patch.object(module,'sample_system',return_value=values),patch.object(module,'probe_ports',return_value={8005:{'online':True},11435:{'online':True},4455:{'online':True}}):
            hub._sample_until_stopped()
        frame=writer.write.call_args.args[0]
        self.assertEqual(frame['ports_mask'],(1<<8)|(1<<24))
        self.assertEqual(frame['ports_total'],24)
        self.assertEqual(frame['ports_online'],2)

    def test_executive_observations_drop_retired_socket(self):
        from native_studio.executive_service import PORTS
        self.assertNotIn(4455,PORTS)

    def test_lexicon_cannot_claim_or_dispatch_an_external_scene_swap(self):
        from PyQt6.QtWidgets import QApplication,QPushButton
        from native_studio.lexicon_view import LexiconNativeView
        app=QApplication.instance() or QApplication([])
        bus=Mock()
        widget=LexiconNativeView(bus)
        try:
            self.assertFalse(hasattr(widget,'_test_obs_trigger'))
            self.assertFalse(any('OBS' in b.text() for b in widget.findChildren(QPushButton)))
            bus.submit.assert_not_called()
        finally:widget.deleteLater()

if __name__=='__main__':unittest.main()
