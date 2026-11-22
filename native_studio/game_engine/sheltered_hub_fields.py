"""Sheltered Hub and Pencil Room station definitions and authoring helpers.

Coordinates and validated schemas for:
- Writing Desk (pencil claim, writing mode, note journaling)
- Memory Shelves (keepsake placement, capacity, secret compartment)
- Shared Play Corner (restored power display, interactive session)
- 7 Spatial Trigger Zones for narrative audio guidance
"""
from dataclasses import dataclass
import math
from typing import Dict, Any, List, Optional, Tuple

from .creator_payload import PayloadError

SHELTERED_HUB_CAPABILITY = 'chapter-sheltered-hub-stations-v1'

WRITING_DESK_TYPE = 'firstboot.WritingDesk'
MEMORY_SHELVES_TYPE = 'firstboot.MemoryShelves'
SHARED_PLAY_TYPE = 'firstboot.SharedPlay'

STATION_TYPES = (WRITING_DESK_TYPE, MEMORY_SHELVES_TYPE, SHARED_PLAY_TYPE)

PENCIL_MODES = ('record', 'trace', 'sketch')

SPATIAL_ZONES = (
    'nook_awakening',
    'corridor_approach',
    'fault_trench',
    'relay_bypass_socket',
    'threshold_aperture',
    'sheltered_hub',
    'pencil_room',
)

ZONE_BOUNDS = {
    'nook_awakening': ((-36.5, -2.0, -31.0), (-28.5, 4.0, -21.0)),
    'corridor_approach': ((-39.0, -2.0, -21.0), (-34.0, 4.0, -9.0)),
    'fault_trench': ((-36.0, -2.0, -9.0), (-30.0, 4.0, 0.0)),
    'relay_bypass_socket': ((-45.0, -2.0, -9.0), (-39.0, 4.0, 0.0)),
    'threshold_aperture': ((-43.0, -2.0, 0.0), (-31.0, 4.0, 5.0)),
    'sheltered_hub': ((-44.0, -2.0, 5.0), (-29.0, 5.0, 14.0)),
    'pencil_room': ((-41.0, -2.0, 14.0), (-32.0, 5.0, 22.0)),
}


def validate_vec3(fields: Dict[str, Any], prefix: str = '') -> Tuple[float, float, float]:
    values = tuple(fields.get(f'{prefix}{axis}') for axis in 'xyz')
    for val in values:
        if type(val) not in (int, float) or not math.isfinite(val):
            raise PayloadError(f'Station coordinates require finite {prefix}x/y/z numbers')
    return (float(values[0]), float(values[1]), float(values[2]))


def validate_writing_desk(fields: Dict[str, Any]) -> Dict[str, Any]:
    pencil_claimed = fields.get('pencil_claimed', False)
    if type(pencil_claimed) is not bool:
        raise PayloadError('pencil_claimed must be a boolean')

    mode = fields.get('mode', 'record')
    if mode not in PENCIL_MODES:
        raise PayloadError(f'mode must be one of {PENCIL_MODES}')

    notes_written = fields.get('notes_written', 0)
    if type(notes_written) is not int or notes_written < 0:
        raise PayloadError('notes_written must be a non-negative integer')

    if notes_written > 0 and not pencil_claimed:
        raise PayloadError('Cannot record notes before pencil is claimed')

    validate_vec3(fields)
    return {
        'pencil_claimed': pencil_claimed,
        'mode': mode,
        'notes_written': notes_written,
        'x': float(fields['x']),
        'y': float(fields['y']),
        'z': float(fields['z']),
    }


def validate_memory_shelves(fields: Dict[str, Any]) -> Dict[str, Any]:
    items_placed = fields.get('items_placed', 0)
    capacity = fields.get('capacity', 12)
    secret_revealed = fields.get('secret_revealed', False)

    if type(items_placed) is not int or items_placed < 0:
        raise PayloadError('items_placed must be a non-negative integer')
    if type(capacity) is not int or capacity <= 0:
        raise PayloadError('capacity must be a positive integer')
    if items_placed > capacity:
        raise PayloadError('items_placed cannot exceed capacity')
    if type(secret_revealed) is not bool:
        raise PayloadError('secret_revealed must be a boolean')

    if items_placed < 3 and secret_revealed:
        raise PayloadError('Secret compartment requires at least 3 placed items')

    validate_vec3(fields)
    return {
        'items_placed': items_placed,
        'capacity': capacity,
        'secret_revealed': secret_revealed,
        'x': float(fields['x']),
        'y': float(fields['y']),
        'z': float(fields['z']),
    }


def validate_shared_play(fields: Dict[str, Any]) -> Dict[str, Any]:
    display_powered = fields.get('display_powered', False)
    session_active = fields.get('session_active', False)

    if type(display_powered) is not bool or type(session_active) is not bool:
        raise PayloadError('display_powered and session_active must be booleans')

    if session_active and not display_powered:
        raise PayloadError('Shared play session requires display power')

    validate_vec3(fields)
    return {
        'display_powered': display_powered,
        'session_active': session_active,
        'x': float(fields['x']),
        'y': float(fields['y']),
        'z': float(fields['z']),
    }


def find_spatial_zone(position: Tuple[float, float, float]) -> Optional[str]:
    x, y, z = position
    for zone, (min_p, max_p) in ZONE_BOUNDS.items():
        if (min_p[0] <= x <= max_p[0] and
            min_p[1] <= y <= max_p[1] and
            min_p[2] <= z <= max_p[2]):
            return zone
    return None
