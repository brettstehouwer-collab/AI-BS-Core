"""Unit tests for Sheltered Hub stations and spatial zone validators."""
import unittest

from native_studio.game_engine.sheltered_hub_fields import (
    validate_writing_desk,
    validate_memory_shelves,
    validate_shared_play,
    find_spatial_zone,
    PENCIL_MODES,
    SPATIAL_ZONES,
)
from native_studio.game_engine.creator_payload import PayloadError


class TestShelteredHubFields(unittest.TestCase):
    def test_writing_desk_valid(self):
        fields = {
            'pencil_claimed': False,
            'mode': 'record',
            'notes_written': 0,
            'x': -38.5,
            'y': 1.1,
            'z': 16.5,
        }
        res = validate_writing_desk(fields)
        self.assertFalse(res['pencil_claimed'])
        self.assertEqual(res['mode'], 'record')
        self.assertEqual(res['notes_written'], 0)

    def test_writing_desk_cannot_write_without_pencil(self):
        fields = {
            'pencil_claimed': False,
            'mode': 'trace',
            'notes_written': 1,
            'x': -38.5,
            'y': 1.1,
            'z': 16.5,
        }
        with self.assertRaises(PayloadError):
            validate_writing_desk(fields)

    def test_writing_desk_with_claimed_pencil(self):
        fields = {
            'pencil_claimed': True,
            'mode': 'sketch',
            'notes_written': 3,
            'x': -38.5,
            'y': 1.1,
            'z': 16.5,
        }
        res = validate_writing_desk(fields)
        self.assertTrue(res['pencil_claimed'])
        self.assertEqual(res['mode'], 'sketch')
        self.assertEqual(res['notes_written'], 3)

    def test_memory_shelves_valid(self):
        fields = {
            'items_placed': 2,
            'capacity': 12,
            'secret_revealed': False,
            'x': -30.0,
            'y': 1.5,
            'z': 10.0,
        }
        res = validate_memory_shelves(fields)
        self.assertEqual(res['items_placed'], 2)
        self.assertFalse(res['secret_revealed'])

    def test_memory_shelves_secret_requires_at_least_three_items(self):
        fields = {
            'items_placed': 2,
            'capacity': 12,
            'secret_revealed': True,
            'x': -30.0,
            'y': 1.5,
            'z': 10.0,
        }
        with self.assertRaises(PayloadError):
            validate_memory_shelves(fields)

    def test_memory_shelves_secret_revealed_with_three_items(self):
        fields = {
            'items_placed': 3,
            'capacity': 12,
            'secret_revealed': True,
            'x': -30.0,
            'y': 1.5,
            'z': 10.0,
        }
        res = validate_memory_shelves(fields)
        self.assertTrue(res['secret_revealed'])

    def test_shared_play_power_dependency(self):
        fields = {
            'display_powered': False,
            'session_active': True,
            'x': -35.0,
            'y': 1.0,
            'z': 9.0,
        }
        with self.assertRaises(PayloadError):
            validate_shared_play(fields)

    def test_shared_play_active_when_powered(self):
        fields = {
            'display_powered': True,
            'session_active': True,
            'x': -35.0,
            'y': 1.0,
            'z': 9.0,
        }
        res = validate_shared_play(fields)
        self.assertTrue(res['display_powered'])
        self.assertTrue(res['session_active'])

    def test_find_spatial_zone(self):
        self.assertEqual(find_spatial_zone((-32.0, 0.0, -26.0)), 'nook_awakening')
        self.assertEqual(find_spatial_zone((-37.0, 0.0, -15.0)), 'corridor_approach')
        self.assertEqual(find_spatial_zone((-33.0, 0.0, -3.0)), 'fault_trench')
        self.assertEqual(find_spatial_zone((-42.0, 0.0, -5.0)), 'relay_bypass_socket')
        self.assertEqual(find_spatial_zone((-37.0, 0.0, 2.0)), 'threshold_aperture')
        self.assertEqual(find_spatial_zone((-36.0, 0.0, 10.0)), 'sheltered_hub')
        self.assertEqual(find_spatial_zone((-37.0, 0.0, 17.0)), 'pencil_room')
        self.assertIsNone(find_spatial_zone((100.0, 100.0, 100.0)))


if __name__ == '__main__':
    unittest.main()
