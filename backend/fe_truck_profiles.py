"""Owned vehicle facts, not a routing service. No storage is opened on import."""
import asyncio
import hashlib
import json
import math
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from fe_express_owned_records import (
    bounded_body, canonical, connection, database_path, identifier, require_owner,
)

router = APIRouter(prefix='/api/v1/fe-express/driver-records/truck-profile', tags=['Owned truck profile'])
MEASUREMENTS = {'cargo_box_length_ft': 200, 'height_in': 400, 'width_in': 400,
                'overall_length_ft': 300, 'loaded_gross_lb': 1000000}
FIELDS = set(MEASUREMENTS) | {'schema_version', 'vehicle_configuration', 'axles',
    'dimensions_confirmed', 'weights_confirmed', 'hazmat_status', 'restrictions_notes', 'measurement_notes'}
_profile_transaction = threading.Lock()


@contextmanager
def profile_connection(path):
    # The retained helper initializes WAL before beginning its transaction. Serialize
    # this new caller's initial opens as well as writes; this is process-local only.
    headers = {'Cache-Control': 'private, no-store', 'Retry-After': '1'}
    if not _profile_transaction.acquire(timeout=10):
        raise HTTPException(503, 'Truck profile store is busy; retain and retry the same operation', headers=headers)
    try:
        with connection(path) as db:
            yield db
    except sqlite3.OperationalError as error:
        if 'locked' not in str(error).lower() and 'busy' not in str(error).lower():
            raise
        raise HTTPException(503, 'Truck profile store is busy; retain and retry the same operation', headers=headers) from error
    finally:
        _profile_transaction.release()


def positive(value, maximum):
    return type(value) in (int, float) and 0 < value <= maximum and math.isfinite(value)


def validate_profile(payload):
    if not isinstance(payload, dict) or set(payload) - FIELDS or type(payload.get('schema_version')) is not int or payload['schema_version'] != 1:
        raise HTTPException(422, 'Unknown truck profile schema or fields')
    for name, maximum in MEASUREMENTS.items():
        if payload.get(name) is not None and not positive(payload[name], maximum):
            raise HTTPException(422, f'{name} must be a positive finite number in its named unit')
    if payload.get('vehicle_configuration', 'unknown') not in ('unknown', 'straight_truck', 'tractor_trailer', 'other'):
        raise HTTPException(422, 'Invalid vehicle configuration')
    if payload.get('hazmat_status', 'unknown') not in ('unknown', 'none', 'declared'):
        raise HTTPException(422, 'Invalid hazardous-material status')
    for name in ('dimensions_confirmed', 'weights_confirmed'):
        if name in payload and type(payload[name]) is not bool:
            raise HTTPException(422, 'Confirmation must be a boolean')
    for name in ('restrictions_notes', 'measurement_notes'):
        if name in payload and (not isinstance(payload[name], str) or len(payload[name]) > 4000):
            raise HTTPException(422, 'Notes must be bounded original strings')
    axles = payload.get('axles', [])
    if not isinstance(axles, list) or len(axles) > 16:
        raise HTTPException(422, 'At most 16 explicitly identified axles are supported')
    ids = set()
    for axle in axles:
        if not isinstance(axle, dict) or set(axle) - {'axle_id', 'actual_weight_lb'}:
            raise HTTPException(422, 'Invalid axle fields')
        axle_id = identifier(axle.get('axle_id'))
        if axle_id in ids:
            raise HTTPException(422, 'Duplicate axle identifier')
        ids.add(axle_id)
        if axle.get('actual_weight_lb') is not None and not positive(axle['actual_weight_lb'], 1000000):
            raise HTTPException(422, 'Axle weight must be positive finite pounds')
    if payload.get('dimensions_confirmed') and (
        payload.get('vehicle_configuration', 'unknown') == 'unknown' or
        any(payload.get(name) is None for name in ('height_in', 'width_in', 'overall_length_ft'))
    ):
        raise HTTPException(422, 'Complete actual vehicle dimensions before confirming')
    if payload.get('weights_confirmed') and (
        payload.get('loaded_gross_lb') is None or not axles or
        any(axle.get('actual_weight_lb') is None for axle in axles)
    ):
        raise HTTPException(422, 'Complete actual gross and individual axle weights before confirming')


