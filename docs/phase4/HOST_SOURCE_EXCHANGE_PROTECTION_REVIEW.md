# AI-BS host source and exchange root protection review

The current source and exchange components do not yet establish a trusted execution controller. This review proposes a protected deployment layout and explicit root-admission policy. Admission, execution and apply remain disabled. No permissions, accounts, services, VM settings or control sources were changed.

Record117, October26 2026. Host metadata was measured around 01:00 America/New_York (05:00 UTC). The VM proposal was relayed by the operator through Kief; it is proposal evidence, not evidence that the proposed setup exists.

## Findings from current host metadata and source

| Finding | Evidence | Required resolution |
| --- | --- | --- |
| Source trees are writable by broad identities | C:\AI-BS, isolated_workers, connector and protocol inherit Authenticated Users Modify. The staging Python source has the same grant. Reviewed source hashes still match. | Use a separately protected deployment tree with reviewed ownership, ancestors and importable content. Preserve the working checkout and existing ACLs. |
| Source pins do not cover every possible loaded object | Start-PairedConnector.ps1:5–25 pins and locks nine files until launcher completion. run_paired.py:3–6 imports before its consistency loop at11–13 and inserts the repository root into sys.path. Package initializer files are absent, not pinned. Connector/protocol caches exist with5/4pyc entries and broad Modify grants. | Verify the entire approved load path before imports, including executable, dependencies, initializers, cache/native libraries and configuration. Do not rely on source hashes alone to attest loaded code. No cache contents or tampering were tested. |
| Interpreter selection is not policy-pinned | Start-PairedConnector.ps1:54 resolves python.exe through PATH. It currently resolves to Python312\python.exe, file version3.12.10, valid Python Software Foundation signature, SHA2564d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a. Its file/directory ACLs include an additional capability SID with FullControl. | Select a supported, reviewed absolute runtime/dependency distribution and trusted writer set. Current valid signature/hash is metadata, not approval of the version or all writers. No Python version command or project import was run. |
| Private connector leaf is restricted, but ancestors need review | Existing paired private leaf has protected inheritance, operator ownership and only operator/SYSTEM/Administrators FullControl. Its parent admits another capability SID with FullControl. | Verify ancestors, delete/rename rights and stable object identity; do not treat the leaf ACL alone as full path protection. Do not reuse key/replay storage as a file-exchange root. |
| File helpers enforce structure rather than authorization | coding_vm_staging.py:3–6,90 assumes trusted admission and suitable root ACLs. ExchangeFiles.cs:70–97 pins a caller-supplied NTFS root identity and allowlist, without establishing account/owner/DACL policy. | A host broker must establish caller/token/owner/root authorization before invoking either helper. Calling Describe on an arbitrary root is not authorization. |
| Contract and primitive differ | Existing VM contract allows20files,2MiB/file,16MiB total and240-character relative paths including valid Unicode/dotfiles. Protocol/file primitive use1MiB/file; protocol8MiB total,64entries and192-character restricted paths. | Define and verify an adapter preserving the existing contract. Neither silently lower bounds nor raise helper constants without reviewing streaming/wire allocation and path handling. |
| End-to-end delivery remains absent | Search of backend core/routers and connector/protocol sources found no production stage_vm_inputs call or ExchangeRoot.Open integration. Shared low-level staging helpers are reused by preparation/snapshot code. | Add authenticated admission, protected materialization, durable delivery receipts, exact attempt binding and interruption recovery before claiming accepted file exchange. Do not alter the shared helpers casually. |

Windows deletion/rename checks can depend on a parent delete-child grant, so checking only the leaf ACL is insufficient for path protection. This is a policy inference from the observed ACLs, not an attempted replacement. [Microsoft DeleteFile documentation](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-deletefilew)

