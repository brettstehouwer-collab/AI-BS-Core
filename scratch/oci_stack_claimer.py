"""Fail-Closed OCI Resource Manager Provisioning Controller (AI-BS-HA-OCI-001 Section 6).

Enforces every Section 6 requirement:
  1. Single Authoritative Provisioning Authority: Oracle Resource Manager APPLY only
     (zero direct LaunchInstance calls).
  2. Single Profile Selection & Immutable Cycle Config Snapshot (never merges profiles;
     validates region consistency across config, stack OCID, and approved policy).
  3. Exclusive Single-Instance Host ControllerLock (two concurrent controllers yield one owner).
  4. Complete Pagination (`opc-next-page` followed even across empty `[]` pages) +
     fail-closed on non-200 HTTP status, malformed JSON, or transport errors.
  5. Durable Pre-Submission Operation Identity (`pending_operation` with `deployment_id`,
     `stack_id`, `plan_hash`, `request_body_hash`, `operation_id`, `opc_retry_token`,
     `created_utc`) & `SUBMISSION_UNKNOWN` reconciliation before any retry.
  6. Unmanaged VM detection (`MANUAL_REVIEW_UNMANAGED_VM`), lost-VM outage halt
     (`OUTAGE_RECOVERY_REQUIRED`), and unknown/active job blocking (`JOB_STATE_UNKNOWN`).
  7. Restart-safe 20-minute capacity cadence (`POLL_INTERVAL_SECONDS = 1200`),
     persisted `next_attempt_not_before_utc`, backward clock-jump guard, and explicit
     failure cause classification (capacity vs 429 vs auth vs quota/config vs transport).
  8. Atomic status/state writes raising `AuditWriteError` visibly on failure, strict
     TLS verification, zero secrets in logs, and non-zero `--check-only` exit on errors.
"""
from __future__ import annotations

import argparse
import base64
import configparser
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import formatdate
import hashlib
import json
import os
from pathlib import Path
import ssl
import sys
import time
from typing import Any, Callable
import urllib.error
import urllib.parse
import urllib.request
import uuid

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pure_rsa_sha256 import rsa_sha256_sign_b64


STACK_ID = "ocid1.ormstack.oc1.us-chicago-1.amaaaaaacuqpksyalu7rlzfn6tci6ml3fxwetdykbjdpifi5sir44tztpyrq"
CONFIG_PATH = r"C:\Users\Administrator\.oci\config"
DEFAULT_POLICY_PATH = Path(r"C:\AI-BS\deploy\oci_standby\oci_plan_policy.json")
SAVED_DATA_DIR = Path(r"C:\AI-BS\saved_data")
LOG_FILE = SAVED_DATA_DIR / "oci_claimer.log"
STATUS_FILE = SAVED_DATA_DIR / "oci_claimer_status.json"
CONTROLLER_STATE_FILE = SAVED_DATA_DIR / "oci_controller_state.json"
LOCK_FILE = SAVED_DATA_DIR / "oci_controller.lock"

POLL_INTERVAL_SECONDS = 1200  # 20 minutes minimum wait after completed failed capacity attempt
MAX_BACKOFF_SECONDS = 3600    # 60 minutes max backoff on HTTP 429
ALLOWED_FREE_SHAPE = "VM.Standard.A1.Flex"
MAX_FREE_OCPUS = 2
MAX_FREE_MEMORY_GB = 12
REQUIRED_CONFIG_KEYS = ("user", "fingerprint", "tenancy", "region", "key_file")

DEFAULT_APPROVED_POLICY: dict[str, Any] = {
    "region": "us-chicago-1",
    "allowed_shape": ALLOWED_FREE_SHAPE,
    "max_ocpus": 1,
    "max_memory_gb": 6,
    "max_boot_volume_gb": 50,
    "max_instances": 1,
    "paid_spend_authorized": False,
    "expected_plan_hash": None,
}


class AuditWriteError(RuntimeError):
    """Raised when atomic state, status, or audit log persistence fails (OPS-02)."""


@dataclass(frozen=True)
class OciConfigSnapshot:
    """Immutable validated OCI profile snapshot used for a single decision cycle."""

    profile: str
    user: str
    fingerprint: str
    tenancy: str
    region: str
    key_file: str
    config_path: str


@dataclass(frozen=True)
class OciResponse:
    """Normalized OCI REST HTTP response preserving status, headers, and correlation IDs."""

    status: int
    body: Any
    headers: dict[str, str]
    request_id: str | None = None
    next_page: str | None = None
    retry_after: str | None = None
    raw_error: str | None = None
    json_valid: bool = True


TransportFn = Callable[
    [str, str, str, dict[str, str], bytes | None],
    OciResponse,
]


class SystemOciClock:
    def utc_now(self) -> datetime:
        return datetime.now(timezone.utc)


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        s = ts.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    try:
        if path.exists() and path.is_dir():
            raise IsADirectoryError(f"Target path is a directory: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, indent=2, sort_keys=True))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception as exc:
        raise AuditWriteError(f"Failed atomic JSON write to {path}: {exc}") from exc


def write_log(msg: str, log_file: Path = LOG_FILE, *, raise_on_error: bool = True) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        if log_file.exists() and log_file.is_dir():
            raise IsADirectoryError(f"Log file path is a directory: {log_file}")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as exc:
        print(f"[{ts}] [AUDIT_LOG_WRITE_ERROR] {exc}", file=sys.stderr, flush=True)
        if raise_on_error:
            raise AuditWriteError(f"Failed writing audit log {log_file}: {exc}") from exc


class ControllerLock:
    """Exclusive single-instance OS file lock preventing concurrent mutation owners (OCI-05)."""

    def __init__(self, lock_path: str | Path = LOCK_FILE) -> None:
        self.lock_path = Path(lock_path)
        self._fh: Any = None
        self._locked = False

    def acquire(self) -> bool:
        if self._locked:
            return True
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.lock_path, "a+b")
        try:
            fh.seek(0)
            if os.name == "nt":
                import msvcrt

                # Ensure at least 1 byte exists for Windows byte-range lock
                if fh.seek(0, os.SEEK_END) == 0:
                    fh.write(b"0")
                    fh.flush()
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._fh = fh
            self._locked = True
            return True
        except OSError:
            try:
                fh.close()
            except OSError:
                pass
            return False

    def release(self) -> None:
        if self._fh is not None:
            try:
                self._fh.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None
        self._locked = False

    def __enter__(self) -> ControllerLock:
        if not self.acquire():
            raise RuntimeError(f"Lock already held: {self.lock_path}")
        return self

    def __exit__(self, *_args: Any) -> None:
        self.release()


