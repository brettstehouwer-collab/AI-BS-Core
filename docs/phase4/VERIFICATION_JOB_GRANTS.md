# Host verification grants and durable attempt reservations

Record125, October 26, 2026. Status: dormant trusted-controller prerequisite; no operational issuer, worker admission or execution path.

`isolated_workers/protocol/verification_grants.py` implements exact-scope Ed25519 verification and a durable single-use attempt reservation. It does not issue grants, provision keys or stores, launch a process, control a VM, enforce resources, collect execution results or authorize application/deployment. A successful signature or reservation remains data. The existing `windows_vm` provider guards still return `ISOLATION_UNAVAILABLE` without a trusted-host fallback. Diagnostic port 18443 remains diagnostic-only.

## Implemented API

| API | Implemented behavior | Caller prerequisite |
| --- | --- | --- |
| `prepare_scope(admission, contents, *, worker, runtime, resource_profile, environment, fixture_manifest_sha256)` | Validates schema2 admitted bytes with the existing input validator, validates the bounded Python profile, detaches caller-owned objects, and returns canonical UTF-8 scope bytes smaller than 131072 bytes. | All admission, immutable roles, worker/runtime observations, fixture digest and profile must originate independently from reviewed host policy. Calling the function does not establish their provenance or approval. |
| `verify_grant(packet, *, pinned_verifiers, expected_scope, now_utc, authority_domain='disposable_verification')` | Verifies strict bounded canonical JSON, reconstructs and validates the complete expected scope and its derived digests/commands, checks exact fields/domain/purpose/scope, pinned Ed25519 signature and validity interval; returns a frozen `VerifiedGrant` with packet and identity/digest metadata. | Supply the independently prepared expected scope, trusted current UTC and trusted public-key pins. This API neither consumes replay scope nor launches anything. |
| `VerificationAttemptRegistry(connection, *, store_id, authority_domain, create=False)` | Checks a dedicated persistent SQLite store, exact schema and stored domain/ID. Explicit creation requires an empty store. No migration or pruning. | The native host controller must independently provision and protect one persistent store and pin its object identity and continuity. The library accepts a supplied connection; it does not authenticate a filesystem path. |
| `registry.claim_once(packet, *, pinned_verifiers, expected_scope, current_identity, clock)` | Within `BEGIN IMMEDIATE`, samples the trusted clock callback, re-verifies packet/scope/time and supplied current worker/runtime identity, rejects grant or globally unique attempt reuse, then samples the clock again immediately before insertion and refuses expiry or time reversal. Retains exact packet and digests; returns a `ReservationReceipt` only after confirmed commit. | Current identity and the callable clock must originate independently from the protected controller. Supplying matching dictionaries is not executable/image attestation. |
| `registry.inspect(task_id, attempt_id)` | Returns the retained reservation metadata or `None`; does not launch, deliver, replay or promote anything. | Recovery inspection is data only. An interrupted attempt requires independent reconciliation. |

`ReservationReceipt.state` is `ATTEMPT_RESERVED`. Its `worker_admitted`, `execution_authorized` and `apply_authorized` fields are fixed false, and `verification_status` is fixed `not_run`. A caller-supplied `VerifiedGrant` cannot bypass re-verification inside `claim_once`.

## Exact prepared scope

The complete scope is signed and compared byte-for-byte with the host's expected canonical scope. Verification reconstructs the expected scope from its validated manifest, worker/runtime, profile, explicit environment and fixture digest, including derived hashes and commands; a caller cannot make inconsistent derived fields valid by signing them. This structural validation does not reread actual input bytes or attest their provenance; the future launcher must recheck stable admitted objects. Scope fields are:

