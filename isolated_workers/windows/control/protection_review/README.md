# Host protection review candidate

The operator authorized scoped permission changes after the initial review. Record118 created eight protected directories and staged eight review-package files. Owner/DACL and file-hash readback passed; existing checkout/profile permissions were preserved. No runtime, connector, guest task or admission/execution/apply provider was activated. Existing launchers and backend routes do not import the review checker.

The protected review_candidate copy is a retained v1 snapshot from provisioning. This source README was subsequently updated to record the result; the protected snapshot and its original receipt were not overwritten.

## Files and scope

- `policy.review.json` identifies proposed host roots, exact existing host principal SIDs and observed file hashes. It is an incomplete review template, not an approved deployment manifest. Its Python hash describes the observed file; it does not approve that runtime version. The final distribution must add every approved runtime/dependency/cache/native-library component and use reviewed import layout.
- `review_policy.py` performs pure validation of supplied review data, with no filesystem, socket, process or permission operations. It flags missing paths, unexpected writers/owners, unprotected DACLs, unsupported ACE forms, changed hashes and runtime signature mismatches. It always returns false authority flags and outstanding native checks. Supplied JSON is not OS-attested evidence.
- `Collect-ProtectionReview.ps1` is a prepared metadata-only collector for the fixed proposed roots and listed deployment files. It has no apply/start switch. It returns JSON to stdout, skips detected reparse paths and leaves held-object/effective-access/dependency checks unverified. It has not been run against the host. It is not a replacement-resistant security boundary or a provisioning tool.
- `test_review_policy.py` uses synthetic records only. Passing these cases proves the specified review behavior, not actual ACL denial, safe loaded code or VM containment.
- `AtomicDirectory.cs` creates only new directories within the fixed protection tree or retained fixture namespace, supplying the final security descriptor at creation. Existing targets are refused. `Test-AtomicDirectory.ps1` passed four native creation checks with retained fixtures; these are not VM containment cases.
- `Provision-HostProtectionRoot.ps1 -Provision` was run once under the exact authenticated x64 administrator provisioner after operator authorization. It created fresh roots, verified exact ACL readback and staged the review package with exclusive writes/hash readback. It refuses an existing target and must not be rerun to adopt or repair it. No existing-directory ACL update operation is included.

## Concrete proposed permission changes

Record118 provisioned `C:\ProgramData\AI-BS-WorkerControl` and its deployment, policy, state, sealed-input, incoming-output, receipt and review-candidate directories. Existing checkout/profile/runtime permissions were preserved. The provisioner supplies the final descriptor at creation, refuses existing targets and retains action intents/results. Readback is evidence of configured permissions; standard-worker behavioral denial and held-object/native broker admission remain unverified.

Owner for protected roots: Administrators (`S-1-5-32-544`), with protected inheritance. SYSTEM and Administrators remain trusted FullControl writers. The proposed normal gateway companion SID ends1001; the separate host VM-worker SID ends1005. They are not the guest task account; actual tokens, nested groups and privileges remain native acceptance prerequisites.

| Proposed root | Additional reader | Additional writer |
| --- | --- | --- |
| deployment | Exact controller and host VM worker RX | None |
| state | Exact controller | Exact controller Modify |
| sealed_inputs | Exact delivery worker read | Broker/controller publishes, then seals each attempt |
| incoming_outputs | Broker/controller reads bounded bytes | Exact controller and delivery worker, scoped per attempt |
| receipts | Separately approved reader | Broker/controller only |

This table is proposed policy, not an applied DACL. Protected subtree roots must resist replacement; task-created descendants require separate effective OWNER RIGHTS/inheritance/privilege validation. The pure checker does not interpret generic/conditional/deny ACE semantics as safe: it reports unsupported ACEs for native review. The controller's publish permission on the input container is not proof that per-attempt input bytes are sealed.

## Required native implementation before approval

The review checker is deliberately unable to issue authorization. A later authenticated broker must verify actual caller token/privileges, exact owner/DACL policy, all relevant ancestor/delete-child rights, held volume/file identity, regular-file/hardlink exclusion, and a complete protected load tree. Runtime/collector code must execute from reviewed protected storage rather than trust this writable checkout automatically. Effective-access and source-replacement tests remain unrun.

Keep source/control-plane state, sealed inputs, output quarantine and durable receipts separate. Preserve the original20files/2MiBper-file/16MiBtotal contract and Unicode/dotfile paths. The narrower protocol/file primitive is not changed by this package. No transport, credential store, guest service or raw-device access is implemented.

## Revised guest proposal assessment

The relayed revision correctly treats OWNER RIGHTS, explicit SID-based DACLs, token privileges, independent clean media and protected ancestors as requirements. Its LogonUserW/LOGON32_LOGON_BATCH/CreateProcessAsUserW service sequence is a candidate requiring credential lifecycle, privileges and launcher review. Its filesystem-free fixed-size VHD/application container is a candidate; exact device access, hypervisor/parser behavior and bounded collection remain unresolved. Neither mechanism is approved or implemented here.

The pasted revision still supplies no actual account/path matrix or explicit corrected numeric limit table. Retain the combined stdout/stderr default256KiB/maximum1MiB and treat any CPU/RAM/process limits as unaccepted canary proposals. The full fourteen-case contract remains in `docs/phase4/ISOLATED_WORKER_CONTRACT.md`. No case is replaced or completed by these policy tests.

## Review and activation boundaries

The scoped host-root provisioning authorization has been used. Remaining account/right/service/VM changes and real acceptance tests must follow the operator's authorization and the concrete reviewed design; the guest service/raw-device candidates remain unresolved. Keep `windows_vm` unavailable until actual acceptance. Host apply/rollback and later Phase5/6 acceptance remain separate gates.