def load_oci_config(
    config_path: str | Path = CONFIG_PATH,
    profile: str | None = None,
) -> OciConfigSnapshot:
    """Parse `~/.oci/config` selecting ONE explicit profile without merging other profiles."""
    cpath = Path(config_path)
    if not cpath.is_file():
        raise FileNotFoundError(f"OCI config file not found: {cpath}")

    eff_profile = (profile or os.environ.get("OCI_CLI_PROFILE") or "DEFAULT").strip()
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(str(cpath), encoding="utf-8")

    section: dict[str, str]
    if eff_profile == "DEFAULT":
        section = dict(cp.defaults())
        if not section:
            raise ValueError(f"Profile [DEFAULT] missing or empty in {cpath}")
    else:
        if not cp.has_section(eff_profile):
            raise ValueError(f"Profile [{eff_profile}] not found in {cpath}")
        # Read strictly keys explicitly belonging to this section when validating non-DEFAULT profiles
        raw_items: dict[str, str] = {}
        current_sec: str | None = None
        for raw_line in cpath.read_text(encoding="utf-8").splitlines():
            s = raw_line.strip()
            if not s or s.startswith("#") or s.startswith(";"):
                continue
            if s.startswith("[") and s.endswith("]"):
                current_sec = s[1:-1].strip()
                continue
            if current_sec == eff_profile and "=" in s:
                k, v = s.split("=", 1)
                raw_items[k.strip()] = v.strip()
        section = raw_items

    missing = [k for k in REQUIRED_CONFIG_KEYS if not section.get(k, "").strip()]
    if missing:
        raise ValueError(f"OCI profile [{eff_profile}] missing required keys: {missing}")

    key_file = section["key_file"].strip()
    if not Path(key_file).is_file():
        raise FileNotFoundError(f"OCI private key_file does not exist: {key_file}")

    return OciConfigSnapshot(
        profile=eff_profile,
        user=section["user"].strip(),
        fingerprint=section["fingerprint"].strip(),
        tenancy=section["tenancy"].strip(),
        region=section["region"].strip(),
        key_file=key_file,
        config_path=str(cpath),
    )


