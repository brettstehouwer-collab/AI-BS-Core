"""Revision-checked shared portal preferences and inert form drafts."""
import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response

router = APIRouter(prefix='/workspace', tags=['FE Express workspace'])
MAX_BYTES = 512 * 1024
FIELDS = set('searchMiles searchEquipment searchBroker filterScore selectedBoard reportDriver reportsOpened tripForReport calcOrigin calcDest calcEquip calcMiles calcDeadhead calcPay calcWeight calcBroker homeBase searchOrigin searchDest minRpm minFlatPay maxWeight maxDeadhead vehicleFilter viewMode showEvaluator activeSubTab bolUploadNote bolFuelCost bolTollsCost bolStatusUpdate newDriverName newDriverPhone newDriverEmail newDriverSSN4 newDriverDL newDriverDLState newDriverPayModel newDriverPayRate newDriverMedCardExp newDriverMVRStatus newDriverW9Status newDriverNotes settleDate settleLane settleMiles settleGrossPay settleFuelDeduct settleAdvance settlePayMethod settleNotes blastBidAmount cpmParams claimParams report.week report.logDate report.exportFormat report.sheetDrafts report.kind'.split())


def database_path():
    return Path(__file__).resolve().parents[1] / 'saved_data' / 'fe_express.db'


def validate_values(values):
    if not isinstance(values, dict) or len(values) > 500:
        raise HTTPException(422, 'Invalid portal snapshot.')
    for key in values:
        if key not in FIELDS and not re.fullmatch(r'report\.(?:day|shipment|shipmentId):[A-Za-z0-9_-]{1,100}:\d{4}-\d{2}-\d{2}', key):
            raise HTTPException(422, 'Unknown portal field.')
        structured = key in {'cpmParams', 'claimParams', 'report.sheetDrafts'} or key.startswith(('report.day:', 'report.shipment:'))
        if structured:
            if values[key] is not None and not isinstance(values[key], dict):
                raise HTTPException(422, 'Invalid draft structure.')
        elif not isinstance(values[key], (str, int, float, bool)):
            raise HTTPException(422, 'Invalid portal selection.')
    nodes = [0]

    def visit(value, depth=0):
        nodes[0] += 1
        if depth > 8 or nodes[0] > 15000:
            raise HTTPException(422, 'Portal snapshot is too complex.')
        if isinstance(value, dict):
            for key, item in value.items():
                if len(key) > 220 or key in {'__proto__', 'constructor', 'prototype'}:
                    raise HTTPException(422, 'Invalid portal field.')
                visit(item, depth + 1)
        elif isinstance(value, list):
            raise HTTPException(422, 'Lists are not portal form fields.')
        elif isinstance(value, str):
            if len(value) > 4000:
                raise HTTPException(422, 'Portal text is too long.')
        elif isinstance(value, float) and not math.isfinite(value):
            raise HTTPException(422, 'Portal numbers must be finite.')
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            raise HTTPException(422, 'Invalid portal value.')
    visit(values)


def connection(path):
    db = sqlite3.connect(str(path), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS fe_portal_workspace (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, saved_at TEXT NOT NULL, payload TEXT NOT NULL)')
    return db


@router.get('')
def read_workspace(response: Response, path=Depends(database_path)):
    response.headers['Cache-Control'] = 'no-store'
    db = connection(path)
    try:
        row = db.execute('SELECT revision,saved_at,payload FROM fe_portal_workspace WHERE id=1').fetchone()
        return dict(revision=row['revision'], saved_at=row['saved_at'], values=json.loads(row['payload'])) if row else dict(revision=0, saved_at=None, values={})
    finally:
        db.close()


@router.put('')
async def save_workspace(request: Request, response: Response, path=Depends(database_path)):
    response.headers['Cache-Control'] = 'no-store'
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_BYTES:
            raise HTTPException(413, 'Portal save exceeds 512 KiB. Finalize or discard older drafts first.')
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate field')
                result[key] = value
            return result
        item = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise HTTPException(422, 'Invalid portal JSON.')
    if not isinstance(item, dict) or set(item) != {'revision', 'values'} or type(item['revision']) is not int or item['revision'] < 0:
        raise HTTPException(422, 'A valid saved revision is required.')
    validate_values(item['values'])
    db = connection(path)
    try:
        db.execute('BEGIN IMMEDIATE')
        current = db.execute('SELECT revision FROM fe_portal_workspace WHERE id=1').fetchone()
        revision = current['revision'] if current else 0
        if revision != item['revision']:
            raise HTTPException(409, 'Another session saved newer portal changes. Your edits are still here. Open a fresh tab to review the newer save before replacing anything.')
        saved_at = datetime.now(timezone.utc).isoformat()
        db.execute('INSERT INTO fe_portal_workspace VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,saved_at=excluded.saved_at,payload=excluded.payload', (revision + 1, saved_at, json.dumps(item['values'], allow_nan=False)))
        db.commit()
        return dict(revision=revision + 1, saved_at=saved_at)
    finally:
        db.close()
