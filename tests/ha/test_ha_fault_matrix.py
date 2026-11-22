"""Offline Fault-Test Matrix for AI-BS Oracle Hot Standby (AI-BS-HA-OCI-001 Section 8).

Covers:
  - HA-01 .. HA-08 (Exclusive Execution Gateway, Epoch Fencing, Recovery, Passive Enforcement)
  - OCI-01 .. OCI-08 (Paginated Inspection, Fail-Closed Auth/HTTP, Idempotent CreateJob,
                      Single ControllerLock, Restart-Safe 20m Policy, Policy/Region Checks)
  - OPS-01 .. OPS-03 (Passive Safe Recovery, Visible Write Failures, Consistent SQLite Backup/Restore)
  - pure_rsa_sha256 disposable RSA-2048 cryptographic signing & negative format validation
  - structural_dip_engine gateway & passive integration
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gc
import importlib.util
import io
import json
import logging
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_REPO_ROOT = Path(r"C:\AI-BS")
_SCRATCH = _REPO_ROOT / "scratch"
_DEPLOY = _REPO_ROOT / "deploy" / "oci_standby"

for p in (str(_SCRATCH), str(_DEPLOY)):
    if p not in sys.path:
        sys.path.insert(0, p)

import ha_execution_gateway as ha  # noqa: E402
import oci_stack_claimer as oci  # noqa: E402
import pure_rsa_sha256 as rsa_mod  # noqa: E402
import backup_and_restore as bnr  # noqa: E402


def _load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeExchange:
    """Deterministic mock exchange supporting normal acks, lost responses, partial fills, and reads."""

    def __init__(self) -> None:
        self.bids = [(Decimal("0.04140"), Decimal("500")), (Decimal("0.04130"), Decimal("1000"))]
        self.asks = [(Decimal("0.04150"), Decimal("500")), (Decimal("0.04160"), Decimal("1000"))]
        self.open_orders: dict[str, dict] = {}
        self.order_details: dict[str, dict] = {}
        self.balances = {
            "CRO": {"free": Decimal("0"), "reserved": Decimal("0"), "total": Decimal("0")},
            "USDT": {"free": Decimal("100.00"), "reserved": Decimal("0"), "total": Decimal("100.00")},
            "USD": {"free": Decimal("0"), "reserved": Decimal("0"), "total": Decimal("0")},
        }
        self.mutations: list[dict] = []
        self.drop_next_create_response = False
        self._seq = 1000

    def get_book(self, depth: int = 10):
        return self.bids[0][0], self.asks[0][0], self.bids[:depth], self.asks[:depth]

    def get_open_orders(self):
        return [dict(v) for v in self.open_orders.values()]

    def get_order_detail(self, order_id: str):
        return dict(self.order_details[str(order_id)])

    def get_balances(self):
        return {k: dict(v) for k, v in self.balances.items()}

    def create_limit_order(self, *, side: str, qty_cro: int, price: Decimal, client_oid: str):
        self._seq += 1
        oid = f"ex-{self._seq}"
        order_obj = {
            "order_id": oid,
            "client_oid": client_oid,
            "side": side,
            "quantity": str(qty_cro),
            "cumulative_quantity": "0",
            "limit_price": f"{price:.5f}",
            "price": f"{price:.5f}",
            "avg_price": "0",
            "cumulative_fee": "0",
            "fee_instrument_name": "USDT",
            "status": "ACTIVE",
            "exec_inst": ["POST_ONLY"],
            "time_in_force": "GOOD_TILL_CANCEL",
        }
        self.open_orders[oid] = dict(order_obj)
        self.order_details[oid] = dict(order_obj)
        self.mutations.append({"op": "CREATE", "order_id": oid, "client_oid": client_oid})
        if self.drop_next_create_response:
            self.drop_next_create_response = False
            raise TimeoutError("Simulated socket read timeout after exchange accepted order")
        return {"order_id": oid, "client_oid": client_oid}

    def cancel_order(self, order_id: str):
        oid = str(order_id)
        self.mutations.append({"op": "CANCEL", "order_id": oid})
        self.open_orders.pop(oid, None)
        if oid in self.order_details:
            self.order_details[oid]["status"] = "CANCELED"
        return {"order_id": oid, "status": "CANCELED"}

    def amend_order(self, *, order_id: str, qty_cro: int, price: Decimal):
        self.mutations.append({"op": "AMEND", "order_id": str(order_id)})
        return {"order_id": str(order_id), "status": "AMENDED"}

    def bulk_order(self, orders: list[dict]):
        self.mutations.append({"op": "BULK", "count": len(orders)})
        return {"ok": True}

    def emergency_action(self, op: str, params: dict):
        self.mutations.append({"op": "EMERGENCY", "action": op})
        return {"status": "ok"}


class TestHAFaultMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.clock = ha.FakeClock()
        self.db_path = self.tmp / "ha_gateway.db"
        self.store = ha.AuthorityStore(self.db_path, clock=self.clock)
        self.exchange = FakeExchange()
        self.gateway = ha.ExecutionGateway(self.store, self.exchange)
        self.fsm = ha.FailoverStateMachine(self.store, self.gateway, auto_promote_enabled=False)

    def tearDown(self) -> None:
        self.store.close()
        gc.collect()
        self.tmpdir.cleanup()

    def test_HA_01_primary_returns_with_old_epoch(self) -> None:
        st1 = self.store.acquire_or_promote("windows-primary", lease_ttl_sec=45.0, actor="boot", reason="start")
        self.assertEqual(st1["epoch"], 1)
        st2 = self.fsm.request_promotion(
            "oci-standby",
            manual_approval_actor="brett",
            read_client=self.exchange,
            risk_snapshot={"healthy": True, "kill_switch_tripped": False},
            market_data_age_sec=1.0,
        )
        self.assertGreater(st2["epoch"], st1["epoch"])
        self.assertEqual(st2["owner_id"], "oci-standby")

        before = len(self.exchange.mutations)
        with self.assertRaises(ha.StaleEpochError):
            self.gateway.submit_create_limit(
                owner_id="windows-primary",
                epoch=1,
                side="BUY",
                qty_cro=100,
                price=Decimal("0.04100"),
                client_oid="stale-primary-1",
            )
        with self.assertRaises(ha.StaleEpochError):
            self.gateway.submit_cancel(owner_id="windows-primary", epoch=1, order_id="ex-1")
        self.assertEqual(len(self.exchange.mutations), before)

        # Returning primary host starts strictly PASSIVE and cannot keep old authority
        rec = self.fsm.recover_host_passive("windows-primary")
        self.assertEqual(rec["role"], "PASSIVE")
        with self.assertRaises(ha.PassiveAuthorityError):
            self.gateway.submit_create_limit(
                owner_id="windows-primary",
                epoch=rec["epoch"],
                side="BUY",
                qty_cro=100,
                price=Decimal("0.04100"),
                client_oid="post-recover-1",
            )

    def test_HA_02_old_command_queued_during_promotion(self) -> None:
        st1 = self.store.acquire_or_promote("windows-primary", lease_ttl_sec=45.0, actor="boot", reason="start")
        qid = self.gateway.enqueue_command(
            ha.GatewayCommand(
                owner_id="windows-primary",
                epoch=st1["epoch"],
                action="CREATE",
                side="BUY",
                qty_cro=500,
                price=Decimal("0.04100"),
                client_oid="queued-old-epoch",
            )
        )
        # Promote standby -> fences epoch 1 -> draining queue rejects before dispatch!
        st2 = self.fsm.request_promotion(
            "oci-standby",
            manual_approval_actor="brett",
            read_client=self.exchange,
            risk_snapshot={"healthy": True, "kill_switch_tripped": False},
            market_data_age_sec=1.0,
        )
        self.assertGreater(st2["epoch"], 1)
        self.assertEqual(len(self.exchange.mutations), 0)
        q_rows = self.store.list_queued_commands(status="ABORTED")
        self.assertTrue(any(r["queue_id"] == qid for r in q_rows))

        # Even across restart with another stale DB-persisted queue item, expired epoch is never replayed
        self.store.enqueue_durable_command(
            ha.GatewayCommand(
                owner_id="windows-primary",
                epoch=st1["epoch"],
                action="CANCEL",
                order_id="ex-999",
            )
        )
        self.store.close()
        reopened = ha.AuthorityStore(self.db_path, clock=self.clock)
        gw2 = ha.ExecutionGateway(reopened, self.exchange)
        try:
            res = gw2.drain_queue()
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["status"], "ABORTED")
            self.assertEqual(res[0]["error_type"], "StaleEpochError")
            self.assertEqual(len(self.exchange.mutations), 0)
        finally:
            reopened.close()

    def test_HA_03_exchange_accepts_but_response_lost(self) -> None:
        st1 = self.store.acquire_or_promote("windows-primary", lease_ttl_sec=45.0, actor="boot", reason="start")
        self.exchange.drop_next_create_response = True

        with self.assertRaises(ha.UnresolvedIntentError):
            self.gateway.submit_create_limit(
                owner_id="windows-primary",
                epoch=st1["epoch"],
                side="BUY",
                qty_cro=700,
                price=Decimal("0.04100"),
                client_oid="lost-resp-1",
            )

        self.assertEqual(len(self.exchange.mutations), 1)
        self.assertEqual(len(self.store.get_unresolved_intents()), 1)
        self.assertEqual(self.store.get_unresolved_intents()[0]["status"], "UNKNOWN")

        # Subsequent dependent order blocked (no blind resubmission!)
        with self.assertRaises(ha.UnresolvedIntentError):
            self.gateway.submit_create_limit(
                owner_id="windows-primary",
                epoch=st1["epoch"],
                side="BUY",
                qty_cro=700,
                price=Decimal("0.04100"),
                client_oid="blind-retry-2",
            )
        self.assertEqual(len(self.exchange.mutations), 1)

        # Manual approval CANNOT bypass unresolved UNKNOWN intent during promotion!
        # Simulate exchange read failure during reconcile so intent stays unresolved
        broken_read = FakeExchange()
        broken_read.get_open_orders = lambda: (_ for _ in ()).throw(ConnectionError("exchange read down"))
        with self.assertRaises(ha.GateBlockedError):
            self.fsm.request_promotion(
                "oci-standby",
                manual_approval_actor="brett",
                read_client=broken_read,
                risk_snapshot={"healthy": True, "kill_switch_tripped": False},
                market_data_age_sec=1.0,
            )
        # Reconcile succeeds once exchange read recovers
        rec = self.gateway.reconcile_unresolved_intents(self.exchange)
        self.assertEqual(len(rec["resolved"]), 1)
        self.assertEqual(len(self.store.get_unresolved_intents()), 0)

    def test_HA_04_partial_fill_during_handoff(self) -> None:
        st1 = self.store.acquire_or_promote("windows-primary", lease_ttl_sec=45.0, actor="boot", reason="start")
        ack = self.gateway.submit_create_limit(
            owner_id="windows-primary",
            epoch=st1["epoch"],
            side="SELL",
            qty_cro=714,
            price=Decimal("0.04234"),
            client_oid="tp-0-handoff",
        )
        oid = ack["order_id"]

        # Simulate partial fill of 300 CRO during handoff, plus duplicate reconciliation check
        self.exchange.order_details[oid]["cumulative_quantity"] = "300"
        self.exchange.open_orders[oid]["cumulative_quantity"] = "300"
        self.exchange.order_details[oid]["avg_price"] = "0.04234"

        applied_1, acct_1 = self.store.apply_fill_idempotent(
            fill_key=f"{oid}:300",
            order_id=oid,
            client_oid="tp-0-handoff",
            side="SELL",
            order_qty=Decimal("714"),
            cum_fill_qty=Decimal("300"),
            delta_fill_qty=Decimal("300"),
            price=Decimal("0.04234"),
            fee_usdt=Decimal("0"),
            cost_basis_price=Decimal("0.04198"),
            reserve_share=Decimal("0.50"),
            epoch=st1["epoch"],
        )
        self.assertTrue(applied_1)
        self.assertEqual(acct_1["remaining_qty"], "414")
        # 300 * (0.04234 - 0.04198) = 0.108000; 50% reserve = 0.054000
        self.assertEqual(acct_1["total_realized_pnl_usdt"], "0.108000")
        self.assertEqual(acct_1["profit_reserve_usdt"], "0.054000")

        # Replay/duplicate fill reconciliation must not double-count
        applied_dup, acct_dup = self.store.apply_fill_idempotent(
            fill_key=f"{oid}:300",
            order_id=oid,
            client_oid="tp-0-handoff",
            side="SELL",
            order_qty=Decimal("714"),
            cum_fill_qty=Decimal("300"),
            delta_fill_qty=Decimal("300"),
            price=Decimal("0.04234"),
            fee_usdt=Decimal("0"),
            cost_basis_price=Decimal("0.04198"),
            reserve_share=Decimal("0.50"),
            epoch=st1["epoch"],
        )
        self.assertFalse(applied_dup)
        self.assertEqual(acct_dup["total_realized_pnl_usdt"], "0.108000")
        self.assertEqual(acct_dup["profit_reserve_usdt"], "0.054000")

        # Remaining 414 fills after standby promoted to epoch 2
        st2 = self.fsm.request_promotion(
            "oci-standby",
            manual_approval_actor="brett",
            read_client=self.exchange,
            risk_snapshot={"healthy": True, "kill_switch_tripped": False},
            market_data_age_sec=1.0,
        )
        applied_2, acct_2 = self.store.apply_fill_idempotent(
            fill_key=f"{oid}:714",
            order_id=oid,
            client_oid="tp-0-handoff",
            side="SELL",
            order_qty=Decimal("714"),
            cum_fill_qty=Decimal("714"),
            delta_fill_qty=Decimal("414"),
            price=Decimal("0.04234"),
            fee_usdt=Decimal("0"),
            cost_basis_price=Decimal("0.04198"),
            reserve_share=Decimal("0.50"),
            epoch=st2["epoch"],
        )
        self.assertTrue(applied_2)
        self.assertEqual(acct_2["remaining_qty"], "0")
        # Total = 714 * 0.00036 = 0.257040; 50% reserve = 0.128520
        self.assertEqual(acct_2["total_realized_pnl_usdt"], "0.257040")
        self.assertEqual(acct_2["profit_reserve_usdt"], "0.128520")

    def test_HA_05_gateway_restart_mid_request(self) -> None:
        st1 = self.store.acquire_or_promote("windows-primary", lease_ttl_sec=60.0, actor="boot", reason="start")
        # Simulate crash while SUBMITTING intent was persisted just before exchange response returned
        self.store.seed_intent_for_test(
            intent_id="int-midcrash01",
            client_oid="dip-crash-01",
            epoch=st1["epoch"],
            owner_id="windows-primary",
            action="CREATE",
            status="SUBMITTING",
            qty_cro=710,
            price=Decimal("0.04100"),
        )
        self.exchange.create_limit_order(side="BUY", qty_cro=710, price=Decimal("0.04100"), client_oid="dip-crash-01")
        self.store.close()

        # Restarted store + gateway from same SQLite WAL DB
        restarted_store = ha.AuthorityStore(self.db_path, clock=self.clock)
        restarted_gw = ha.ExecutionGateway(restarted_store, self.exchange)
        try:
            self.assertEqual(len(restarted_store.get_unresolved_intents()), 1)
            with self.assertRaises(ha.UnresolvedIntentError):
                restarted_gw.submit_create_limit(
                    owner_id="windows-primary",
                    epoch=st1["epoch"],
                    side="BUY",
                    qty_cro=500,
                    price=Decimal("0.04090"),
                    client_oid="new-after-crash",
                )
            rec = restarted_gw.reconcile_unresolved_intents(self.exchange)
            self.assertEqual(len(rec["resolved"]), 1)
            self.assertEqual(len(restarted_store.get_unresolved_intents()), 0)
        finally:
            restarted_store.close()

    def test_HA_06_lease_unavailable_or_clock_jump(self) -> None:
        self.store.acquire_or_promote("windows-primary", lease_ttl_sec=45.0, actor="boot", reason="start")

        # 1. Lease unavailable blocks self-promotion
        self.store.set_lease_service_available(False)
        with self.assertRaises(ha.GateBlockedError):
            self.fsm.request_promotion(
                "oci-standby",
                manual_approval_actor="brett",
                read_client=self.exchange,
                risk_snapshot={"healthy": True, "kill_switch_tripped": False},
                market_data_age_sec=1.0,
            )

        # 2. Restore lease availability, then inject +120s wall clock jump with 1s monotonic advance
        self.store.set_lease_service_available(True)
        self.clock.advance_monotonic_only(1.0)
        self.clock.jump_wall(120.0)
        with self.assertRaises(ha.GateBlockedError):
            self.fsm.request_promotion(
                "oci-standby",
                manual_approval_actor="brett",
                read_client=self.exchange,
                risk_snapshot={"healthy": True, "kill_switch_tripped": False},
                market_data_age_sec=1.0,
            )
        self.assertTrue(any(a["code"] == "CLOCK_JUMP" or a["code"] == "CLOCK_ANOMALY" for a in self.store.get_alerts()))
        self.assertNotEqual(self.store.get_state()["owner_id"], "oci-standby")

    def test_HA_07_journal_unwritable_or_replica_stale(self) -> None:
        st1 = self.store.acquire_or_promote("windows-primary", lease_ttl_sec=45.0, actor="boot", reason="start")

        # 1. Replica stale blocks unjournaled/stale mutation and degrades health
        self.store.set_replica_stale(True, lag_seconds=95.0, reason="Standby snapshot stale")
        before = len(self.exchange.mutations)
        with self.assertRaises(ha.JournalDurabilityError):
            self.gateway.submit_create_limit(
                owner_id="windows-primary",
                epoch=st1["epoch"],
                side="BUY",
                qty_cro=100,
                price=Decimal("0.04100"),
                client_oid="stale-rep-order",
            )
        self.assertEqual(len(self.exchange.mutations), before)
        health = ha.build_ha_health_payload(
            host_id="AI-BS", build_revision="test", store=self.store, clock=self.clock,
        )
        self.assertFalse(health["dimensions"]["journal_durable"])
        self.assertFalse(health["dimensions"]["application_ready"])

        # 2. Unwritable SQLite journal path (Windows-deterministic read-only URI & directory target)
        ro_store = ha.AuthorityStore(self.db_path, clock=self.clock, read_only_uri=True)
        ro_gw = ha.ExecutionGateway(ro_store, self.exchange)
        try:
            with self.assertRaises(ha.JournalDurabilityError):
                ro_gw.submit_create_limit(
                    owner_id="windows-primary",
                    epoch=st1["epoch"],
                    side="BUY",
                    qty_cro=100,
                    price=Decimal("0.04100"),
                    client_oid="ro-db-order",
                )
            self.assertEqual(len(self.exchange.mutations), before)
        finally:
            ro_store.close()

        bad_dir = self.tmp / "not_a_db_file"
        bad_dir.mkdir()
        with self.assertRaises(ha.JournalDurabilityError):
            ha.AuthorityStore(bad_dir)

    def test_HA_08_passive_host_and_engine_deny_all_mutations(self) -> None:
        passive = ha.PassiveStandbyClient(self.exchange)
        self.assertEqual(passive.get_book(depth=2)[0], Decimal("0.04140"))

        with self.assertRaises(ha.PassiveAuthorityError):
            passive.create_limit_order(side="BUY", qty_cro=100, price=Decimal("0.04100"), client_oid="p1")
        with self.assertRaises(ha.PassiveAuthorityError):
            passive.amend_order(order_id="ex-1", qty_cro=100, price=Decimal("0.04100"))
        with self.assertRaises(ha.PassiveAuthorityError):
            passive.cancel_order("ex-1")
        with self.assertRaises(ha.PassiveAuthorityError):
            passive.bulk_order([{"side": "BUY"}])
        with self.assertRaises(ha.PassiveAuthorityError):
            passive.rearm(tranche_idx=0)
        with self.assertRaises(ha.PassiveAuthorityError):
            passive.emergency_cancel_all()
        self.assertEqual(passive.denied_mutation_attempts, 6)
        self.assertEqual(len(self.exchange.mutations), 0)

        # Also test structural_dip_engine.run_cycle(..., role="passive") and gateway active path
        sde = _load_mod("structural_dip_engine_ha", _SCRATCH / "structural_dip_engine.py")
        log = logging.getLogger("test_ha_sde")
        log.handlers = [logging.NullHandler()]
        saved = self.tmp / "sde_saved"
        saved.mkdir()
        with (
            patch.object(sde, "SAVED_DATA_DIR", saved),
            patch.object(sde, "STATE_FILE", saved / "state.json"),
            patch.object(sde, "LEDGER_CSV_FILE", saved / "ledger.csv"),
            patch.object(sde, "LEDGER_DB_FILE", saved / "ledger.db"),
            patch.object(sde, "SCOUT_SIGNAL_FILE", saved / "scout.json"),
            patch.object(sde, "ALERT_FILE", saved / "alert.json"),
        ):
            sde.init_ledgers()
            st_passive = sde.load_state()
            sde.run_cycle(passive, st_passive, log, role="passive")
            self.assertEqual(st_passive["ha_role"], "PASSIVE")
            self.assertEqual(len(self.exchange.mutations), 0)

            # Now test gateway-enforced primary path places via ExecutionGateway
            epoch1 = self.store.acquire_or_promote("windows-primary", lease_ttl_sec=60.0, actor="boot", reason="test")
            st_active = sde.load_state()
            sde.run_cycle(
                self.exchange,
                st_active,
                log,
                role="primary",
                gateway=self.gateway,
                authority_epoch=epoch1["epoch"],
                owner_id="windows-primary",
            )
            self.assertEqual(st_active["ha_role"], "ACTIVE")
            self.assertGreater(len(self.exchange.mutations), 0)
            acked = [i for i in self.store.get_all_intents() if i["status"] == "ACKED"]
            self.assertEqual(len(acked), len(self.exchange.mutations))


class FakeOciTransport:
    """Deterministic HTTP router for OCI Resource Manager & Compute API fault testing."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, dict | None]] = []
        self.stack_resp = oci.OciResponse(
            status=200,
            body={
                "id": oci.STACK_ID,
                "compartmentId": "ocid1.compartment.oc1..testcomp",
                "lifecycleState": "ACTIVE",
                "variables": {
                    "compartment_ocid": "ocid1.compartment.oc1..testcomp",
                    "instance_shape": "VM.Standard.A1.Flex",
                    "instance_ocpus": "1",
                    "instance_shape_config_memory_in_gbs": "6",
                },
            },
            headers={"opc-request-id": "req-stack-1"},
            request_id="req-stack-1",
        )
        self.instance_pages: dict[str | None, oci.OciResponse] = {
            None: oci.OciResponse(status=200, body=[], headers={"opc-request-id": "req-inst-0"}, request_id="req-inst-0")
        }
        self.job_pages: dict[str | None, oci.OciResponse] = {
            None: oci.OciResponse(status=200, body=[], headers={"opc-request-id": "req-job-0"}, request_id="req-job-0")
        }
        self.job_details: dict[str, oci.OciResponse | Exception] = {}
        self.post_job_handler = None
        self.post_count = 0

    def __call__(self, method: str, host: str, path: str, headers: dict[str, str], body_bytes: bytes | None) -> oci.OciResponse:
        parsed_body = json.loads(body_bytes.decode("utf-8")) if body_bytes else None
        self.calls.append((method, host, path, parsed_body))

        if path.startswith("/20180917/stacks/"):
            return self.stack_resp
        if path.startswith("/20160918/instances"):
            page = None
            if "page=" in path:
                page = path.split("page=", 1)[1].split("&", 1)[0]
            resp = self.instance_pages[page]
            if isinstance(resp, Exception):
                raise resp
            return resp
        if path == "/20180917/jobs" and method == "POST":
            self.post_count += 1
            if self.post_job_handler is not None:
                return self.post_job_handler(parsed_body, headers)
            return oci.OciResponse(
                status=202,
                body={"id": f"ocid1.ormjob.oc1.us-chicago-1..job{self.post_count}", "lifecycleState": "ACCEPTED"},
                headers={"opc-request-id": f"req-create-{self.post_count}"},
                request_id=f"req-create-{self.post_count}",
            )
        if path.startswith("/20180917/jobs?"):
            page = None
            if "page=" in path:
                page = path.split("page=", 1)[1].split("&", 1)[0]
            return self.job_pages[page]
        if path.startswith("/20180917/jobs/") and method == "GET":
            jid = path.split("/20180917/jobs/", 1)[1]
            res = self.job_details[jid]
            if isinstance(res, Exception):
                raise res
            return res
        raise AssertionError(f"Unexpected OCI call: {method} https://{host}{path}")


class TestOciAndRsaMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.key_path = self.tmp / "disposable_rsa_pkcs8.pem"
        self.key_pkcs1_path = self.tmp / "disposable_rsa_pkcs1.pem"
        self.priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.key_path.write_bytes(
            self.priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        self.key_pkcs1_path.write_bytes(
            self.priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        self.cfg_path = self.tmp / "oci_config"
        self.cfg_path.write_text(
            f"[DEFAULT]\n"
            f"user=ocid1.user.oc1..test\n"
            f"fingerprint=aa:bb:cc:dd:ee\n"
            f"tenancy=ocid1.tenancy.oc1..test\n"
            f"region=us-chicago-1\n"
            f"key_file={self.key_path}\n\n"
            f"[WRONG_REGION]\n"
            f"user=ocid1.user.oc1..other\n"
            f"fingerprint=11:22:33\n"
            f"tenancy=ocid1.tenancy.oc1..other\n"
            f"region=us-ashburn-1\n"
            f"key_file={self.key_path}\n",
            encoding="utf-8",
        )
        self.cfg = oci.load_oci_config(self.cfg_path, profile="DEFAULT")
        self.state_file = self.tmp / "oci_state.json"
        self.status_file = self.tmp / "oci_status.json"
        self.log_file = self.tmp / "oci.log"
        self.lock_file = self.tmp / "oci.lock"
        self.clock = ha.FakeClock()
        self.policy = dict(oci.DEFAULT_APPROVED_POLICY)

    def tearDown(self) -> None:
        gc.collect()
        self.tmpdir.cleanup()

    def test_pure_rsa_sha256_disposable_keys_pkcs1_pkcs8_and_validation(self) -> None:
        msg = b"(request-target): get /20180917/jobs?stackId=test\ndate: Thu, 19 Nov 2026 18:00:00 GMT"
        for pem_p in (self.key_path, self.key_pkcs1_path):
            sig_b64 = rsa_mod.rsa_sha256_sign_b64(str(pem_p), msg)
            self.assertTrue(rsa_mod.verify_pem_signature_b64(str(pem_p), msg, sig_b64))
            # Cross-verify mathematically with independent `cryptography` library!
            import base64
            self.priv.public_key().verify(
                base64.b64decode(sig_b64),
                msg,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            self.assertFalse(rsa_mod.verify_pem_signature_b64(str(pem_p), msg + b"x", sig_b64))

        # Encrypted PEM & weak <2048-bit key must fail cleanly with ValueError (not AssertionError!)
        enc_path = self.tmp / "enc.pem"
        enc_path.write_bytes(
            self.priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(b"test-pass"),
            )
        )
        with self.assertRaises(ValueError):
            rsa_mod.load_rsa_key_components(str(enc_path))

        weak_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
        weak_path = self.tmp / "weak1024.pem"
        weak_path.write_bytes(
            weak_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        with self.assertRaises(ValueError):
            rsa_mod.load_rsa_key_components(str(weak_path))

    def test_OCI_01_paginated_empty_then_nonempty_page(self) -> None:
        tr = FakeOciTransport()
        target_vm = {
            "id": "ocid1.instance.oc1.us-chicago-1.targetvm",
            "displayName": "aibs-standby-arm64",
            "lifecycleState": "RUNNING",
            "shape": "VM.Standard.A1.Flex",
            "shapeConfig": {"ocpus": 1, "memoryInGBs": 6},
            "freeformTags": {"aibs_stack_id": oci.STACK_ID},
        }
        tr.instance_pages = {
            None: oci.OciResponse(status=200, body=[], headers={"opc-next-page": "p2"}, next_page="p2", request_id="r1"),
            "p2": oci.OciResponse(status=200, body=[], headers={"opc-next-page": "p3"}, next_page="p3", request_id="r2"),
            "p3": oci.OciResponse(status=200, body=[target_vm], headers={}, next_page=None, request_id="r3"),
        }
        st = oci.load_controller_state(self.state_file)
        outcome, _sleep = oci.run_controller_cycle(
            self.cfg, st, 1, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
        )
        self.assertEqual(outcome, "MONITOR_READY")
        self.assertEqual(st["mode"], "MONITOR")
        self.assertEqual(st["verified_instance_id"], target_vm["id"])
        self.assertEqual(tr.post_count, 0)

    def test_OCI_02_listing_errors_and_malformed_json(self) -> None:
        for bad_resp in (
            oci.OciResponse(status=401, body={"message": "NotAuthenticated"}, headers={}, request_id="r401"),
            oci.OciResponse(status=403, body={"message": "NotAuthorized"}, headers={}, request_id="r403"),
            oci.OciResponse(status=429, body={"message": "TooManyRequests"}, headers={}, request_id="r429"),
            oci.OciResponse(status=503, body={"message": "ServiceUnavailable"}, headers={}, request_id="r503"),
            oci.OciResponse(status=200, body=None, headers={}, json_valid=False, request_id="rbadjson"),
        ):
            tr = FakeOciTransport()
            tr.instance_pages = {None: bad_resp}
            st = oci.load_controller_state(self.state_file)
            outcome, _sleep = oci.run_controller_cycle(
                self.cfg, st, 1, policy=self.policy, transport=tr, clock=self.clock,
                status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
            )
            self.assertIn(outcome, ("INSPECTION_FAILED", "HALT_AUTH_ERROR"))
            self.assertEqual(tr.post_count, 0)
            saved_status = json.loads(self.status_file.read_text(encoding="utf-8"))
            self.assertFalse(saved_status["inspection_ok"])
            self.assertFalse(saved_status["target_exists"])

        # CLI `--check-only` MUST exit non-zero (1) on incomplete inspection
        proc = subprocess.run(
            [
                sys.executable,
                str(_SCRATCH / "oci_stack_claimer.py"),
                "--check-only",
                "--config", str(self.tmp / "nonexistent_oci_config"),
                "--state-file", str(self.state_file),
                "--status-file", str(self.status_file),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_OCI_03_create_job_response_lost_reconciled(self) -> None:
        tr = FakeOciTransport()
        captured_tokens: list[tuple[str, str]] = []

        def drop_once(body, hdrs):
            captured_tokens.append((body["displayName"], hdrs["opc-retry-token"]))
            raise TimeoutError("Lost response after CreateJob POST sent")

        tr.post_job_handler = drop_once
        st = oci.load_controller_state(self.state_file)
        outcome1, _ = oci.run_controller_cycle(
            self.cfg, st, 1, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
        )
        self.assertEqual(outcome1, "SUBMISSION_UNKNOWN")
        self.assertTrue(st["uncertain_creation_outcome"])
        self.assertEqual(st["pending_operation"]["state"], "SUBMISSION_UNKNOWN")
        saved_op = st["pending_operation"]["operation_id"]

        # Next cycle: job created on OCI from the lost request now appears in list_jobs!
        tr.job_pages = {
            None: oci.OciResponse(
                status=200,
                body=[{
                    "id": "ocid1.ormjob.oc1.us-chicago-1..recoveredjob",
                    "displayName": f"aibs-apply-{saved_op}",
                    "lifecycleState": "FAILED",
                    "operation": "APPLY",
                }],
                headers={},
            )
        }
        st_reloaded = oci.load_controller_state(self.state_file)
        outcome2, _ = oci.run_controller_cycle(
            self.cfg, st_reloaded, 2, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
        )
        self.assertEqual(outcome2, "RECONCILED_EXISTING_JOB")
        self.assertEqual(tr.post_count, 1)  # Never issued a fresh CreateJob!

    def test_OCI_04_partial_success_or_unmanaged_or_lost_vm(self) -> None:
        # 1. Active/nonterminal job blocks new APPLY
        tr = FakeOciTransport()
        tr.job_pages = {
            None: oci.OciResponse(
                status=200,
                body=[{"id": "ocid1.ormjob.oc1..active1", "lifecycleState": "IN_PROGRESS", "operation": "APPLY"}],
                headers={},
            )
        }
        tr.job_details["ocid1.ormjob.oc1..active1"] = oci.OciResponse(
            status=200, body={"id": "ocid1.ormjob.oc1..active1", "lifecycleState": "IN_PROGRESS"}, headers={},
        )
        st = oci.load_controller_state(self.state_file)
        outcome_active, _ = oci.run_controller_cycle(
            self.cfg, st, 1, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
            max_job_polls=1, job_poll_sleep_sec=0.0,
        )
        self.assertEqual(outcome_active, "JOB_STATE_UNKNOWN")
        self.assertEqual(tr.post_count, 0)

        # 2. Unmanaged VM blocks adoption/reprovisioning
        tr2 = FakeOciTransport()
        tr2.instance_pages = {
            None: oci.OciResponse(
                status=200,
                body=[{
                    "id": "ocid1.instance.oc1..manualvm",
                    "displayName": "manual-console-vm",
                    "lifecycleState": "RUNNING",
                    "shape": "VM.Standard.A1.Flex",
                    "shapeConfig": {"ocpus": 1, "memoryInGBs": 6},
                }],
                headers={},
            )
        }
        st2 = oci.load_controller_state(self.tmp / "s2.json")
        out_unmanaged, _ = oci.run_controller_cycle(
            self.cfg, st2, 1, policy=self.policy, transport=tr2, clock=self.clock,
            status_file=self.status_file, state_file=self.tmp / "s2.json", log_file=self.log_file,
        )
        self.assertEqual(out_unmanaged, "MANUAL_REVIEW_UNMANAGED_VM")
        self.assertEqual(tr2.post_count, 0)

        # 3. Lost VM after prior success halts for outage recovery
        tr3 = FakeOciTransport()
        st3 = oci.load_controller_state(self.tmp / "s3.json")
        st3["verified_instance_id"] = "ocid1.instance.oc1.us-chicago-1.prevok"
        out_lost, _ = oci.run_controller_cycle(
            self.cfg, st3, 1, policy=self.policy, transport=tr3, clock=self.clock,
            status_file=self.status_file, state_file=self.tmp / "s3.json", log_file=self.log_file,
        )
        self.assertEqual(out_lost, "OUTAGE_RECOVERY_REQUIRED")
        self.assertEqual(tr3.post_count, 0)

    def test_OCI_05_two_controller_processes_single_owner(self) -> None:
        lock1 = oci.ControllerLock(self.lock_file)
        lock2 = oci.ControllerLock(self.lock_file)
        tr = FakeOciTransport()
        self.assertTrue(lock1.acquire())
        try:
            st = oci.load_controller_state(self.state_file)
            outcome, _ = oci.run_controller_cycle(
                self.cfg, st, 1, policy=self.policy, transport=tr, clock=self.clock,
                status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
                lock=lock2,
            )
            self.assertEqual(outcome, "LOCK_HELD_BY_ANOTHER_CONTROLLER")
            self.assertEqual(tr.post_count, 0)
        finally:
            lock1.release()
        self.assertTrue(lock2.acquire())
        lock2.release()

    def test_OCI_06_restart_preserves_20min_retry_schedule(self) -> None:
        tr = FakeOciTransport()
        tr.post_job_handler = lambda _b, _h: oci.OciResponse(
            status=202,
            body={"id": "ocid1.ormjob.oc1.us-chicago-1..capfail", "lifecycleState": "ACCEPTED"},
            headers={"opc-request-id": "req-cap-1"},
        )
        tr.job_details["ocid1.ormjob.oc1.us-chicago-1..capfail"] = oci.OciResponse(
            status=200,
            body={
                "id": "ocid1.ormjob.oc1.us-chicago-1..capfail",
                "lifecycleState": "FAILED",
                "failureCause": "Out of host capacity.",
            },
            headers={},
        )
        st = oci.load_controller_state(self.state_file)
        out1, sleep1 = oci.run_controller_cycle(
            self.cfg, st, 1, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
            max_job_polls=2, job_poll_sleep_sec=0.0,
        )
        self.assertEqual(out1, "CAPACITY_SATURATED")
        self.assertGreaterEqual(sleep1, 1200)
        self.assertEqual(tr.post_count, 1)

        # Simulate daemon restart 300s later -> 900s still remaining, MUST enforce wait with 0 new POSTs!
        self.clock.advance(300.0)
        st_restarted = oci.load_controller_state(self.state_file)
        out2, sleep2 = oci.run_controller_cycle(
            self.cfg, st_restarted, 1, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
            max_job_polls=2, job_poll_sleep_sec=0.0,
        )
        self.assertEqual(out2, "COOLDOWN_ENFORCED")
        self.assertEqual(sleep2, 900)
        self.assertEqual(tr.post_count, 1)

        # Backward clock jump triggers protective delay instead of burst
        self.clock.jump_wall(-600.0)
        out_jump, sleep_jump = oci.run_controller_cycle(
            self.cfg, st_restarted, 2, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
            max_job_polls=2, job_poll_sleep_sec=0.0,
        )
        self.assertEqual(out_jump, "CLOCK_JUMP_DELAY")
        self.assertGreaterEqual(sleep_jump, 1200)
        self.assertEqual(tr.post_count, 1)

        # After jumping forward back + advancing past 1200s window, fresh attempt is eligible
        self.clock.jump_wall(600.0)
        self.clock.advance(1300.0)
        tr.post_job_handler = lambda _b, _h: oci.OciResponse(
            status=202,
            body={"id": "ocid1.ormjob.oc1.us-chicago-1..capretry", "lifecycleState": "ACCEPTED"},
            headers={},
        )
        tr.job_details["ocid1.ormjob.oc1.us-chicago-1..capretry"] = oci.OciResponse(
            status=200,
            body={"id": "ocid1.ormjob.oc1.us-chicago-1..capretry", "lifecycleState": "FAILED", "failureCause": "Out of capacity"},
            headers={},
        )
        out3, _ = oci.run_controller_cycle(
            self.cfg, st_restarted, 3, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
            max_job_polls=2, job_poll_sleep_sec=0.0,
        )
        self.assertEqual(out3, "CAPACITY_SATURATED")
        self.assertEqual(tr.post_count, 2)

    def test_OCI_07_unknown_job_state_or_failed_get_job(self) -> None:
        tr = FakeOciTransport()
        tr.post_job_handler = lambda _b, _h: oci.OciResponse(
            status=202, body={"id": "ocid1.ormjob.oc1.us-chicago-1..unkjob"}, headers={},
        )
        tr.job_details["ocid1.ormjob.oc1.us-chicago-1..unkjob"] = oci.OciResponse(
            status=500, body={"message": "InternalError during GetJob"}, headers={},
        )
        st = oci.load_controller_state(self.state_file)
        out1, _ = oci.run_controller_cycle(
            self.cfg, st, 1, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
            max_job_polls=1, job_poll_sleep_sec=0.0,
        )
        self.assertEqual(out1, "JOB_STATE_UNKNOWN")
        self.assertEqual(st["active_job_id"], "ocid1.ormjob.oc1.us-chicago-1..unkjob")

        # Subsequent cycle must STILL refuse a new POST while GetJob returns missing lifecycleState
        tr.job_details["ocid1.ormjob.oc1.us-chicago-1..unkjob"] = oci.OciResponse(
            status=200, body={"id": "ocid1.ormjob.oc1.us-chicago-1..unkjob"}, headers={},
        )
        out2, _ = oci.run_controller_cycle(
            self.cfg, st, 2, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
            max_job_polls=1, job_poll_sleep_sec=0.0,
        )
        self.assertEqual(out2, "JOB_STATE_UNKNOWN")
        self.assertEqual(tr.post_count, 1)

    def test_OCI_08_wrong_profile_region_or_plan_cost_blocked(self) -> None:
        with self.assertRaises(ValueError):
            oci.load_oci_config(self.cfg_path, profile="NONEXISTENT_PROFILE")

        wrong_region_cfg = oci.load_oci_config(self.cfg_path, profile="WRONG_REGION")
        tr = FakeOciTransport()
        st = oci.load_controller_state(self.state_file)
        out_reg, _ = oci.run_controller_cycle(
            wrong_region_cfg, st, 1, policy=self.policy, transport=tr, clock=self.clock,
            status_file=self.status_file, state_file=self.state_file, log_file=self.log_file,
        )
        self.assertEqual(out_reg, "HALT_CONFIG_MISMATCH")
        self.assertEqual(tr.post_count, 0)

        # Oversized paid instance / shape variable in stack blocks APPLY
        tr_big = FakeOciTransport()
        tr_big.stack_resp = oci.OciResponse(
            status=200,
            body={
                "id": oci.STACK_ID,
                "lifecycleState": "ACTIVE",
                "variables": {
                    "compartment_ocid": "ocid1.compartment.oc1..testcomp",
                    "instance_shape": "VM.Standard.E4.Flex",
                    "instance_ocpus": "8",
                },
            },
            headers={},
        )
        out_cost, _ = oci.run_controller_cycle(
            self.cfg, oci.load_controller_state(self.tmp / "s_cost.json"), 1, policy=self.policy,
            transport=tr_big, clock=self.clock, status_file=self.status_file,
            state_file=self.tmp / "s_cost.json", log_file=self.log_file,
        )
        self.assertIn(out_cost, ("HALT_CONFIG_MISMATCH", "HALT_COST_POLICY"))
        self.assertEqual(tr_big.post_count, 0)


class TestOperationalResilienceMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.sup = _load_mod("aibs_24x7_supervisor_ops", _SCRATCH / "aibs_24x7_supervisor.py")

    def tearDown(self) -> None:
        gc.collect()
        self.tmpdir.cleanup()

    def test_OPS_01_primary_reboot_safe_passive_recovery(self) -> None:
        # Completed/halted OCI state prevents supervisor crash-relaunch loop
        oci_state_p = self.tmp / "oci_controller_state.json"
        for mode_val in ("MONITOR", "HALT_COST_POLICY", "OUTAGE_RECOVERY_REQUIRED", "MANUAL_REVIEW"):
            oci_state_p.write_text(json.dumps({"mode": mode_val}), encoding="utf-8")
            allow, _reason = self.sup.should_launch_oci_claimer(oci_state_p)
            self.assertFalse(allow, f"Expected False for mode={mode_val}")

        # Safe recovery mode launches structural_dip_engine in --role passive (no stale live role!)
        spawned_cmds: list[list[str]] = []

        def fake_spawn(args, cwd, log, label, extra_env=None):
            spawned_cmds.append(list(args))
            return 99999

        sup_status = self.tmp / "master_status.json"
        log = logging.getLogger("test_ops01")
        log.handlers = [logging.NullHandler()]
        with (
            patch.object(self.sup, "get_running_command_lines", return_value=[]),
            patch.object(self.sup, "is_port_open", return_value=False),
            patch.object(self.sup, "spawn_background", side_effect=fake_spawn),
        ):
            summary = self.sup.supervise_once(
                log, {}, safe_recovery_mode=True, status_file=sup_status, oci_state_file=oci_state_p,
            )
        self.assertTrue(summary["safe_recovery_mode"])
        trader_cmds = [c for c in spawned_cmds if any("structural_dip_engine.py" in a for a in c)]
        self.assertEqual(len(trader_cmds), 1)
        self.assertIn("--role", trader_cmds[0])
        self.assertIn("passive", trader_cmds[0])
        oci_cmds = [c for c in spawned_cmds if any("oci_stack_claimer.py" in a for a in c)]
        self.assertEqual(len(oci_cmds), 0)

    def test_OPS_02_status_or_alert_write_failure_visible(self) -> None:
        # 1. Supervisor status target is an existing directory -> status_write_ok=False (never false healthy!)
        bad_dir = self.tmp / "dir_not_file"
        bad_dir.mkdir()
        log = logging.getLogger("test_ops02")
        log.handlers = [logging.NullHandler()]
        with (
            patch.object(self.sup, "get_running_command_lines", return_value=[(100, "python.exe", "structural_dip_engine.py")]),
            patch.object(self.sup, "is_port_open", return_value=True),
            patch.object(self.sup, "spawn_background", return_value=11111),
        ):
            summary = self.sup.supervise_once(log, {}, status_file=bad_dir, oci_state_file=self.tmp / "missing.json")
        self.assertFalse(summary["status_write_ok"])
        self.assertIn("status_write_error", summary)

        # 2. structural_dip_engine save_state & send_alert fail visibly
        sde = _load_mod("structural_dip_engine_ops02", _SCRATCH / "structural_dip_engine.py")
        with (
            patch.object(sde, "STATE_FILE", bad_dir),
            patch.object(sde, "ALERT_FILE", bad_dir),
        ):
            st = sde.default_state()
            ok_save = sde.save_state(st, strict_io=False)
            self.assertFalse(ok_save)
            self.assertFalse(st["status_write_ok"])
            self.assertTrue(any(a["code"] == "STATUS_WRITE_FAILED" for a in st["alerts"]))
            ok_alert = sde.send_alert("test failure", log, strict_io=False)
            self.assertFalse(ok_alert)

        # 3. agent4_risk_watchdog marks CRITICAL & status_write_ok=False when status path is directory
        wd = _load_mod("agent4_risk_watchdog_ops02", _SCRATCH / "agent4_risk_watchdog.py")
        ex = FakeExchange()
        with (
            patch.object(wd, "OUTPUT_STATUS_PATH", bad_dir),
            patch.object(wd, "SCOUT_SIGNAL_PATH", self.tmp / "missing_scout.json"),
            patch.object(wd, "check_trader_telemetry", return_value={"status": "LIVE_ACTIVE", "last_tick_utc": datetime.now(timezone.utc).isoformat()}),
        ):
            w_res = wd.run_watchdog_cycle(ex, {}, log)
        self.assertFalse(w_res["status_write_ok"])
        self.assertEqual(w_res["watchdog_health"], "CRITICAL")

        # 4. oci_stack_claimer raises AuditWriteError when atomic JSON replace fails
        with self.assertRaises(oci.AuditWriteError):
            oci.save_controller_state({"mode": "INSPECT"}, state_file=bad_dir)

    def test_OPS_03_backup_restore_disposable_env_stays_passive(self) -> None:
        db_src = self.tmp / "live_authority.db"
        clock = ha.FakeClock()
        store = ha.AuthorityStore(db_src, clock=clock)
        try:
            st1 = store.acquire_or_promote("windows-primary", lease_ttl_sec=60.0, actor="ops", reason="baseline")
            store.apply_fill_idempotent(
                fill_key="ord1:100",
                order_id="ord1",
                client_oid="tp-1",
                side="SELL",
                order_qty=Decimal("714"),
                cum_fill_qty=Decimal("100"),
                delta_fill_qty=Decimal("100"),
                price=Decimal("0.04234"),
                fee_usdt=Decimal("0"),
                cost_basis_price=Decimal("0.04198"),
                reserve_share=Decimal("0.50"),
                epoch=st1["epoch"],
            )
            store.seed_intent_for_test(
                intent_id="int-bak-1",
                client_oid="c-bak-1",
                epoch=st1["epoch"],
                owner_id="windows-primary",
                action="CREATE",
                status="ACKED",
                exchange_order_id="ord1",
            )
        finally:
            store.close()

        backup_dir = self.tmp / "backups"
        restore_dir = self.tmp / "disposable_restore"
        t0 = time.perf_counter()
        bak_info = bnr.perform_backup(db_src, backup_dir)
        res_info = bnr.verify_restore_in_dir(
            Path(bak_info["backup_path"]),
            restore_dir,
            expected_sha256=str(bak_info["sha256"]),
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(res_info["integrity"].lower(), "ok")
        self.assertTrue(res_info["sha256_verified"])
        self.assertEqual(res_info["role"], "PASSIVE")
        self.assertIsNone(res_info["owner_id"])
        self.assertTrue(res_info["auto_live_disabled"])
        self.assertEqual(res_info["applied_fills_count"], 1)
        self.assertEqual(res_info["execution_intents_count"], 1)
        self.assertLess(elapsed_ms, 5000.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