def load_approved_policy(policy_path: Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    policy = dict(DEFAULT_APPROVED_POLICY)
    if policy_path.is_file():
        loaded = json.loads(policy_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            policy.update(loaded)
    return policy


def extract_stack_region(stack_id: str) -> str:
    parts = stack_id.split(".")
    if len(parts) < 4 or not parts[3].strip():
        raise ValueError(f"Cannot extract OCI region from stack OCID: {stack_id}")
    return parts[3].strip()


def validate_environment_policy(
    cfg: OciConfigSnapshot,
    stack_id: str,
    policy: dict[str, Any],
    stack_obj: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Verify profile region, stack region, compartment, shape, and reviewed plan limits (OCI-08)."""
    stack_region = extract_stack_region(stack_id)
    if cfg.region != stack_region:
        return False, f"Region mismatch: config profile [{cfg.profile}] uses '{cfg.region}', stack uses '{stack_region}'"
    policy_region = str(policy.get("region") or stack_region)
    if cfg.region != policy_region:
        return False, f"Region mismatch: config uses '{cfg.region}', policy requires '{policy_region}'"

    max_ocpus = int(policy.get("max_ocpus", 1))
    max_mem = int(policy.get("max_memory_gb", 6))
    allowed_shape = str(policy.get("allowed_shape") or ALLOWED_FREE_SHAPE)
    if max_ocpus > MAX_FREE_OCPUS or max_mem > MAX_FREE_MEMORY_GB or allowed_shape != ALLOWED_FREE_SHAPE:
        return False, (
            f"Policy exceeds Always-Free allowlist: shape={allowed_shape} ocpus={max_ocpus} mem={max_mem}GB"
        )

    if stack_obj is not None:
        exp_comp = policy.get("expected_compartment_id")
        vars_map = stack_obj.get("variables") or {}
        actual_comp = str(vars_map.get("compartment_ocid") or stack_obj.get("compartmentId") or "")
        if exp_comp and actual_comp != str(exp_comp):
            return False, f"Compartment mismatch: expected '{exp_comp}', stack specifies '{actual_comp}'"

        req_shape = vars_map.get("instance_shape") or vars_map.get("shape")
        if req_shape and str(req_shape) != allowed_shape:
            return False, f"Disapproved stack shape '{req_shape}' (allowed: '{allowed_shape}')"

        for key_name, limit_val in (
            ("instance_ocpus", max_ocpus),
            ("ocpus", max_ocpus),
            ("instance_shape_config_memory_in_gbs", max_mem),
            ("memory_in_gbs", max_mem),
        ):
            if key_name in vars_map:
                try:
                    num = float(vars_map[key_name])
                    if num > float(limit_val):
                        return False, f"Stack variable {key_name}={num} exceeds approved limit {limit_val}"
                except Exception:
                    return False, f"Invalid numeric stack variable {key_name}={vars_map[key_name]!r}"

        if policy.get("expected_plan_hash") and stack_obj.get("planHash"):
            if str(stack_obj.get("planHash")) != str(policy["expected_plan_hash"]):
                return False, (
                    f"Plan hash mismatch: stack planHash={stack_obj.get('planHash')} "
                    f"expected={policy['expected_plan_hash']}"
                )

    return True, "OK"


def load_controller_state(state_file: Path = CONTROLLER_STATE_FILE) -> dict[str, Any]:
    default = {
        "schema": "aibs.oci_controller.v2",
        "spec": "AI-BS-HA-OCI-001",
        "mode": "INSPECT",
        "target_compartment_id": None,
        "active_job_id": None,
        "pending_operation": None,
        "uncertain_creation_outcome": False,
        "verified_instance_id": None,
        "next_attempt_not_before_utc": None,
        "last_clock_utc": None,
        "consecutive_429s": 0,
        "last_failure_class": None,
        "last_transition_utc": None,
    }
    if state_file.exists():
        if state_file.is_dir():
            raise AuditWriteError(f"Controller state path is a directory: {state_file}")
        loaded = json.loads(state_file.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            default.update(loaded)
    return default


def save_controller_state(
    state: dict[str, Any],
    *,
    state_file: Path = CONTROLLER_STATE_FILE,
    clock: Any | None = None,
) -> None:
    clk = clock or SystemOciClock()
    now_iso = clk.utc_now().isoformat()
    state["last_transition_utc"] = now_iso
    state["last_clock_utc"] = now_iso
    _atomic_write_json(state_file, state)


def _real_https_transport(
    method: str,
    host: str,
    path: str,
    headers: dict[str, str],
    body_bytes: bytes | None,
) -> OciResponse:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        f"https://{host}{path}",
        data=body_bytes,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            json_valid = True
            if raw:
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = None
                    json_valid = False
            else:
                parsed = {}
            return OciResponse(
                status=int(resp.status),
                body=parsed,
                headers=resp_headers,
                request_id=resp_headers.get("opc-request-id"),
                next_page=resp_headers.get("opc-next-page"),
                retry_after=resp_headers.get("retry-after"),
                json_valid=json_valid,
            )
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        resp_headers = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
        json_valid = True
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"message": raw}
            json_valid = False
        return OciResponse(
            status=int(e.code),
            body=parsed,
            headers=resp_headers,
            request_id=resp_headers.get("opc-request-id"),
            next_page=resp_headers.get("opc-next-page"),
            retry_after=resp_headers.get("retry-after"),
            raw_error=raw[:400],
            json_valid=json_valid,
        )


def oci_request(
    cfg: OciConfigSnapshot,
    method: str,
    host: str,
    path: str,
    body_obj: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
    *,
    transport: TransportFn | None = None,
) -> OciResponse:
    """Sign and send an OCI REST request, preserving full response status & headers."""
    key_id = f"{cfg.tenancy}/{cfg.user}/{cfg.fingerprint}"
    date_str = formatdate(usegmt=True)
    headers_to_sign = ["(request-target)", "date", "host"]
    signing_lines = [
        f"(request-target): {method.lower()} {path}",
        f"date: {date_str}",
        f"host: {host}",
    ]
    req_headers: dict[str, str] = {
        "Date": date_str,
        "Host": host,
        "Accept": "application/json",
    }
    if extra_headers:
        for hk, hv in extra_headers.items():
            req_headers[hk] = hv

    data_bytes: bytes | None = None
    if body_obj is not None:
        data_bytes = json.dumps(body_obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
        sha256_b64 = base64.b64encode(hashlib.sha256(data_bytes).digest()).decode("ascii")
        headers_to_sign += ["x-content-sha256", "content-type", "content-length"]
        signing_lines += [
            f"x-content-sha256: {sha256_b64}",
            "content-type: application/json",
            f"content-length: {len(data_bytes)}",
        ]
        req_headers["x-content-sha256"] = sha256_b64
        req_headers["Content-Type"] = "application/json"
        req_headers["Content-Length"] = str(len(data_bytes))

    if transport is None:
        signing_str = "\n".join(signing_lines).encode("utf-8")
        sig_b64 = rsa_sha256_sign_b64(cfg.key_file, signing_str)
        req_headers["Authorization"] = (
            f'Signature version="1",keyId="{key_id}",algorithm="rsa-sha256",'
            f'headers="{" ".join(headers_to_sign)}",signature="{sig_b64}"'
        )
        return _real_https_transport(method, host, path, req_headers, data_bytes)

    return transport(method, host, path, req_headers, data_bytes)


def oci_list_paginated(
    cfg: OciConfigSnapshot,
    host: str,
    base_path: str,
    *,
    max_pages: int = 100,
    transport: TransportFn | None = None,
) -> tuple[bool, int, list[dict[str, Any]], list[str | None], str | None]:
    """Read EVERY page following `opc-next-page` (including empty pages) and fail closed on errors."""
    items: list[dict[str, Any]] = []
    request_ids: list[str | None] = []
    next_page: str | None = None
    last_status = 0

    for _page_idx in range(max_pages):
        sep = "&" if "?" in base_path else "?"
        path = f"{base_path}{sep}page={urllib.parse.quote(next_page)}" if next_page else base_path
        try:
            resp = oci_request(cfg, "GET", host, path, transport=transport)
        except Exception as exc:
            return False, 0, [], request_ids, f"Transport error during list ({exc})"

        last_status = resp.status
        request_ids.append(resp.request_id)
        if resp.status != 200 or not resp.json_valid or not isinstance(resp.body, list):
            return (
                False,
                resp.status,
                [],
                request_ids,
                f"List failed status={resp.status} json_valid={resp.json_valid} type={type(resp.body).__name__}",
            )
        items.extend(x for x in resp.body if isinstance(x, dict))
        next_page = resp.next_page or resp.headers.get("opc-next-page")
        if not next_page:
            return True, last_status, items, request_ids, None

    return False, last_status, [], request_ids, f"Exceeded max_pages={max_pages} with remaining opc-next-page"


def classify_failure(http_code: int | None, body: Any = None, job_log_text: str = "") -> str:
    """Explicitly distinguish capacity, rate limit, auth, quota/config, transport, and unknown failures."""
    if http_code is None or http_code == 0:
        return "TRANSPORT_ERROR"
    if http_code == 429:
        return "RATE_LIMITED"
    if http_code in (401, 403):
        return "AUTH_ERROR"
    if http_code in (400, 404, 409):
        return "QUOTA_OR_CONFIG_ERROR"

    combined = f"{json.dumps(body, default=str) if body is not None else ''} {job_log_text}".lower()
    if "out of host capacity" in combined or "out of capacity" in combined or "capacity" in combined:
        return "CAPACITY_SATURATED"
    if "limitexceeded" in combined or "quota" in combined or "invalidparameter" in combined:
        return "QUOTA_OR_CONFIG_ERROR"
    if "notauthorized" in combined or "authentication" in combined:
        return "AUTH_ERROR"
    if http_code >= 500:
        return "UNKNOWN_FAILURE"
    return "UNKNOWN_FAILURE"


def _is_instance_managed_by_stack(inst: dict[str, Any], stack_id: str, state: dict[str, Any]) -> bool:
    if state.get("verified_instance_id") and str(inst.get("id")) == str(state["verified_instance_id"]):
        return True
    free_tags = inst.get("freeformTags") or {}
    def_tags = inst.get("definedTags") or {}
    if free_tags.get("managed_by") == "unmanaged":
        return False
    tag_dump = json.dumps({"f": free_tags, "d": def_tags})
    if stack_id in tag_dump:
        return True
    # Only consider ORM-created instances tagged by OCI Resource Manager unless explicitly unassociated
    orm_tag = free_tags.get("orm_stack_id") or free_tags.get("aibs_stack_id")
    if orm_tag is not None:
        return str(orm_tag) == stack_id
    # Check Oracle-Tags or display name prefix when no conflicting stack tag exists
    if "Oracle-Tags" in def_tags or free_tags.get("role") == "aibs-standby":
        return True
    return str(inst.get("displayName") or "").startswith("aibs-")


def inspect_managed_environment(
    cfg: OciConfigSnapshot,
    controller_state: dict[str, Any],
    *,
    stack_id: str = STACK_ID,
    policy: dict[str, Any] | None = None,
    transport: TransportFn | None = None,
    status_file: Path = STATUS_FILE,
    clock: Any | None = None,
) -> dict[str, Any]:
    """Fail-closed paginated inspection of target compartment instances, ownership, and stack jobs."""
    eff_policy = policy or load_approved_policy()
    clk = clock or SystemOciClock()
    iaas_host = f"iaas.{cfg.region}.oraclecloud.com"
    rm_host = f"resourcemanager.{cfg.region}.oraclecloud.com"

    policy_ok, policy_msg = validate_environment_policy(cfg, stack_id, eff_policy, stack_obj=None)
    stack_ok = False
    stack_http = 0
    compartment_id = controller_state.get("target_compartment_id") or cfg.tenancy
    stack_obj: dict[str, Any] | None = None
    stack_err: str | None = None

    if policy_ok:
        try:
            s_resp = oci_request(
                cfg, "GET", rm_host, f"/20180917/stacks/{urllib.parse.quote(stack_id)}", transport=transport
            )
            stack_http = s_resp.status
            if s_resp.status == 200 and s_resp.json_valid and isinstance(s_resp.body, dict):
                stack_obj = s_resp.body
                if stack_obj.get("lifecycleState") in ("ACTIVE", None):
                    stack_ok = True
                    variables = stack_obj.get("variables") or {}
                    compartment_id = str(variables.get("compartment_ocid") or stack_obj.get("compartmentId") or cfg.tenancy)
                    policy_ok, policy_msg = validate_environment_policy(cfg, stack_id, eff_policy, stack_obj=stack_obj)
                else:
                    stack_err = f"Stack lifecycleState={stack_obj.get('lifecycleState')}"
            else:
                stack_err = f"Stack GET failed HTTP={s_resp.status} json_valid={s_resp.json_valid}"
        except Exception as exc:
            stack_err = f"Stack GET transport error: {exc}"
    else:
        stack_err = policy_msg

    controller_state["target_compartment_id"] = compartment_id

    inst_ok, inst_code, all_instances, inst_reqs, inst_err = oci_list_paginated(
        cfg,
        iaas_host,
        f"/20160918/instances?compartmentId={urllib.parse.quote(compartment_id)}&limit=1000",
        transport=transport,
    )
    jobs_ok, jobs_code, all_jobs, job_reqs, jobs_err = oci_list_paginated(
        cfg,
        rm_host,
        f"/20180917/jobs?stackId={urllib.parse.quote(stack_id)}&limit=1000",
        transport=transport,
    )

    active_instances: list[dict[str, Any]] = []
    unmanaged_instances: list[dict[str, Any]] = []
    for i in all_instances:
        state_str = i.get("lifecycleState")
        if state_str not in ("TERMINATED", "TERMINATING"):
            shape_cfg = i.get("shapeConfig") or {}
            row = {
                "id": i.get("id"),
                "display_name": i.get("displayName"),
                "state": state_str,
                "shape": i.get("shape"),
                "ocpus": shape_cfg.get("ocpus"),
                "memory_gb": shape_cfg.get("memoryInGBs"),
                "availability_domain": i.get("availabilityDomain"),
                "time_created": i.get("timeCreated"),
                "managed": _is_instance_managed_by_stack(i, stack_id, controller_state),
            }
            active_instances.append(row)
            if not row["managed"]:
                unmanaged_instances.append(row)

    for inst in active_instances:
        if inst["shape"] != ALLOWED_FREE_SHAPE:
            policy_ok = False
            policy_msg = f"Unexpected non-Always-Free shape detected: {inst['shape']}"
        elif (inst.get("ocpus") or 0) > int(eff_policy.get("max_ocpus", MAX_FREE_OCPUS)) or (
            inst.get("memory_gb") or 0
        ) > int(eff_policy.get("max_memory_gb", MAX_FREE_MEMORY_GB)):
            policy_ok = False
            policy_msg = (
                f"Instance exceeds approved policy limits: {inst.get('ocpus')} OCPU / {inst.get('memory_gb')} GB"
            )

    prev_verified = controller_state.get("verified_instance_id")
    lost_prior_instance = bool(
        stack_ok
        and inst_ok
        and prev_verified
        and not any(a["id"] == prev_verified for a in active_instances)
    )

    nonterminal_jobs = [
        j for j in all_jobs if j.get("lifecycleState") in ("ACCEPTED", "IN_PROGRESS", "CANCELLING")
    ]
    recent_jobs = [
        {
            "id": j.get("id"),
            "display_name": j.get("displayName"),
            "state": j.get("lifecycleState"),
            "operation": j.get("operation"),
            "time_created": j.get("timeCreated"),
        }
        for j in all_jobs[:8]
    ]

    inspection_ok = bool(stack_ok and inst_ok and jobs_ok)
    errors = [e for e in (stack_err, inst_err, jobs_err) if e]
    summary = {
        "checked_utc": clk.utc_now().isoformat(),
        "spec": "AI-BS-HA-OCI-001",
        "profile": cfg.profile,
        "controller_mode": controller_state.get("mode", "INSPECT"),
        "region": cfg.region,
        "stack_id": stack_id,
        "compartment_id": compartment_id,
        "inspection_ok": inspection_ok,
        "stack_http_status": stack_http,
        "compute_http_status": inst_code,
        "jobs_http_status": jobs_code,
        "request_ids": (inst_reqs + job_reqs)[:10],
        "budget_policy_ok": policy_ok,
        "budget_policy_message": policy_msg,
        "active_instances": active_instances,
        "unmanaged_instances": unmanaged_instances,
        "duplicate_targets": len(active_instances) > int(eff_policy.get("max_instances", 1)),
        "target_exists": len(active_instances) == 1 and len(unmanaged_instances) == 0,
        "lost_prior_instance": lost_prior_instance,
        "nonterminal_jobs": [j.get("id") for j in nonterminal_jobs],
        "all_jobs": all_jobs,
        "recent_jobs": recent_jobs,
        "errors": errors,
        "next_attempt_not_before_utc": controller_state.get("next_attempt_not_before_utc"),
        "active_job_id": controller_state.get("active_job_id"),
    }

    disk_summary = {k: v for k, v in summary.items() if k != "all_jobs"}
    _atomic_write_json(status_file, disk_summary)
    return summary


def monitor_existing_job(
    cfg: OciConfigSnapshot,
    rm_host: str,
    job_id: str,
    *,
    transport: TransportFn | None = None,
    log_file: Path = LOG_FILE,
    max_polls: int = 50,
    poll_sleep_sec: float = 6.0,
) -> tuple[str, str]:
    """Bounded poll of an active Resource Manager job; returns `(state, failure_class)`."""
    write_log(f"[WAIT_FOR_EXISTING_JOB] Monitoring Resource Manager job: {job_id}", log_file=log_file)
    for _ in range(max_polls):
        if poll_sleep_sec > 0:
            time.sleep(poll_sleep_sec)
        try:
            resp = oci_request(
                cfg, "GET", rm_host, f"/20180917/jobs/{urllib.parse.quote(job_id)}", transport=transport
            )
        except Exception as exc:
            write_log(f"  Job poll transport failure ({exc}); retaining job {job_id} as unresolved.", log_file=log_file)
            return "JOB_STATE_UNKNOWN", "TRANSPORT_ERROR"

        if resp.status != 200 or not resp.json_valid or not isinstance(resp.body, dict):
            cls = classify_failure(resp.status, resp.body)
            write_log(
                f"  Job status poll returned HTTP {resp.status} ({cls}); retaining job {job_id} as unresolved.",
                log_file=log_file,
            )
            return "JOB_STATE_UNKNOWN", cls

        raw_state = resp.body.get("lifecycleState")
        if not raw_state or not isinstance(raw_state, str):
            write_log(
                f"  Job status missing lifecycleState; retaining job {job_id} as unresolved.",
                log_file=log_file,
            )
            return "JOB_STATE_UNKNOWN", "UNKNOWN_FAILURE"

        if raw_state not in ("ACCEPTED", "IN_PROGRESS", "CANCELLING"):
            f_cls = "NONE" if raw_state == "SUCCEEDED" else classify_failure(resp.status, resp.body)
            write_log(f"  Job {job_id} finished with terminal state: {raw_state} (class={f_cls})", log_file=log_file)
            return raw_state, f_cls

    write_log(
        f"  Job {job_id} polling pass reached bound ({max_polls} polls); leaving unresolved for reconciliation.",
        log_file=log_file,
    )
    return "JOB_STATE_UNKNOWN", "NONE"


def _set_next_retry_not_before(
    state: dict[str, Any],
    *,
    now_utc: datetime,
    delay_seconds: int,
) -> int:
    enforced = max(POLL_INTERVAL_SECONDS, int(delay_seconds))
    state["next_attempt_not_before_utc"] = (now_utc + timedelta(seconds=enforced)).isoformat()
    return enforced


def run_controller_cycle(
    cfg: OciConfigSnapshot,
    state: dict[str, Any],
    attempt: int,
    *,
    stack_id: str = STACK_ID,
    policy: dict[str, Any] | None = None,
    transport: TransportFn | None = None,
    clock: Any | None = None,
    status_file: Path = STATUS_FILE,
    state_file: Path = CONTROLLER_STATE_FILE,
    log_file: Path = LOG_FILE,
    lock: ControllerLock | None = None,
    max_job_polls: int = 20,
    job_poll_sleep_sec: float = 6.0,
) -> tuple[str, int]:
    """Execute one fail-closed AI-BS-HA-OCI-001 controller cycle."""
    clk = clock or SystemOciClock()
    eff_policy = policy or load_approved_policy()
    rm_host = f"resourcemanager.{cfg.region}.oraclecloud.com"

    if lock is not None and not lock.acquire():
        write_log("[LOCK_HELD] Another controller process owns provisioning authority; exiting/waiting.", log_file=log_file)
        return "LOCK_HELD_BY_ANOTHER_CONTROLLER", 60

    prev_clock_utc = _parse_iso(state.get("last_clock_utc"))
    state["mode"] = "INSPECT"
    save_controller_state(state, state_file=state_file, clock=clk)
    summary = inspect_managed_environment(
        cfg,
        state,
        stack_id=stack_id,
        policy=eff_policy,
        transport=transport,
        status_file=status_file,
        clock=clk,
    )

    # 1. Fail-closed on config/policy/cost validation
    if not summary["budget_policy_ok"]:
        state["mode"] = "HALT_COST_POLICY" if "limit" in summary["budget_policy_message"].lower() or "shape" in summary["budget_policy_message"].lower() else "HALT_CONFIG_MISMATCH"
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(f"[{state['mode']}] {summary['budget_policy_message']}", log_file=log_file)
        return state["mode"], MAX_BACKOFF_SECONDS

    # 2. Fail-closed on incomplete or failed inspection
    if not summary["inspection_ok"]:
        cls = classify_failure(
            summary["compute_http_status"] or summary["jobs_http_status"] or summary["stack_http_status"],
            summary["errors"],
        )
        if cls == "AUTH_ERROR":
            state["mode"] = "HALT_AUTH_ERROR"
            save_controller_state(state, state_file=state_file, clock=clk)
            write_log(f"[HALT_AUTH_ERROR] Inspection failed due to authentication/permission error: {summary['errors']}", log_file=log_file)
            return "HALT_AUTH_ERROR", MAX_BACKOFF_SECONDS
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(
            f"[INSPECTION_FAILED:{cls}] stack={summary['stack_http_status']} compute={summary['compute_http_status']} "
            f"jobs={summary['jobs_http_status']} errors={summary['errors']}",
            log_file=log_file,
        )
        return "INSPECTION_FAILED", 300

    # 3. Halt for manual review if unmanaged or duplicate VMs exist
    if summary["unmanaged_instances"]:
        state["mode"] = "MANUAL_REVIEW_UNMANAGED_VM"
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(f"[MANUAL_REVIEW_UNMANAGED_VM] Unmanaged VM(s) present: {summary['unmanaged_instances']}", log_file=log_file)
        return "MANUAL_REVIEW_UNMANAGED_VM", MAX_BACKOFF_SECONDS

    if summary["duplicate_targets"]:
        state["mode"] = "MANUAL_REVIEW"
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(f"[MANUAL_REVIEW] Multiple instances detected: {summary['active_instances']}", log_file=log_file)
        return "MANUAL_REVIEW", MAX_BACKOFF_SECONDS

    # 4. Halt if previously verified VM disappeared (outage recovery, no blind reprovision!)
    if summary["lost_prior_instance"]:
        state["mode"] = "OUTAGE_RECOVERY_REQUIRED"
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(
            f"[OUTAGE_RECOVERY_REQUIRED] Previously verified instance {state.get('verified_instance_id')} is missing.",
            log_file=log_file,
        )
        return "OUTAGE_RECOVERY_REQUIRED", MAX_BACKOFF_SECONDS

    # 5. If exact managed target exists, verify and switch to MONITOR mode
    if summary["target_exists"]:
        target = summary["active_instances"][0]
        state["verified_instance_id"] = target["id"]
        state["active_job_id"] = None
        state["pending_operation"] = None
        state["uncertain_creation_outcome"] = False
        state["next_attempt_not_before_utc"] = None
        if target["state"] == "RUNNING":
            state["mode"] = "MONITOR"
            save_controller_state(state, state_file=state_file, clock=clk)
            write_log(
                f"[MONITOR] Verified RUNNING Standby Instance: {target['display_name']} "
                f"({target['id']}, shape={target['shape']} {target['ocpus']} OCPU / {target['memory_gb']} GB)",
                log_file=log_file,
            )
            return "MONITOR_READY", POLL_INTERVAL_SECONDS
        state["mode"] = "VERIFY"
        save_controller_state(state, state_file=state_file, clock=clk)
        return "VERIFY_PENDING", 60

    # 6. Check if a persisted pending_operation matches an existing job from paginated inspection (OCI-03)
    pending_op = state.get("pending_operation")
    if isinstance(pending_op, dict) and pending_op.get("operation_id"):
        op_id = str(pending_op["operation_id"])
        matched_job = next(
            (j for j in summary["all_jobs"] if op_id in str(j.get("displayName") or "")),
            None,
        )
        if matched_job is not None:
            m_id = str(matched_job["id"])
            m_state = str(matched_job.get("lifecycleState") or "UNKNOWN")
            state["active_job_id"] = m_id
            state["uncertain_creation_outcome"] = False
            if m_state in ("ACCEPTED", "IN_PROGRESS", "CANCELLING"):
                save_controller_state(state, state_file=state_file, clock=clk)
                term, cls = monitor_existing_job(
                    cfg, rm_host, m_id, transport=transport, log_file=log_file,
                    max_polls=max_job_polls, poll_sleep_sec=job_poll_sleep_sec,
                )
                if term == "JOB_STATE_UNKNOWN":
                    return "JOB_STATE_UNKNOWN", 300
                if term in ("FAILED", "CANCELED"):
                    state["active_job_id"] = None
                    state["pending_operation"] = None
                    wait_s = _set_next_retry_not_before(state, now_utc=clk.utc_now(), delay_seconds=POLL_INTERVAL_SECONDS)
                    save_controller_state(state, state_file=state_file, clock=clk)
                    return cls or "JOB_FAILED", wait_s
                return "RECONCILED_EXISTING_JOB", POLL_INTERVAL_SECONDS
            if m_state == "SUCCEEDED":
                state["active_job_id"] = None
                state["pending_operation"] = None
                save_controller_state(state, state_file=state_file, clock=clk)
                return "RECONCILED_EXISTING_JOB", 60
            # Reconciled terminal failure
            state["active_job_id"] = None
            state["pending_operation"] = None
            state["uncertain_creation_outcome"] = False
            wait_s = _set_next_retry_not_before(state, now_utc=clk.utc_now(), delay_seconds=POLL_INTERVAL_SECONDS)
            save_controller_state(state, state_file=state_file, clock=clk)
            return "RECONCILED_EXISTING_JOB", wait_s

    # 7. Reconcile any active/nonterminal Resource Manager job before submitting another
    if summary["nonterminal_jobs"]:
        existing_job_id = str(summary["nonterminal_jobs"][0])
        state["mode"] = "CLAIM"
        state["active_job_id"] = existing_job_id
        save_controller_state(state, state_file=state_file, clock=clk)
        term_state, f_cls = monitor_existing_job(
            cfg, rm_host, existing_job_id, transport=transport, log_file=log_file,
            max_polls=max_job_polls, poll_sleep_sec=job_poll_sleep_sec,
        )
        if term_state == "JOB_STATE_UNKNOWN":
            return "JOB_STATE_UNKNOWN", 300
        if term_state in ("FAILED", "CANCELED"):
            state["active_job_id"] = None
            state["pending_operation"] = None
            state["uncertain_creation_outcome"] = False
            wait_s = _set_next_retry_not_before(state, now_utc=clk.utc_now(), delay_seconds=POLL_INTERVAL_SECONDS)
            save_controller_state(state, state_file=state_file, clock=clk)
            return f_cls, wait_s
        return "RECONCILED_EXISTING_JOB", POLL_INTERVAL_SECONDS

    # 8. If a previously tracked active_job_id was left unresolved without appearing active above, verify its GetJob state
    if state.get("active_job_id"):
        term_state, f_cls = monitor_existing_job(
            cfg, rm_host, str(state["active_job_id"]), transport=transport, log_file=log_file,
            max_polls=1, poll_sleep_sec=0.0,
        )
        if term_state == "JOB_STATE_UNKNOWN":
            return "JOB_STATE_UNKNOWN", 300
        if term_state in ("ACCEPTED", "IN_PROGRESS", "CANCELLING"):
            return "RECONCILED_EXISTING_JOB", 60
        state["active_job_id"] = None
        state["pending_operation"] = None
        save_controller_state(state, state_file=state_file, clock=clk)

    # 9. Enforce persisted 20-minute cadence across restarts AND backward clock-jump guard (OCI-06)
    now_utc = clk.utc_now()
    if prev_clock_utc is not None and now_utc < prev_clock_utc - timedelta(seconds=60):
        wait_s = _set_next_retry_not_before(state, now_utc=now_utc, delay_seconds=POLL_INTERVAL_SECONDS)
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(f"[CLOCK_JUMP_DELAY] Wall clock moved backward; delaying retry for {wait_s}s.", log_file=log_file)
        return "CLOCK_JUMP_DELAY", wait_s

    not_before = _parse_iso(state.get("next_attempt_not_before_utc"))
    if not_before is not None and now_utc < not_before:
        rem = int(max(1.0, (not_before - now_utc).total_seconds()))
        write_log(f"[COOLDOWN_ENFORCED] Next APPLY not permitted until {not_before.isoformat()} ({rem}s remaining).", log_file=log_file)
        return "COOLDOWN_ENFORCED", rem

    # 10. Reuse existing retry identity if prior response was uncertain, else allocate new durable operation identity (OCI-03)
    state["mode"] = "CLAIM"
    if isinstance(pending_op, dict) and state.get("uncertain_creation_outcome"):
        created_dt = _parse_iso(pending_op.get("created_utc"))
        if created_dt is not None and (now_utc - created_dt) >= timedelta(hours=23):
            state["mode"] = "MANUAL_REVIEW"
            save_controller_state(state, state_file=state_file, clock=clk)
            write_log("[MANUAL_REVIEW] Uncertain operation retry token nearing/past 24h TTL.", log_file=log_file)
            return "MANUAL_REVIEW", MAX_BACKOFF_SECONDS
        op_id = str(pending_op["operation_id"])
        retry_token = str(pending_op["opc_retry_token"])
        write_log(f"[RECONCILE_BEFORE_RETRY] Confirmed 0 jobs/instances; reusing persisted op={op_id}.", log_file=log_file)
    else:
        op_id = uuid.uuid4().hex[:16]
        retry_token = uuid.uuid4().hex

    payload = {
        "stackId": stack_id,
        "displayName": f"aibs-apply-{op_id}",
        "operation": "APPLY",
        "jobOperationDetails": {
            "operation": "APPLY",
            "executionPlanStrategy": "AUTO_APPROVED",
        },
        "freeformTags": {"aibs_operation_id": op_id},
    }
    req_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    req_hash = hashlib.sha256(req_bytes).hexdigest()

    state["pending_operation"] = {
        "deployment_id": f"dep-{op_id}",
        "stack_id": stack_id,
        "plan_hash": eff_policy.get("expected_plan_hash") or "UNSET",
        "request_body_hash": req_hash,
        "operation_id": op_id,
        "opc_retry_token": retry_token,
        "created_utc": now_utc.isoformat(),
        "state": "PENDING_SUBMIT",
    }
    save_controller_state(state, state_file=state_file, clock=clk)

    write_log(f"--- Attempt #{attempt} [CLAIM]: Submitting Resource Manager APPLY (op={op_id}) ---", log_file=log_file)
    try:
        resp = oci_request(
            cfg,
            "POST",
            rm_host,
            "/20180917/jobs",
            payload,
            extra_headers={"opc-retry-token": retry_token},
            transport=transport,
        )
    except Exception as exc:
        state["uncertain_creation_outcome"] = True
        state["pending_operation"]["state"] = "SUBMISSION_UNKNOWN"
        state["last_failure_class"] = "TRANSPORT_ERROR"
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(f"[SUBMISSION_UNKNOWN] CreateJob transport error ({exc}); reconciling before any retry.", log_file=log_file)
        return "SUBMISSION_UNKNOWN", 300

    if resp.status == 429:
        c429 = int(state.get("consecutive_429s", 0)) + 1
        state["consecutive_429s"] = c429
        state["pending_operation"] = None
        state["uncertain_creation_outcome"] = False
        state["last_failure_class"] = "RATE_LIMITED"
        retry_hdr = 0
        if resp.retry_after and str(resp.retry_after).isdigit():
            retry_hdr = int(resp.retry_after)
        backoff = max(retry_hdr, min(MAX_BACKOFF_SECONDS, POLL_INTERVAL_SECONDS * (2 ** min(c429, 3))))
        wait_s = _set_next_retry_not_before(state, now_utc=clk.utc_now(), delay_seconds=backoff)
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(f"[RATE_LIMITED] CreateJob HTTP 429; waiting {wait_s}s.", log_file=log_file)
        return "RATE_LIMITED", wait_s

    if resp.status in (401, 403):
        state["mode"] = "HALT_AUTH_ERROR"
        state["pending_operation"] = None
        state["uncertain_creation_outcome"] = False
        state["last_failure_class"] = "AUTH_ERROR"
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(f"[HALT_AUTH_ERROR] CreateJob HTTP {resp.status}: {resp.body}", log_file=log_file)
        return "HALT_AUTH_ERROR", MAX_BACKOFF_SECONDS

    if resp.status not in (200, 201, 202) or not resp.json_valid or not isinstance(resp.body, dict) or "id" not in resp.body:
        f_cls = classify_failure(resp.status, resp.body)
        state["pending_operation"] = None
        state["uncertain_creation_outcome"] = False
        state["last_failure_class"] = f_cls
        if f_cls == "QUOTA_OR_CONFIG_ERROR":
            state["mode"] = "HALT_CONFIG_MISMATCH"
        wait_s = _set_next_retry_not_before(state, now_utc=clk.utc_now(), delay_seconds=POLL_INTERVAL_SECONDS)
        save_controller_state(state, state_file=state_file, clock=clk)
        write_log(f"[CREATE_JOB_FAILED:{f_cls}] HTTP {resp.status}: {resp.body}", log_file=log_file)
        return f_cls, wait_s

    # Persist returned job_id immediately BEFORE polling
    state["consecutive_429s"] = 0
    state["uncertain_creation_outcome"] = False
    job_id = str(resp.body["id"])
    state["active_job_id"] = job_id
    state["pending_operation"]["job_id"] = job_id
    state["pending_operation"]["opc_request_id"] = resp.request_id
    state["pending_operation"]["state"] = "SUBMITTED"
    save_controller_state(state, state_file=state_file, clock=clk)
    write_log(f"Apply Job submitted: {job_id} (req_id={resp.request_id})", log_file=log_file)

    term_state, job_cls = monitor_existing_job(
        cfg, rm_host, job_id, transport=transport, log_file=log_file,
        max_polls=max_job_polls, poll_sleep_sec=job_poll_sleep_sec,
    )
    if term_state == "JOB_STATE_UNKNOWN":
        return "JOB_STATE_UNKNOWN", 300

    if term_state == "SUCCEEDED":
        state["mode"] = "VERIFY"
        state["pending_operation"] = None
        save_controller_state(state, state_file=state_file, clock=clk)
        post_summary = inspect_managed_environment(
            cfg, state, stack_id=stack_id, policy=eff_policy, transport=transport, status_file=status_file, clock=clk,
        )
        if post_summary["target_exists"]:
            inst = post_summary["active_instances"][0]
            state["verified_instance_id"] = inst["id"]
            save_controller_state(state, state_file=state_file, clock=clk)
            write_log(f"Job SUCCEEDED and verified instance: {inst['id']} (state={inst['state']})", log_file=log_file)
            return "VERIFY_AFTER_SUCCEEDED", 15
        write_log("Job reported SUCCEEDED but target verification incomplete; staying in VERIFY.", log_file=log_file)
        return "VERIFY_MISSING_INSTANCE", POLL_INTERVAL_SECONDS

    state["active_job_id"] = None
    state["pending_operation"] = None
    final_cls = job_cls if job_cls != "NONE" else "CAPACITY_SATURATED"
    state["last_failure_class"] = final_cls
    wait_s = _set_next_retry_not_before(state, now_utc=clk.utc_now(), delay_seconds=POLL_INTERVAL_SECONDS)
    save_controller_state(state, state_file=state_file, clock=clk)
    write_log(f"Apply Job terminal={term_state} ({final_cls}); next attempt not before {wait_s}s.", log_file=log_file)
    return final_cls, wait_s


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI-BS-HA-OCI-001 Resource Manager Provisioning Controller")
    parser.add_argument("--check-only", action="store_true", help="Inspect read-only state and exit non-zero on error")
    parser.add_argument("--profile", default=None, help="Explicit OCI config profile name (default DEFAULT)")
    parser.add_argument("--config", default=CONFIG_PATH, help="Path to OCI config file")
    parser.add_argument("--state-file", default=str(CONTROLLER_STATE_FILE), help="Path to controller state JSON")
    parser.add_argument("--status-file", default=str(STATUS_FILE), help="Path to status JSON")
    parser.add_argument("--lock-file", default=str(LOCK_FILE), help="Path to exclusive controller lock file")
    parser.add_argument("--log-file", default=str(LOG_FILE), help="Path to controller log file")
    parser.add_argument("--policy-file", default=str(DEFAULT_POLICY_PATH), help="Path to approved resource policy JSON")
    args = parser.parse_args(argv)

    state_file = Path(args.state_file)
    status_file = Path(args.status_file)
    lock_file = Path(args.lock_file)
    log_file = Path(args.log_file)
    policy = load_approved_policy(Path(args.policy_file))

    try:
        cfg = load_oci_config(args.config, profile=args.profile)
        state = load_controller_state(state_file)
    except Exception as exc:
        print(json.dumps({"inspection_ok": False, "error": str(exc)}, indent=2))
        return 1

    if args.check_only:
        try:
            summary = inspect_managed_environment(
                cfg, state, policy=policy, status_file=status_file,
            )
            disk_summary = {k: v for k, v in summary.items() if k != "all_jobs"}
            print(json.dumps(disk_summary, indent=2))
            return 0 if summary.get("inspection_ok") else 1
        except Exception as exc:
            print(json.dumps({"inspection_ok": False, "error": str(exc)}, indent=2))
            return 1

    lock = ControllerLock(lock_file)
    if not lock.acquire():
        write_log(f"[LOCK_HELD] Another controller owns lock {lock_file}; exiting cleanly.", log_file=log_file, raise_on_error=False)
        return 0

    try:
        write_log("=================================================================", log_file=log_file)
        write_log(f"AI-BS-HA-OCI-001 Provisioning Controller Active (profile={cfg.profile})", log_file=log_file)
        write_log(f"Target Stack: {STACK_ID} | Poll Cadence: {POLL_INTERVAL_SECONDS}s", log_file=log_file)
        write_log("=================================================================", log_file=log_file)

        attempt = 1
        while True:
            try:
                _outcome, sleep_sec = run_controller_cycle(
                    cfg,
                    state,
                    attempt,
                    policy=policy,
                    status_file=status_file,
                    state_file=state_file,
                    log_file=log_file,
                )
            except Exception as exc:
                write_log(f"Controller cycle #{attempt} error: {exc}", log_file=log_file, raise_on_error=False)
                sleep_sec = POLL_INTERVAL_SECONDS
            time.sleep(sleep_sec)
            attempt += 1
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