Python isolated mode removes several ambient import influences, while -B only suppresses bytecode writes and hash-based cache options do not change timestamp-based cache semantics. These options do not replace a protected, fully reviewed load tree; the existing code also explicitly reinserts the repository path. [Python command-line documentation](https://docs.python.org/3.12/using/cmdline.html)

## Proposed host layout and access policy

The following paths are proposed, not created. C:\ProgramData\AI-BS-WorkerControl did not exist when inspected. Its parent has ordinary Users write/create grants, so trusted creation, ownership and exact child identity must be verified before use; the parent is not presumed approved merely by its name.

Keep existing C:\AI-BS source and all existing permissions unchanged. Provision a fresh deployment tree only after a concrete approval. Resolve principals to exact SIDs and inspect effective groups/privileges. The normal gateway companion principal, host hypervisor worker and guest task account are distinct roles; do not silently merge them or grant the guest task host access.

| Proposed child of C:\ProgramData\AI-BS-WorkerControl | Trusted writer | Runtime reader/writer | Task access |
| --- | --- | --- | --- |
| releases/<manifest SHA>/controller and runtime | Reviewed deployer/SYSTEM; Administrators remain trusted | Exact approved host controller/worker RX only | No host access |
| policy | Reviewed deployer/SYSTEM | Controllers read approved policy | None |
| state/<controller identity> | Its exact controller, within provisioned state root | Only that controller writes lease/replay/state | None |
| exchange/<task>/<attempt>/sealed_inputs | Broker publishes approved bytes, then seals | Exact delivery role reads only | No direct host access; guest receives copies |
| exchange/<task>/<attempt>/incoming_outputs | Exact collector for this attempt | Broker validates bounded untrusted bytes | No direct host access |
| receipts and retained evidence | Broker only | Read access separately scoped | None |
| dedicated identity material | Exact control-plane principal in separate private storage | Never task-readable or co-mingled with payloads | None |

Protected code/policy roots must not grant runtime workers or broad users write, delete, ownership or DACL rights. State/output writers must not be able to replace code/policy roots or alter trusted receipts. Check all relevant ancestors and object identities. No broad recursive ACL change to the checkout, profile or existing runtime is proposed.

## Proposed implementation gates

1. Deploy approved immutable code/runtime/dependencies to a new protected tree. Require exact interpreter path/hash/signer/version policy, a controlled working directory and environment, and only protected import/cache/native-library paths. Complete validation before imports and hold verified identities through loading. Direct invocation that bypasses the reviewed launcher must not claim admission.
2. Introduce a broker-owned root registry binding purpose, owner, allowed SIDs, DACL policy, volume/file identity and allowed attempt paths. Reject project/original/private-store/model roots and unregistered caller-selected roots. Validate policy on held objects, not only lexical path strings.
3. Bind authenticated owner/repository/commit/authorization reference, exact selected byte set, immutable roles, base-image identity and fresh attempt to delivery policy. Preserve the existing schemas and bounds. Render returned bytes as data; never accept a guest-selected host destination or success flag as a seal.
4. Specify a bounded offline transfer format/parser before implementation. Do not mount untrusted guest filesystems into a privileged host workflow. Separate disposable execution transport from the networked integration channel; do not weaken the offline containment contract to reuse connectivity.
5. Persist attempt intent before consequential operations and completion receipts only after flush/hash/object-identity checks. Identical duplicate delivery may return the same retained receipt; conflicting reuse fails. A nonce claim is not a delivery receipt. Preserve partial attempts; never automatically replay uncertain execution or apply.

These are proposals only. Root provisioning or permission changes need their own exact approval; this review does not register a broker, admit a worker or enable execution.

## Review of the VM proposal

The proposal correctly preserves the signed-in integration guest, requires a clean independently built execution image, excludes integration credentials and retains all14actualcontainment cases as NOT RUN. Its host/guest root separation and quarantine requirements align with the retained contract.

Resolve these items before approving implementation:

- Supply the exact proposed guest account, allowed groups and privileges, controller/task identities, child path/owner/access matrix, inheritance rules and protected ancestors. A separate standard account alone is insufficient.
- Replace separate1MiBstdout and1MiBstderr allowances with the existing combined ceiling: default262144bytes and maximum1048576bytes across both streams. Do not double the contract.
- Treat2vCPUs as a new unaccepted profile proposal because the existing offline inspector pins4. Specify a VM RAM bound separately from the proposed512MiBaggregate task-job bound. Clarify CPU-rate semantics and process-count enforcement. Small canary limits do not establish React/coordinated workload capability.
- Specify the restricted noninteractive launch mechanism and its exact rights, without elevated runtime fallback, embedded credentials or automatic service/batch-right grants.
- Resolve the exact offline transfer writer/reader and untrusted-image parsing boundary. While-stopped attachment is necessary to the proposal, not proof that its host parser is safe.
- Map future evidence to the retained14cases in ISOLATED_WORKER_CONTRACT.md:49–64. Preserve normal fixed Python verification, host canaries, network/device/secret denial, path/output limits, child cancellation, interruptions, stale tests/proposals and failed-shutdown quarantine. No case has been run by this review.

## Next bounded step

Through the operator's Kief relay, obtain the completed guest permission/identity matrix and answers to the limit/launcher/transfer gaps. Combine them with this host policy into one concrete implementation proposal. Keep admission/execution/apply false and windows_vm unavailable until actual acceptance. Host apply remains a separate reviewed gate after the Phase4/5 evidence.

Evidence and full source hashes are retained under backups/host_source_exchange_review_20261026_record117. Only metadata, selected source files and documentation were read/written; no credentials/private keys, originals, private databases or models were opened. No canary/access attempt, source import, compilation, harness, port request, VM command or permission change was performed.


## Record118 authorized setup result
The operator authorized scoped permissions and controlled verification. Eight new protected roots and eight review-package files were created/read back; existing permissions remained unchanged. The source review package README and latest handoff describe current status; the protected v1 snapshot is retained without overwrite. No runtime/connector/guest executor was started and no VM containment case passed. Private cloud handoff: https://chatgpt.com/space/page_0c34c8baf1108191b9757b3df8b0f9d8 . Host text archive: https://drive.google.com/file/d/1CdthiaV8syZu53h0ba_L1NiQOKKxwxf0/view?usp=drivesdk . Guest archive/access remain pending.


## Record119: effective-access diagnostic still pending
Only the standard host worker batch-logon right was granted. Cross-account password-free S4U registration failed before creation. A disabled same-account registration helper and fixed seven-case native-access diagnostic are protected and hash-checked, but neither worker registration nor those access cases ran. Preserve the signed-in integration VM; the protected-root ACL metadata is still not behavioral worker denial. See backups/standard_worker_prerequisites_20261026_record119/NEXT_HOST_WORKER_STEP.md.