def readiness(payload):
    payload = payload or {}
    missing = [name for name in ('height_in', 'width_in', 'overall_length_ft', 'loaded_gross_lb')
               if payload.get(name) is None]
    if payload.get('vehicle_configuration', 'unknown') == 'unknown':
        missing.append('vehicle_configuration')
    if not payload.get('axles') or any(axle.get('actual_weight_lb') is None for axle in payload.get('axles', [])):
        missing.append('actual_axle_weights')
    for name in ('dimensions_confirmed', 'weights_confirmed'):
        if not payload.get(name):
            missing.append(name)
    if payload.get('hazmat_status', 'unknown') == 'unknown':
        missing.append('hazmat_status')
    return {'routing_ready': False, 'missing_vehicle_fields': missing,
            'provider_qualified': False, 'reason': 'Truck routing is not configured or qualified'}


def schema(db):
    # Individual statements keep DDL inside the existing transaction; no executescript commit.
    db.execute('''CREATE TABLE IF NOT EXISTS truck_profile_revisions(
        owner TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL,
        updated_at TEXT NOT NULL, PRIMARY KEY(owner, revision))''')
    db.execute('''CREATE TABLE IF NOT EXISTS truck_profile_operations(
        owner TEXT NOT NULL, op_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
        result TEXT NOT NULL, PRIMARY KEY(owner, op_id))''')


def decode(row):
    return {'revision': row['revision'], 'payload': json.loads(row['payload']), 'updated_at': row['updated_at']}


@router.get('')
def current(owner=Depends(require_owner), path=Depends(database_path)):
    with profile_connection(path) as db:
        schema(db)
        row = db.execute('SELECT * FROM truck_profile_revisions WHERE owner=? ORDER BY revision DESC LIMIT 1', (owner,)).fetchone()
        profile = decode(row) if row else None
        return {'profile': profile, 'revision': row['revision'] if row else 0,
                **readiness(profile['payload'] if profile else None)}


@router.get('/history')
def history(before_revision: int = 2147483647, owner=Depends(require_owner), path=Depends(database_path)):
    if before_revision < 1:
        raise HTTPException(422, 'Invalid history cursor')
    with profile_connection(path) as db:
        schema(db)
        rows = db.execute('SELECT * FROM truck_profile_revisions WHERE owner=? AND revision<? ORDER BY revision DESC LIMIT 21', (owner, before_revision)).fetchall()
        return {'profiles': [decode(row) for row in rows[:20]],
                'next_before_revision': rows[19]['revision'] if len(rows) > 20 else None,
                'routing_ready': False}


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('Non-finite JSON constant')


@router.post('')
async def save(request: Request, owner=Depends(require_owner), path=Depends(database_path)):
    try:
        operation = json.loads(await bounded_body(request, 32768), object_pairs_hook=reject_duplicates, parse_constant=reject_constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise HTTPException(422, 'Invalid profile JSON')
    if not isinstance(operation, dict) or set(operation) != {'op_id', 'base_revision', 'payload'}:
        raise HTTPException(422, 'Invalid profile operation')
    identifier(operation['op_id'])
    if type(operation['base_revision']) is not int or not 0 <= operation['base_revision'] < 2147483646:
        raise HTTPException(422, 'Invalid profile base revision')
    validate_profile(operation['payload'])
    return await asyncio.to_thread(store_profile, path, owner, operation)


def store_profile(path, owner, operation):
    fingerprint = hashlib.sha256(canonical(operation).encode()).hexdigest()
    with profile_connection(path) as db:
        schema(db)
        retry = db.execute('SELECT fingerprint,result FROM truck_profile_operations WHERE owner=? AND op_id=?', (owner, operation['op_id'])).fetchone()
        if retry:
            if retry['fingerprint'] != fingerprint:
                raise HTTPException(409, 'Operation ID already used with different profile content')
            return json.loads(retry['result'])
        revision = db.execute('SELECT COALESCE(MAX(revision),0) FROM truck_profile_revisions WHERE owner=?', (owner,)).fetchone()[0]
        if revision != operation['base_revision']:
            raise HTTPException(409, {'message': 'Truck profile revision conflict', 'current_revision': revision})
        payload = operation['payload']
        profile = {'revision': revision + 1, 'payload': payload, 'updated_at': datetime.now(timezone.utc).isoformat()}
        db.execute('INSERT INTO truck_profile_revisions VALUES(?,?,?,?)', (owner, profile['revision'], canonical(payload), profile['updated_at']))
        result = {'profile': profile, 'revision': profile['revision'], **readiness(payload)}
        db.execute('INSERT INTO truck_profile_operations VALUES(?,?,?,?)', (owner, operation['op_id'], fingerprint, canonical(result)))
        return result