- `input_manifest`: the existing validated schema2 envelope, binding task/request/unique attempt, repository/base revision/authorization reference, base-image digest, exact file paths/lengths/SHA-256/roles, check IDs/argv and admitted time/output limits. `input_manifest_sha256` retains the older input-validator JSON serialization; it is deliberately distinct from the compact canonical serialization used for the grant.
- `immutable_files` and `immutable_files_sha256`: all admitted `verification` and `dependency` entries. At least one verification file is required. The function verifies consistency, not independent ownership of the test graph; a candidate cannot establish its own immutable-test authority.
- `fixture_manifest_sha256`: an explicit digest supplied by the host. This field does not read or discover the originating fixture.
- `worker`: exactly `worker_id`, `vm_id`, `image_sha256`, `disposable_image_id`, `account_sid`. The image digest must match the input manifest. These are identity requirements; no image/account is created or inspected.
- `runtime`: exactly `executable_path`, `executable_sha256`, `runtime_tree_sha256`, `protection_receipt_sha256`. The executable path must use a canonical absolute Windows drive path with forward slashes and end in `/python.exe`; unsafe relative/UNC/traversal forms are refused. Digests do not themselves establish protected loaded code.
- `commands`: one fixed command per admitted check, with its `check_id`, the exact runtime `executable`, argv beginning with that absolute executable followed by `-m unittest`, and `working_directory='.'` inside the future admitted task root. Shell commands and general project execution are outside this first profile.
- `environment`: `inherit=false` and explicit `values`. Only `SYSTEMROOT`, `TEMP`, `TMP`, `PYTHONUTF8`, `PYTHONIOENCODING`, `PYTHONDONTWRITEBYTECODE` are allowed, with bounded string values and no NULs. No inherited host environment is authorized by the scope; enforcing this remains a launcher requirement.
- `resource_profile` and `resource_profile_sha256`: exactly the fields below. They specify requirements for a future controller, not measured enforcement.

| Resource field | Validator constraint |
| --- | --- |
| `profile_id` | Bounded opaque label |
| `vcpus` | Integer 1–4 |
| `vm_memory_bytes` | Integer 268435456–17179869184 |
| `task_memory_bytes` | Integer 16777216–17179869184 and no greater than VM memory |
| `task_cpu_rate_percent` | Integer 1–100 |
| `process_limit` | Integer 1–64 |
| `check_seconds` | Integer 1–120; matches admitted manifest limit |
| `total_seconds` | Integer 1–600; matches admitted manifest limit |
| `output_bytes` | Integer 1024–1048576; matches admitted manifest limit; combined stdout/stderr |
| `artifact_files` | Exactly 20 |
| `artifact_file_bytes` | Exactly 2097152 |
| `artifact_total_bytes` | Exactly 16777216 |
| `network_policy` | Exactly `deny_all` |

These ranges are syntax/admission ceilings, not an approved operating profile. The actual disposable VM RAM, CPU-rate semantics, process-tree accounting and process-count enforcement remain unresolved. The earlier 2-vCPU/512-MiB task proposal and the synthetic test profile are not operational acceptance. Preserve the retained default 30-second check, 180-second task and 262144-byte combined console bound unless an exact reviewed scope selects otherwise; the combined maximum remains 1 MiB. No tests establish live enforcement of any listed limit.

## Signature and domain separation

The packet has exactly `body` and `signature`. The body has exactly `schema_version`, `domain`, `authority_domain`, `purpose`, `issuer_id`, `key_id`, `grant_id`, `issued_at`, `expires_at`, `scope`. Version is integer 1, domain is `AI-BS/host-verification-grant/v1`, and purpose is `bounded_verification`. Packets are at most 262144 bytes. UTF-8 JSON must have sorted keys, compact separators, no duplicate fields or nonfinite numbers and exactly the canonical encoding; boolean values cannot substitute for required integer fields.

The Ed25519 signature covers `b'AI-BS/host-verification-grant/v1\x00' + canonical(body)`. The verifier selects a 32-byte raw public key exclusively from host-supplied `pinned_verifiers[(issuer_id, key_id)]`; a packet cannot supply its own trusted key. The signature is represented as 128 lowercase hexadecimal characters. Validity requires `issued_at <= now_utc < expires_at` and a positive lifetime no greater than 600 seconds. Trusted clock freshness and pin provisioning remain external responsibilities.

