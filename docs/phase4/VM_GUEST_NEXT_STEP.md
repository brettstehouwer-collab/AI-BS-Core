# AI-BS VM guest diagnostic handoff

The metadata-only inventory was completed at 2026-10-26T04:51:21–04:51:23Z and relayed by the operator. Do not repeat it. The instructions below are retained as the scope of that completed diagnostic task; the results and next prerequisites appear at the end. Keep worker admission, execution and apply disabled.

## Completed communication checks

The paired client completed status, gateway_health and model_version. Gateway returned HTTP 200; model service returned HTTP 200 and version 0.40.9. Host evidence matched the upstream nonces and canonical request hashes. Successful receipts retain worker_admitted=false, execution_authorized=false, apply_authorized=false and execution verification not_run. The manually edited true-flags payload grants no authority.

Do not repeat these requests or restart the connector. No listener was observed on host port 18443 at 2026-10-26T04:40:19Z; this dated observation does not invalidate completed receipts or authorize a restart.

## Instructions for the VM agent

Use existing non-elevated Windows metadata commands, such as Get-FileHash, Get-Item, Get-Acl, whoami identity/group queries and local interface/route/listener metadata. Do not invoke project scripts or custom code.

1. Report the current guest account, process elevation, token integrity and Administrators membership, including deny-only membership. Non-elevation alone does not establish a standard account. Do not change accounts or privileges.
2. Locate the already-used client bundle within the known AI-BS-VM-Worker workspace or recorded bootstrap directory. Do not search the whole profile. Hash the existing files against the table below without invoking the wrapper, compiling C# or reusing a loaded client type. Report missing files or mismatches without downloading replacements.
3. Inspect ACL metadata only for the existing worker workspace and client bundle. Report the principals granted read, write and execute access. Do not open unrelated files, create canaries or test access. ACL metadata does not prove effective behavioral denial.
4. Report local interface, route and listener metadata without scanning ports or contacting endpoints. Redact MAC addresses, public addresses, SSIDs and unrelated endpoint details. Do not change networking.
5. Refer to the retained readiness report for runtime/licensing history. Do not rerun runtime, package or licensing commands. Mark measurements needing refresh as unknown. Do not open authentication material to inventory it.

| Existing client file | Expected SHA-256 |
| --- | --- |
| Invoke-GuestChannelStatus.ps1 | 0493c72cd23ab79ffe060589d41a2110f8d45b504ab5f4c0550755f0565ee84b |
| GuestStatusClient.cs | 1595c7b4b4d0e648e6144414b5164247a7d66a1d3697eec07e1c36d95960b53d |

The standalone wrapper lacks its own source-hash recheck and can reuse a loaded type. Retain the external bootstrap and host checks. Matching source bytes do not attest a loaded type, OS account or containment.

## Limits and acceptance

Do not read credentials, browser profiles, Codex authentication, private keys, secret environment values, personal databases, documents or model contents. Do not install software, change PATH/execution policy/firewall/ACLs, register tasks/services, alter VM settings or start/stop processes. Do not run project code, tests, harnesses, model inference or arbitrary shell payloads. Do not enable admission, execution or apply.

Return a sanitized table: item | observed evidence | passed/failed/unknown | remaining prerequisite. Include measured hashes and UTC time. Separate observations from assumptions and identify what cannot be established inside the guest. Stop after reporting.

Acceptance requires a complete bounded inventory, explicit unknowns and no authority/configuration changes. The report cannot establish host standard-worker rights, host filesystem denial or VM isolation. Host enforcement and all fourteen actual containment cases remain open.

## Later execution and application gates

Review an exact credential-separated disposable execution profile and synthetic test plan before candidate execution. Specify account/image, allowed paths/endpoints/executables, deadlines/output bounds, retained evidence and stop criteria. Metadata-only authorization does not authorize permission grants, task registration, network or VM changes. Any such change needs its own concrete review under the current hold.

Preserve the integration guest's gateway/model/internet/intranet role. Do not convert the signed-in integration guest into an accepted disposable task image. Applying changes remains separate and requires reviewed diffs, fresh original/proposal/test hashes, backups, verification seals, rollback evidence and explicit apply authority.


## Guest inventory received October 26 2026
The operator relayed the completed inventory measured 2026-10-26T04:51:21–04:51:23Z. The metadata inventory is complete; do not repeat it. Both copies of each client file match the expected hashes, also rechecked against host source. The guest token is medium integrity with deny-only Administrators membership: it is a filtered administrator account and fails the standard execution-account requirement. Preserve this signed-in integration guest.

Workspace/client ACLs reportedly grant the guest FullControl. Routes and local listener metadata establish neither enforced egress denial nor external exposure. Runtime/licensing entries remain historical. No source invocation, compilation, access tests, requests or guest writes were reported. Host enforcement, a credential-separated licensed standard execution image and all fourteen real containment cases remain open.

Next: review the separate disposable execution profile and host source/exchange-root protection; bring exact proposed operational changes back for approval. Do not create accounts, change permissions/settings, run a harness or enable execution/apply from this handoff. The host's sanitized engineering checkpoint may record these results under the existing documentation request; the guest diagnostic task itself remains no-write.
