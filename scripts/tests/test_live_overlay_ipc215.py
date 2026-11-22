from pathlib import Path
import unittest


class OverlayIpcNamespace(unittest.TestCase):
    def test_only_exact_owned_overlay_and_recovery_names_can_be_written(self):
        from native_studio.broadcast_ipc import allowed_write_path
        root=Path('fixture/private')
        paths={'status':root/'broadcast_secondary_status.json','command':root/'broadcast_secondary_command.json','stop':root/'broadcast_secondary.stop'}
        for name in ('live_overlay_config.json','live_overlay_status.json',
                     'overlay_event_'+'a'*32+'.json','broadcast_previous_boot_'+'b'*32+'.json'):
            self.assertTrue(allowed_write_path(root/name,paths))
        for path in (root/'arbitrary.json',root/'overlay_event_bad.json',Path('elsewhere/live_overlay_config.json'),root/'../live_overlay_config.json'):
            self.assertFalse(allowed_write_path(path,paths))