Two exact authority domains exist: `infrastructure_test` and `disposable_verification`. Both packet verification and the registry bind the selected domain. The tests use `infrastructure_test`, ephemeral unsaved test private keys and synthetic bytes/worker/runtime identities; a test-domain packet is rejected by the default disposable verifier. Operational pin/domain policy must be controlled outside candidate content. No guest-shared HMAC credential is used as grant authority. No host signing private key, issuer endpoint, issuer implementation, pin distribution/rotation, secret storage or operational signing-key provisioning is added.

The public-key verification API and raw-key/signature sizes follow [cryptography 49.0.0 Ed25519 documentation](https://cryptography.io/en/49.0.0/hazmat/primitives/asymmetric/ed25519/). The official release49 [PDF, Ed25519 section](https://cryptography.io/_/downloads/en/49.0.0/pdf/#page=130) was the accessible versioned primary reference during this review; the HTML endpoint was unavailable through the browsing tool. Library verification authenticates signed bytes against supplied pins; it does not establish safe execution or policy provenance.

## Durable reservation and uncertainty

The dedicated SQLite main database must be persistent with no additional attached databases, an allowed durable journal mode and `synchronous=FULL` or `EXTRA`. Each transaction checks the exact schema and `(version, store_id, authority_domain)` record. Alongside primary key `(task_id, attempt_id)`, separate unique indexes on `attempt_id` and `grant_id` prevent reuse anywhere in this store. Moving an attempt to a different task/worker or reissuing its signed grant does not permit another reservation. Accepted records retain the original packet BLOB, hashes, worker and expiry. Expired records are not removed here.

The registry refuses caller-owned active transactions without committing or rolling them back. Concurrency is serialized through SQLite's write transaction, with an instance lock for connection use. Its callable clock is sampled after the write lock is acquired and again immediately before insertion; a wait cannot preserve a caller's stale timestamp, and backward movement between those samples is refused. Clock trust and system-wide rollback detection remain external requirements. A successful signature check alone has no replay protection; only a confirmed durable `claim_once` reserves the attempt.

Errors during commit, a commit that returns while a transaction remains active, SQLite/OS errors, non-`Exception` interruptions or rollback failure quarantine the registry instance. Cleanup owns its attempted `BEGIN` even when SQLite starts the transaction before its acknowledgement is interrupted; it rolls back that owned active transaction without touching a pre-existing caller transaction. No receipt is returned on uncertainty. A failure after the underlying commit can leave a valid retained reservation despite the missing acknowledgement. Preserve the store and failure evidence; independently reopen and inspect it for reconciliation. Inspection never supplies permission to relaunch, and a committed reservation remains a replay. Do not respond to ambiguous commit by generating a new attempt, replacing the database or retrying execution automatically.

The store ID is checked metadata, not physical identity attestation. A fresh database with a copied ID can lose replay history. A native controller must pin one protected authoritative store, its relevant parent/object identity, trusted writer policy and backup/recovery continuity; detect replacement/rollback and quarantine uncertain history. The registry does not provision these protections, enforce physical disk quotas, supply cross-store atomicity, create a worker lease or prove exactly-once delivery/execution. Database files are infrastructure evidence, never a production/private personal database.

## Required native controller and launcher gates

Before operational connection, review and implement a protected native entry that obtains its own authenticated caller policy and immutable manifest/test authority. It must verify protected code, runtime/dependencies, executable/image hashes and relevant ancestors on stable held objects before use; measure the actual worker token and current VM/runtime identity; and enforce the exact approved account, command, task working directory and explicit environment. Current host metadata and source digests cannot stand in for these checks.

Separately provision the protected issuer/pin and single-store continuity mechanism, bind a durable lease to fresh controller/VM identity, and persist intent before consequential actions. Keep the signed-in integration guest for staging/coordination. Establish a separate clean licensed disposable image and standard execution account with no Codex credentials, private stores/documents or host model stores. Enforce all offline network/device restrictions and the reviewed CPU/memory/process/time/output limits; reject unavailable isolation without host substitution. Do not enable general admission to run verification.

Implement bounded authenticated job delivery, result receipts bound to the originating attempt, safe regular-file collection without host execution, cancellation/process-tree termination, confirmed terminal VM state, interruption reconciliation and failed-shutdown quarantine. Only a separately accepted controller lifecycle can connect a narrow verification reservation to execution. Application/deployment require their later exact patch/base authorization, freshness/original backups, coordinated health checks and rollback. A protected host staging directory is data quarantine and cannot execute returned candidates as implicit verification.

## Evidence and preserved work

The retained `number-summary-roundtrip-v1` fixture is unchanged at `C:\AI-BS\backups\durable_packet_inbox_20261026_record122\guest_test_fixture`. Its manifest SHA-256 is `eba6865c29b2cf41507a9fbafd14492b5c93b5263d55017ae6d89a514714f37c`; byte lengths and all five hashes are retained in the Record125 baseline. The seven fixture tests and all fourteen actual disposable containment cases remain **NOT RUN**. The new infrastructure tests neither import nor execute the retained candidate/tests and do not replace the fixture with their synthetic content.

The fixture also contains preserved pre-existing `__pycache__` entries: `number_summary.cpython-312.pyc` (1054 bytes) and `test_number_summary.cpython-312.pyc` (2742 bytes), both with creation/modification time `2026-10-26T08:11:17Z`, before this turn. These files show earlier compilation/import history may exist; they cannot establish where execution occurred, whether the seven tests ran or whether they passed. The actual disposable seven-test demonstration remains unverified. The preservation audit's initial directory-as-file error and corrected audit of the five known original files are retained separately.

The final Record125 `publication_combined_receipt.json` records **107 passing infrastructure tests** (24 new grant/registry tests plus 83 existing checks); `publication_combined_tests.txt` records 41.010 seconds. Candidate tests and disposable-VM checks both remain zero. This final run supersedes the earlier 19/102-test receipts retained as development evidence. Coverage includes signature/scope/domain/expiry refusals, complete scope reconstruction, changed bytes/identity, globally unique attempts, concurrent claims, clock expiry/resampling, schema/durability rejection, restart inspection, synthetic commit interruption and interrupted `BEGIN` cleanup. Backward-clock refusal is implemented in source without a dedicated reversal test. These are infrastructure checks, not real worker denial, resource enforcement, native loaded-code attestation, authenticated execution receipts or VM acceptance. No production application, deployment or full Phase4–6 status follows from them.

Local implementation and retained evidence:

- [verification_grants.py](/C:/AI-BS/isolated_workers/protocol/verification_grants.py) and [test_verification_grants.py](/C:/AI-BS/isolated_workers/protocol/test_verification_grants.py).
- [coding_vm_inputs.py](/C:/AI-BS/backend/core/coding_vm_inputs.py), [replay_claims.py](/C:/AI-BS/isolated_workers/protocol/replay_claims.py), [coding_workflow.py](/C:/AI-BS/backend/core/coding_workflow.py) and [guest_pairing.py](/C:/AI-BS/isolated_workers/connector/guest_pairing.py).
- [Isolated worker contract](/C:/AI-BS/docs/phase4/ISOLATED_WORKER_CONTRACT.md) and [host source/exchange protection review](/C:/AI-BS/docs/phase4/HOST_SOURCE_EXCHANGE_PROTECTION_REVIEW.md).
- [Record125 baseline](/C:/AI-BS/backups/local_verification_20261026_record125/baseline_readonly.json), [containment status](/C:/AI-BS/backups/local_verification_20261026_record125/containment_status.md), [final infrastructure receipt](/C:/AI-BS/backups/local_verification_20261026_record125/publication_combined_receipt.json) and [final infrastructure output](/C:/AI-BS/backups/local_verification_20261026_record125/publication_combined_tests.txt). Earlier `green_receipt.json` and `combined_tests.txt` remain retained historical evidence.
