AI-BS Oracle Hot Standby — Coding-Agent Execution Brief
Document ID: AI-BS-HA-OCI-001-AGENTS
Revision: 1.0
Prepared: November 19, 2026 — America/New_York
Owner: Brett Stehouwer
Mode: Windows primary + OCI passive hot standby
Document status: Instructions prepared; implementation, deployment, and live operation are not verified.
Source: AI-BS_Oracle_Hot_Standby_Implementation_Instructions.md, saved version 0. This is a separate execution companion; keep the source specification intact.
1. Start here: direct instruction to the implementation agent
You are the AI-BS implementation lead. Convert the existing Oracle hot-standby design into tested, reviewable changes in the actual AI-BS project. Work phase by phase. Preserve an evidence trail, make recovery behavior explicit, and keep only one authority capable of submitting exchange mutations.
Begin with Phase 0. Confirm the real host, project root, repository state, applicable AGENTS.md instructions, running services, and existing implementation. Resume verified work instead of recreating it. Search with rg or rg --files when available. Do not overwrite unrelated local changes or replace the project's existing agent instructions with this file.
Complete authorized inspection, isolated edits, offline tests, documentation, and deployment preparation without repeatedly asking to proceed. Use existing, specific operator authorization when it covers the action. This document is not, by itself, authorization to place trades, restart production, change account credentials, create paid infrastructure, terminate resources, or promote the standby.
If a necessary production action is not already authorized, first finish its concrete change set, test evidence, cost impact where applicable, and rollback plan. Then ask about that exact action. Do not stop routine development at every phase boundary merely to request confirmation.
Completion target: A tested implementation and operator runbook, followed by deployment and live verification only within the authorized scope. Report separate outcomes for code, tests, deployment, and operating health. Never describe a prepared file or a passed simulation as a running standby.
Intended first response from the implementation agent
Report the verified host and project path, current repository revision if available, the phase being resumed, and the immediate inspection work. Then perform that work. Do not respond only with a plan.
2. Operating rules and production boundaries
Rule
Required behavior
One execution authority
Every create, amend, cancel, bulk order, and strategy rearm operation uses the same enforced execution path.
Unknown state
Block new exchange mutations until authority and execution state are established. Retain approved emergency controls through that same authority path.
Passive means passive
A standby process must be technically unable to submit exchange mutations while passive. A configuration label alone is insufficient.
Existing orders
Preserve valid resting orders during restart and takeover unless an established risk procedure requires an authorized change.
Strategy preservation
Keep the current take-profit policy, tranche sizing, reserve accounting, and rearm behavior as found. Reliability work is not permission to change trading strategy.
Evidence
Treat historic balances, fees, service counts, instance IDs, and status messages as unverified until checked against current sources.
Credentials
Do not expose secrets, copy trade keys into replicas, or weaken withdrawal/IP restrictions to make failover work.
Scope
Do not provision, restart services, send notifications to other people, or mutate exchange orders simply because a test mentions them. Check current authorization.
Failure rule
Stop the same engineering or validation step after two consecutive unexpected failures; preserve evidence and report the blocker.
Progress
Continue independent authorized work when one step is blocked. Keep updates concise and specific.
The two-failure rule applies to implementation, validation, and repair attempts. Do not evade it by renaming the step or changing agents. A deliberately injected error in a passing fault test is not an unexpected failure. A documented WAITING_FOR_CAPACITY outcome can follow the configured runtime retry policy; authentication failures, uncertain mutations, and corrupt state require their own halt behavior immediately.
No inference of “guaranteed profit,” “zero fees,” “front of the queue,” “exactly-once exchange execution,” “free infrastructure,” or “24/7 ready” may be based solely on configuration values or process presence.
3. Expected environment: discover before using
Item
Historical/proposed baseline
Required verification
Project
C:\AI-BS
Actual root, working tree, branch, existing instructions
Windows trader
structural_dip_engine.py, historically port 8007
Real entry point, process owner, launch method, API paths, current mode
OCI controller
oci_stack_claimer.py, previously under scratch
Actual source, process, invocation, config profile and state paths
Signing dependency
pure_rsa_sha256.py
Inspect its actual implementation and test with disposable keys
Supervisor
aibs_24x7_supervisor.py
Restart policy, startup mechanism, duplicate prevention, health criteria
Cloud target
us-chicago-1, proposed VM.Standard.A1.Flex, 1 OCPU / 6 GB
Account eligibility, resource compatibility, approved configuration and cost
Related services
Scouts, risk watchdog, notifier, backend, UI, vector store, Ollama, tunnel
Which are present and which are true execution dependencies
Standby
ARM64 Linux
Supported OS, dependency compatibility, service manager, persistent storage
127.0.0.1 refers to the machine running the check. A successful localhost request from a cloud coding workspace is not evidence about the Windows PC. Record where each check ran.
Do not assume a startup-folder launcher provides recovery before sign-in. Verify the selected Windows boot mechanism under the intended service account, including access to its credential store. Do not export Windows-bound credentials merely to work around an account mismatch.
4. Team responsibilities and shared-work discipline
Use parallel agents only when their tasks are independent and capacity is available.
Role
Ownership
Evidence
Integration lead
Scope, baseline, phase gates, merge order, deployment package
Status file and release summary
Trading reliability agent
Journal, reconciliation, gateway interface, supervisor integration
Recovery and stale-authority tests
OCI agent
Claimer, Resource Manager configuration, provisioning recovery
Request fixtures and restart/idempotency tests
Independent reviewer
Fault cases, security boundary, evidence review
Findings and acceptance decision
Assign one writer per shared file or isolate changes in worktrees. Coordinate shared tests and integrations. Only the designated lead may perform an authorized production transition. Do not let parallel workers independently restart services, submit OCI jobs, or alter exchange state.
Reuse existing modules and deployment mechanisms where sound. Avoid introducing a second framework, database, or execution gateway just to match illustrative names in this brief.
5. Architecture contract
5.1 Components and authority
Windows primary: produces strategy decisions, maintains local telemetry, and requests execution while authorized.
OCI standby: runs a ready replica, reads exchange state independently, and remains passive until a controlled promotion.
Execution gateway: holds the trade-capable exchange credential and is the sole path for exchange mutations. The gateway validates authority, risk policy, command identity, and durable journaling.
Authority store: durably records the active owner, monotonically increasing epoch, lease state, and transition history with the consistency required to reject competing leaders.
Exchange: supplies authoritative order, fill, and balance observations. Local journals supply intent and recovery context.
An epoch is a leadership generation number. Fencing means preventing a former leader from issuing valid new commands. Neither a database flag nor a lost heartbeat is fencing unless the final execution path enforces it.
Define an architecture decision record before implementation: where the gateway and authority store run, who can sign exchange requests, how credentials are isolated, how state survives restart, and which failures stop new trading.
For an initial small deployment, one gateway on the OCI VM can simplify authority, but makes that VM a dependency of the Windows trader. Record that limitation plainly. An independent gateway is a separate deployment and cost decision. Do not claim gateway high availability from two uncoordinated copies.
5.2 Gateway enforcement
Authenticate the caller and validate its current owner/epoch at final command admission.
Serialize authority transitions and command dispatch so a stale command cannot pass an earlier check and dispatch after revocation.
Revalidate queued commands before dispatch. Never replay expired-epoch commands after restart.
Apply the same enforcement to cancellations, amendments, bulk endpoints, rearming, and emergency operations.
Persist the intent, parameters, unique ID, epoch, and dispatch state before sending.
Refuse new mutations if required durable storage or authority verification fails.
Record acknowledgments and unknown outcomes. Resolve uncertainty before creating dependent commands.
At the controlled gateway cutover, remove or revoke bypass trade credentials from strategy hosts. Prepare and test that transition first; do not revoke the running primary's credential during the preliminary audit. Network restrictions alone are not proof that a credential bypass is impossible.
Do not assume the exchange accepts application-specific fencing tokens or deduplicates identical client IDs. Verify the actual API contract and keep an application journal regardless. The Crypto.com API references should be checked for the exact API surface deployed. [S4]
5.3 Failover sequence and in-flight requests
Implement durable transitions:
PASSIVE -> SUSPECT -> VERIFY -> FENCE -> DRAIN_AND_RECONCILE -> RISK_CHECK -> PROMOTE -> ACTIVE
Any failed prerequisite leads to SAFE_HALT or MANUAL_REVIEW.
Detect missing/stale primary health using authenticated reports and independent observations.
Stop admitting new primary commands at the gateway and establish the authority boundary.
Reject queued commands from the former epoch.
Account for every command already dispatched. A request can reach the exchange even if its response never arrives.
Resolve pending and uncertain commands against exchange records. Include partial fills and activity occurring during the handoff.
Re-read balances, orders, fills, and available quantities until the chosen consistency checks pass; a single stale snapshot is insufficient.
Verify exposure, reserves, fee inputs, instrument precision, fresh market data, and watchdog health.
Acquire/confirm the exclusive standby authority under the serialized transition protocol, then enable fresh commands.
Keep the recovered Windows host passive. Failback is a deliberate handoff using the same barriers.
Manual approval cannot bypass technical gates. If in-flight outcomes cannot be established, promotion remains blocked even when the operator approved takeover.
The original 15/45/60-second heartbeat thresholds are initial diagnostic settings, not a guarantee of safe promotion time. Lease expiry must be evaluated by the authoritative service; do not decide leadership solely by comparing wall-clock timestamps from two hosts. Use monotonic elapsed time where appropriate and detect significant clock changes.
5.4 Durability and replication
Define the authoritative execution journal and its durability boundary before choosing a datastore.
Record each intent before network submission, then append its acknowledgment, rejection, unknown outcome, fills, and reconciliation decisions.
Retain string-safe order identifiers and decimal-safe quantities/prices; avoid floating-point rounding in order accounting.
Deduplicate fill application by verified exchange identity and handle partial fills.
Track a durable journal position and replication lag. Do not claim zero data loss from asynchronous replication.
Replicate consistent snapshots using the datastore's supported backup/checkpoint method. Do not copy an actively written database file blindly.
Rebuild from the journal and exchange observations; do not replay cached trading commands.
If necessary history is missing, block promotion until reconciliation resolves it.
Set and measure recovery time and recovery point objectives. Leave them marked NOT_MEASURED until tested.
6. OCI claimer implementation requirements
The supplied script is a starting point for inspection, not a tested provisioning controller.
6.1 Findings to verify and correct
Supplied-code behavior
Required correction
Direct launches followed by Resource Manager APPLY
Use Resource Manager as the sole normal provisioning authority.
Any nonterminated VM counts as success
Match the intended managed resource ID/association, compartment, and expected configuration.
Failed listing becomes an empty list
Return an explicit unknown/error state and block provisioning.
Only first list page inspected
Retrieve every relevant page, including empty pages with continuation tokens.
Response headers discarded
Return status, parsed body, relevant headers, and request correlation metadata.
No durable retry identity
Journal the intended operation and supported retry token before submission.
Job polling ignores HTTP status
Treat failed/malformed polling as unresolved; never infer terminal state from missing JSON fields.
All config profiles merged
Select one profile explicitly; validate required fields and paths.
Config reloaded separately in inspection
Use one validated configuration snapshot per decision cycle.
Chicago resource constants mixed with configurable region
Reject mismatched region, stack, subnet, image, compartment, or AD configuration.
Retry timer resets on daemon restart
Persist and enforce the next permitted attempt time.
Log failures swallowed; JSON overwritten in place
Surface audit-write failures and replace status atomically.
The supplied OPENSSL_EXE constant is unused. The custom signer was not included. Do not label authentication “verified OpenSSL” or universally “WDAC-safe.” Inspect the actual dependency and executable policy behavior without disabling Windows protection.
6.2 One provisioning authority and exact ownership
Remove the independent direct LaunchInstance path from automatic claiming.
Inspect the existing stack configuration and Terraform state before changing it.
Identify any VM already created outside Resource Manager. Do not silently import, adopt, delete, or recreate it.
Treat tags and display names as supporting metadata, not unique proof of ownership.
Inspect all relevant stack jobs and resource associations. Unknown or nonterminal job state blocks a new APPLY.
After a failed job, inspect resources and state for partial success before considering another attempt.
A local process lock protects one host only. Keep the controller on one designated host, or implement coordination that also excludes a second controller elsewhere.
Prevent the master supervisor from treating completed provisioning as a crash and repeatedly relaunching claim attempts.
6.3 Review the actual infrastructure change
Resource Manager-only operation does not make every APPLY safe. An APPLY can modify or replace existing infrastructure.
Prepare a plan tied to the exact stack configuration, variables, and intended resource set. Validate that it contains no unapproved deletion, replacement, additional instance, broader network access, or paid substitute. Use the supported reviewed-plan workflow or an explicitly documented immutable configuration policy. Re-plan when configuration, state, or relevant assumptions change.
Submitting a Resource Manager PLAN is itself a cloud job; distinguish it from a local dry run. Run it only within the established OCI authorization.
6.4 HTTP, signing, and configuration
The HTTP layer must preserve pagination, request identity, and retry metadata. Follow continuation headers until the list is complete; an empty page alone is not the end. OCI documents these behaviors in its REST API guidance. [S1]
Inspect the signing dependency with disposable test keys. Check the exact encoded request target, signed body bytes, header/body consistency, key format support, and supported profile handling. Keep TLS verification enabled. Use current Oracle documentation as the API contract; do not invent SDK behavior.
If a safe supported SDK fits the host, reuse it. If policy prevents it, validate the existing compatible adapter instead of weakening application-control rules. Do not print key contents or full authorization headers.
6.5 Durable operation identity and uncertain responses
Before any create-job request:
Persist deployment ID, stack ID, immutable configuration/plan identity, request-body hash, operation ID, retry token, and creation time.
Submit the request.
Persist the returned job ID and request ID before progressing.
On timeout or connection loss, record SUBMISSION_UNKNOWN and reconcile before any fresh operation.
Oracle's create_job supports opc_retry_token. The documented token lifetime is 24 hours and it can be invalidated earlier. Reuse the same token only for the same intended request within the supported contract; an expired token does not establish whether the original operation succeeded. [S2]
Do not mint a new identity merely because a response was lost. Use an operation marker and returned IDs for reconciliation, but do not treat a display-name match alone as a transactional guarantee.
Bound each polling pass. A polling deadline ends observation, not the cloud job. Retain unresolved state and return to monitoring; do not automatically cancel, force-unlock, or launch another APPLY.
6.6 Preserve the 20-minute capacity policy
Keep POLL_INTERVAL_SECONDS = 1200 as the minimum wait after a completed failed capacity attempt before starting a new capacity-attempt mutation. Preserve this schedule across restart.
A still-running or uncertain job never becomes eligible merely because 20 minutes elapsed.
Read-only job monitoring can occur more frequently with its own timeout/backoff.
Backoff and positive jitter can lengthen the wait; neither may shorten the 1,200-second minimum.
Honor valid server retry guidance where present. Persist next_attempt_not_before_utc and reconcile on startup.
If timekeeping is suspect, delay and reconcile; do not make an immediate catch-up burst.
Do not log every failure as “capacity saturated.” Distinguish capacity, rate limit, quota, auth, invalid configuration, transport failure, and unknown result.
No claim that a 20-minute cadence eliminates every possible 429.
Suggested decision outcomes:
Observation
Controller action
Exact target already exists
Verify it; do not create a replacement automatically
Duplicate target candidates
Halt new provisioning and report evidence
Incomplete/failed inspection
Unknown state; no mutation
Active or uncertain job
Monitor and reconcile
Confirmed capacity failure
Wait under the persisted 20-minute policy
Authentication, permission, quota, or configuration error
Block new APPLY until corrected
Rate limit/transient read failure
Bounded read retry/backoff; no fresh provisioning while state is unknown
Successful APPLY
Verify intended resources and readiness; enter monitoring
Lost VM after prior success
Report outage and prepare a recovery plan; no blind reprovisioning
6.7 Cost and readiness checks
Record exact approved shape, count, storage, network services, compartment, region, and paid-spend policy. Check current account eligibility rather than copying historical Always Free allowances.
OCI budgets provide soft spending limits and alerts; they are not a provisioning hard cap. Combine a narrow resource allowlist, reviewed plans, applicable quotas/IAM restrictions, and usage monitoring. Do not promise a guaranteed bill ceiling. [S3]
A successful job and a running VM are separate from standby readiness. Verify OS/bootstrap success, private access, service identity, correct build, read-only exchange inspection, journal recovery, backups, and inability to mutate while passive. Keep provisioning status and application readiness separate.
7. Implementation phases and acceptance gates
Phase 0 — Establish the baseline and rollback boundary
Do:
Read applicable project instructions and the original specification.
Locate actual source, tests, configuration, service launchers, and current deployment state.
Record a nonsecret baseline: host, build, processes, service modes, file hashes, and available observation access.
Inspect live order/account state only through authorized read-only access. If unavailable, mark it NOT_VERIFIED.
Identify existing live credentials and mutation paths by capability, without exporting secrets.
Preserve relevant code/configuration and document how rollback would restore code without restoring stale live-trading authority.
Produce: Baseline, architecture decision record, phase tracker, risk register, and scoped change plan.
Gate: Target is unambiguous, work is isolated, and code/test work can proceed without an uncontrolled production effect. Missing live access blocks live claims, not offline development.
Phase 1 — Harden trading recovery in isolation
Do:
Implement or repair durable intents, reconciliation, fee/precision handling, reserve accounting recovery, and duplicate suppression.
Define the gateway/authority interface with production cutover disabled.
Ensure startup cannot enter live mode from stale cached state.
Integrate the watchdog and supervisor with explicit safe recovery modes.
Keep existing strategy and order-price decisions unchanged unless separately requested.
Gate: Offline scenarios for lost responses, partial fills, restart, and stale state pass; the tested implementation does not emit unauthorized or duplicated mutations.
Phase 2 — Correct the OCI controller
Do:
Implement Section 6 against the actual repository.
Add deterministic API fixtures, controllable time, restart persistence, and transport-failure tests.
Prepare the reviewed Resource Manager change and reconcile any preexisting resources.
Retain --check-only compatibility if already used, but make incomplete inspection observable and unsuccessful to automation.
Gate: Complete inspection, persisted retry identity, single controller, no ambiguous resubmission, and restart-safe cadence are demonstrated offline. Live provisioning remains a separate deployment result.
Phase 3 — Build the passive standby deployment
Do:
Prepare ARM64-compatible pinned dependencies, restricted service accounts, systemd units, private connectivity, and credential references.
Deploy only when that production action is authorized; otherwise complete the deployable package.
Keep GPU/Ollama, UI, and the Cloudflare tunnel outside the minimum trading-recovery dependencies.
Establish supported replication, independent market observation, health checks, backups, and restore procedures.
Configure alerts with approved recipients; delivery tests need authorization to send.
Gate: For an actual deployment, the standby can reconstruct state and observe the exchange, while mutation attempts are denied. If tested only in isolation, label the gate OFFLINE_PASS and live readiness NOT_VERIFIED.
Phase 4 — Implement and cut over the exclusive gateway
Do:
Implement Section 5's admission control, journaling, serialized authority changes, stale-queue rejection, and recovery barrier.
Test conflicting leaders and gateway/datastore restarts.
Prepare a controlled primary cutover, including bypass credential removal and preservation of resting orders.
Apply it only within production authorization and after required tests pass.
Gate: Stale owners and passive replicas cannot submit mutations, including during simulated partitions. An unknown in-flight outcome blocks promotion. Live enforcement requires deployment evidence.
Phase 5 — Drill, measure, and release
Do:
Run the fault matrix in an isolated environment first.
Measure recovery time, replication lag, journal loss boundaries, and alert delivery.
Prepare a manual promotion/failback runbook with authenticated, auditable actions.
Keep automatic promotion disabled for the first rollout.
Propose automatic promotion only after all relevant tests pass and its activation is authorized.
Gate: The reviewer accepts the evidence for the tested revision. Any untested production prerequisite remains explicitly open.
Phases 1 and 2 may proceed in parallel after Phase 0. Phase 3 stays passive. No live promotion is eligible before Phase 4's authority enforcement and Phase 5's relevant drills succeed.
8. Required fault-test matrix
Use mocks, recorded sanitized fixtures, disposable local resources, and an exchange test environment only if its availability and suitability are confirmed. Do not use small real-money trades as an implicit test method.
ID
Scenario
Required observable result
HA-01
Primary returns with old epoch
New mutations rejected; host remains passive
HA-02
Old command waits in a queue during promotion
Rejected before dispatch
HA-03
Exchange accepts request but response is lost
Intent stays unresolved; no blind resubmission or promotion
HA-04
Partial fill occurs during handoff
Quantity/reserve accounting reconciles correctly
HA-05
Gateway/authority store restarts mid-request
Durable intent recovered; uncertain outcomes block new work
HA-06
Lease unavailable or clocks jump
No independent self-promotion
HA-07
Journal becomes unwritable or replica is stale
No unjournaled mutation; readiness degrades
HA-08
Passive host tries create/amend/cancel/bulk calls
Every mutation path denied
OCI-01
Target appears on a later or empty-followed-by-nonempty page
Complete inspection finds it; no extra VM request
OCI-02
Listing returns 401/403/429/5xx or malformed JSON
Unknown/error state, never “no instances”
OCI-03
CreateJob succeeds but response is lost
Persisted operation reconciled; no fresh identity blindly sent
OCI-04
Previous APPLY partially succeeds or is still unresolved
No independent direct launch or replacement APPLY
OCI-05
Two controller processes start
One designated mutation owner; other exits/waits safely
OCI-06
Controller restarts before retry is due
Original minimum delay remains enforced
OCI-07
Unknown job state or failed GetJob call
Job remains unresolved
OCI-08
Wrong profile, region mismatch, unexpected plan/cost
Provisioning blocked
OPS-01
Primary reboot or cloud/network outage
Expected safe recovery; no stale live role restored
OPS-02
Status writes fail or alert delivery fails
Failure visible; no false healthy result
OPS-03
Restore a backup into a disposable environment
State validated; no automatic live activation
For each test record the code revision, fixture/seed where relevant, command, expected assertions, observed result, and evidence path. A large test count alone is not acceptance evidence. Once these concrete risks are sufficiently checked, stop optional test expansion.
9. Health, security, and runbooks
Publish separate health dimensions: process alive, heartbeat age, exchange read access, market-data freshness, journal durability, replica lag, current authority, and application readiness.
Suggested nonsecret fields:
checked_utc, host_id, build_revision, role, authority_epoch, lease_status, last_exchange_reconcile_utc, journal_position, replication_lag_seconds, unresolved_intent_count, risk_state, provisioning_state, active_job_id, next_attempt_not_before_utc, last_verified_restore_utc, alerts.
Do not silently suppress logging or status failures.
Use atomic state replacement and durable transactional journal writes for their distinct purposes.
Keep management APIs and databases private. Preserve least privilege and withdrawal-disabled trading credentials.
Verify egress/IP allowlist behavior for both roles; do not solve changing residential IPs by broadly disabling restrictions.
Audit Windows security posture and prepare targeted remediation. Do not disable Defender, WDAC, Smart App Control, or TLS verification to pass tests.
Use log rotation and sanitized diagnostics; exclude secrets from code, prompts, snapshots, and evidence bundles.
Document gateway loss, exchange outage, failed reconciliation, corrupted state, stopped VM, and failed alert delivery.
Rollback requirements
Each production change needs a specific rollback with prerequisites and consequences. Restoring old code or a disk snapshot does not restore permission to trade. After rollback, start passive, read current exchange state, and obtain current authority.
Do not automatically recreate canceled orders, reuse old epochs, restore stale credentials, destroy cloud resources, or roll back Terraform state as a shortcut. Preserve evidence and use the documented recovery path.
10. Deliverables and status reporting
Use these names unless the project already has equivalent files. They are proposed outputs, not claims that files already exist:
Deliverable
Suggested location under verified project root
Execution brief
docs/AI-BS_Oracle_Hot_Standby_Agent_Execution_Prompt.md
Baseline
docs/ha/BASELINE.md
Architecture decision
docs/ha/ARCHITECTURE_DECISION.md
Phase tracker
docs/ha/IMPLEMENTATION_STATUS.md
Test evidence
docs/ha/TEST_EVIDENCE.md
Operator runbook
docs/ha/FAILOVER_RUNBOOK.md
Deployment and rollback
docs/ha/DEPLOYMENT_AND_ROLLBACK.md
Release assessment
docs/ha/FINAL_REPORT.md
Use only states backed by evidence: NOT_STARTED, IN_PROGRESS, IMPLEMENTED, OFFLINE_PASS, DEPLOYED, LIVE_VERIFIED, BLOCKED, FAILED. Track code/tests/deployment separately so “implemented” never implies live readiness.
At each phase boundary report:
Phase and status:
Verified host/project/revision:
Changes and purpose:
Tests run and observed results:
Production actions actually taken:
Live order/OCI observations, or NOT_VERIFIED:
Rollback readiness:
Open risks or blocker:
Next authorized action:
For a blocked step, record the two failed attempts where applicable, the actual error with secrets removed, impact, and the smallest required decision. Continue independent authorized work. Never conceal an approval rejection or permission failure by changing the route.
11. Release checklist
[ ]
Actual code/configuration reviewed and changes traceable to a revision.
[ ]
Strategy behavior preserved or separately authorized changes documented.
[ ]
Sole execution path and no credential bypass demonstrated.
[ ]
In-flight request barrier, recovery journal, and stale-epoch rejection tested.
[ ]
Complete OCI inspection and one provisioning authority demonstrated.
[ ]
Twenty-minute retry policy survives restart.
[ ]
Approved resource plan and cost assumptions documented.
[ ]
Passive standby cannot mutate the exchange.
[ ]
Backup restore and rollback runbooks tested in isolation.
[ ]
Relevant fault tests passed; unresolved cases listed.
[ ]
Deployment actions recorded separately from simulations.
[ ]
Manual promotion retained until automatic promotion is tested and authorized.
[ ]
Live readiness marked only where fresh evidence exists.
Do not mark the project complete merely because the VM exists or all processes are running.
12. Reference notes for implementation
Checked November 19, 2026. Recheck the exact APIs and installed versions when implementing.
[S1] Oracle OCI REST API guidance: pagination, request/response metadata, throttling, and retry concepts. Official documentation.
[S2] Oracle ResourceManagerClient: current create_job parameters and retry-token contract. Official documentation.
[S3] Oracle Budgets: spending limits and alert semantics. Official documentation.
[S4] Crypto.com Exchange API: verify the active endpoint family, order identifiers, acknowledgment behavior, queries, permissions, and limits against the deployment's actual API. Official API entry point.
Project source: the original hot-standby implementation specification and the OCI script supplied in conversation. Their historical operational claims are not live evidence.
The architecture rules and gates above are project requirements and engineering recommendations. They are not provider guarantees.
Execution directive: Start Phase 0 in the authorized AI-BS environment, complete all available safe work, preserve evidence, and report the next concrete action. Never infer live trading authority from this document.
