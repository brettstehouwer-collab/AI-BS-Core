"""Preparation must never stand in for provider delivery or move real money.

All writes use isolated temporary SQLite files; no application service or provider.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.core import fe_express_dispatcher_dream_cockpit as cockpit
from backend.core import fe_express_owner_operator_engine as owner


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / 'synthetic.sqlite'
    monkeypatch.setattr(cockpit, 'DB_PATH', path)
    monkeypatch.setattr(owner, 'DB_PATH', str(path))
    owner.init_owner_operator_tables()
    cockpit.init_dream_dispatcher_tables()
    with sqlite3.connect(path) as connection:
        connection.execute('''CREATE TABLE fe_express_active_dispatches
            (dispatch_id TEXT PRIMARY KEY, load_id TEXT, gross_pay REAL,
             broker_name TEXT, broker_phone TEXT, origin TEXT, destination TEXT,
             bol_photo_url TEXT, fuel_cost REAL, driver_name TEXT)''')
        connection.execute('''INSERT INTO fe_express_active_dispatches VALUES
            ('SYNTHETIC-TRIP','SYNTHETIC-LOAD',1000,'Test broker','2025550100',
             'Test origin','Test destination','local_bol_photo.jpg',40,'Test driver')''')
        connection.execute('''CREATE TABLE IF NOT EXISTS fe_express_driver_settlements
            (settlement_id TEXT PRIMARY KEY, driver_id TEXT, dispatch_id TEXT,
             trip_date TEXT, origin_dest TEXT, total_miles REAL, gross_load_pay REAL,
             contractor_pay REAL, fuel_deduction REAL, net_payable REAL,
             payment_status TEXT, paid_at TEXT)''')
        connection.execute("INSERT INTO fe_express_driver_settlements (settlement_id,payment_status) VALUES ('HISTORICAL','UNCHANGED')")
    return path


def row(database, table):
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        return dict(connection.execute(f'SELECT * FROM {table} ORDER BY rowid DESC LIMIT 1').fetchone())


def preparation(result):
    assert result['status'] == 'PREPARED_LOCALLY'
    assert result['provider_connected'] is False
    assert result['delivery_confirmed'] is False
    assert result['provider_receipt'] is None


def test_bid_is_a_draft_without_dispatched_channels_or_fictional_latency(database):
    result = cockpit.execute_multi_channel_blast_bid(
        {'load_id': 'SYNTHETIC-LOAD', 'broker_name': 'Test broker'}, 500, {})
    preparation(result)
    assert result['channels'] == []
    assert result['requested_channels']
    assert 'execution_latency_ms' not in result
    saved = row(database, 'fe_express_blast_negotiations')
    assert saved['status'] == 'PREPARED_LOCALLY'
    assert json.loads(saved['channels_json']) == []
    assert saved['dispatched_at'] is None
    assert saved['response_time_sec'] is None


def test_capacity_draft_has_no_published_boards_or_auto_delete_claim(database):
    result = cockpit.broadcast_truck_capacity()
    preparation(result)
    assert result['published_boards'] == []
    assert len(result['requested_boards']) == 5
    assert result['auto_delete_on_book'] is False
    saved = row(database, 'fe_express_capacity_broadcasts')
    assert saved['broadcast_status'] == 'PREPARED_LOCALLY'
    assert json.loads(saved['posted_boards_json']) == []
    assert saved['dispatched_at'] is None


def test_lumper_draft_does_not_claim_sms_or_a_receipt_photo(database):
    result = cockpit.create_lumper_preapproval_request(
        'SYNTHETIC-TRIP', 'Test warehouse', 'Test broker', '2025550100', 175)
    preparation(result)
    assert result['urgent_night_dispatch_sms']
    saved = row(database, 'fe_express_lumper_escrow_ledger')
    assert saved['pre_approval_clause_sent'] == 0
    assert saved['lumper_receipt_photo_url'] is None
    assert saved['approval_code'] is None
    assert saved['escrow_status'] == 'PREPARED_LOCALLY'


def test_factoring_preparation_never_marks_missing_documents_submitted(database):
    result = owner.generate_instant_factoring_submission('SYNTHETIC-TRIP')
    preparation(result)
    assert result['documents_verified'] is False
    assert result['ratecon_url'] is None
    assert result['bol_url'] is None
    saved = row(database, 'fe_express_factoring_submissions')
    assert saved['status'] == 'PREPARED_LOCALLY'
    assert saved['submitted_at'] is None
    assert saved['funded_at'] is None
    # A second preparation retains the first record, rather than replacing history.
    again = owner.generate_instant_factoring_submission('SYNTHETIC-TRIP')
    assert result['submission_id'] != again['submission_id']


def test_legacy_gateway_cannot_fabricate_funding_or_pay_a_driver(database):
    result = owner.AsyncFactoringGatewayClient.execute_async_factoring_submission('SYNTHETIC-TRIP')
    preparation(result)
    assert result['batch_confirmation_code'] is None
    assert result['bank_deposit_eta'] is None
    assert result['driver_settlement_reconciled'] is False
    saved = row(database, 'fe_express_factoring_submissions')
    assert saved['status'] == 'PREPARED_LOCALLY'
    assert saved['submitted_at'] is None and saved['funded_at'] is None
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT settlement_id,payment_status FROM fe_express_driver_settlements').fetchall() == [('HISTORICAL','UNCHANGED')]
