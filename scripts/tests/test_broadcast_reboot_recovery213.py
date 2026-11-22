"""Read-only process/status fixtures; never start capture or network output."""
import unittest
from unittest.mock import patch
from native_studio import broadcast_secondary_control as client


class RebootRecoveryTests(unittest.TestCase):
    def status(self, **changes):
        raw = dict(protocol_version=2, status='running_unverified', process_running=True,
                   controller_create_time=100.0, encoder_create_time=110.0)
        raw.update(changes)
        with patch.object(client, '_read_status', return_value=(raw, False)), \
             patch.object(client, '_read_legacy_status', return_value=({}, False)), \
             patch.object(client, '_verified_owner', return_value=None), \
             patch.object(client.psutil, 'boot_time', return_value=200.0):
            return client.read_broadcast_status()

    def test_verified_previous_boot_epochs_do_not_permanently_lock_start(self):
        state = self.status()
        self.assertEqual(state['status'], 'stopped')
        self.assertTrue(state['can_start'])
        self.assertFalse(state['active'])

    def test_current_boot_or_invalid_epochs_remain_held(self):
        for changes in ({'controller_create_time': 210.0}, {'encoder_create_time': 210.0},
                        {'controller_create_time': None}, {'encoder_create_time': True},
                        {'controller_create_time': float('nan')}, {'protocol_version': 1}):
            with self.subTest(changes=changes):
                state = self.status(**changes)
                self.assertEqual(state['status'], 'owner_unverified')
                self.assertFalse(state['can_start'])

    def test_existing_controller_still_blocks_dispatch(self):
        from contextlib import nullcontext
        with patch.object(client, 'read_broadcast_status', return_value=client._empty()), \
             patch.object(client, '_start_lock', return_value=nullcontext()), \
             patch.object(client, '_existing_controller', return_value=True), \
             patch.object(client, '_spawn') as spawn:
            state = client.start_broadcast({'source_mode': 'auto_game', 'source': None, 'targets': ['youtube']})
            self.assertEqual(state['status'], 'controller_present')
            spawn.assert_not_called()

    def test_recovery_archives_before_reset_and_never_touches_a_current_controller(self):
        from contextlib import nullcontext
        from pathlib import Path
        raw = {'protocol_version': 2, 'controller_create_time': 100.0, 'encoder_create_time': 110.0}
        paths = {'status': Path('fixture/status.json')}
        with patch.object(client, '_start_lock', return_value=nullcontext()), \
             patch.object(client, '_read_status', return_value=(raw, False)), \
             patch.object(client, '_existing_controller', return_value=False), \
             patch.object(client.psutil, 'boot_time', return_value=200.0), \
             patch.object(client, 'ipc_paths', return_value=paths), \
             patch.object(client, 'write_private_json') as write:
            result = client.recover_previous_boot_session()
            self.assertEqual(result['status'], 'previous_boot_recovered')
            self.assertEqual(write.call_count, 2)
            self.assertEqual(write.call_args_list[0].args[1], raw)
            self.assertEqual(write.call_args_list[1].args[0], paths['status'])
            self.assertFalse(write.call_args_list[1].args[1]['process_running'])
        with patch.object(client, '_start_lock', return_value=nullcontext()), \
             patch.object(client, '_read_status', return_value=(raw, False)), \
             patch.object(client, '_existing_controller', return_value=True), \
             patch.object(client.psutil, 'boot_time', return_value=200.0), \
             patch.object(client, 'write_private_json') as write:
            self.assertEqual(client.recover_previous_boot_session()['status'], 'controller_present')
            write.assert_not_called()
