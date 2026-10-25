# Guarded guest provisioning media

October 24, 2026. This is a reviewed infrastructure candidate and verified media artifact. It has not been executed successfully in the guest and does not complete Phase 4.

The separate v2 ISO is staged at `C:\AI-BS\isolated_workers\windows\media\guarded_provisioning_v2_20261024\AIBS_Windows_Guest_Provisioning_v2.iso`.

| Property | Verified evidence |
| --- | --- |
| Length | 70,418,432 bytes |
| SHA-256 | `58d0224bb568169835d40963eed6de1761151f62bc249cc6020dd47424523ecf` |
| Optical volume name | Raw primary descriptor contains `AIBS_PROV` |
| Payloads | Exact 13-file set, independently parsed Joliet directory and complete byte comparison to retained stage |
| Worker file access | Dedicated worker SID has read/execute; no write; artifact folder grants only operator, SYSTEM, Administrators and worker |
| Mount/execution | Neither mounted nor executed; v1 remains attached to the guest |

The seven preserved v1 payloads are unchanged. Added payloads are the guest-only entrypoint, three reviewed helpers, provisioning guide and a manifest recording the other twelve files. There is no autorun payload. The v1 ISO and the other agent's installer were rehashed unchanged. The build used a retained copy of the reviewed native IMAPI2FS builder with exclusive output creation; its prefix-search verification was supplemented by the independent directory/extent/full-byte reader. No runtime installer was executed on the host.

Source lives in `isolated_workers/windows/guest`. The entrypoint rejects actual host/wrong-VM hardware identity and host account SID domain before importing helpers or writing. It requires elevation, a 64-bit process, no enabled guest adapters, the expected optical volume, pinned helper/package bytes and valid installer publishers. Fixed paths, exact versions/imports, offline exact wheel paths, bounded stdout/stderr and deadlines, immutable result records and nonzero failure/reboot handling remain separate from task admission.

An exclusive lease and durable attempt intent precede native steps. Any retained intent, including corrupt/partial JSON or one whose process has exited, blocks automatic replay. Retaining an intent after success also prevents accidental repeated provisioning. A reviewed recovery/maintenance transition is required for another attempt. Best-effort parent process termination cannot prove that Windows Installer service descendants stopped; uncertain attempts remain quarantined for inspection. No API grants a review/apply token or task authority.

Thirty-nine infrastructure cases pass in both Windows PowerShell 5.1 and PowerShell 7: 27 policy cases, four real bounded-process probes, three real host-refusal/parameter/orchestration checks and five real filesystem lease/replay cases. The additional state and orchestration tests first failed against absent behavior; failed and passing output is retained. Earlier passing tests for unchanged policy/process bytes remain applicable. These tests do not demonstrate positive guest CIM identity, successful guest installation, licensing, package compatibility, protected transport or any of the fourteen containment cases.

The candidate's Python destination is `C:\Program Files\AIBSPython313`. Reconcile any separately completed GUI installation's actual path and package state before adopting this candidate; do not create a duplicate runtime or silently call another executable through PATH. Existing user approval covers the pinned Node 24.22.1 and Python 3.13.17 guest installations. The Computer Use restrictions still require human handling of Windows authentication/security prompts and prohibit terminal UI automation.

The existing desktop shows an expired Windows license watermark. Legitimate activation/licensing evidence is required before task admission; no clock changes, snapshot/clone rotation or unapproved networking may substitute. Final guest control, credential exclusion and behavioral containment remain open. Evidence is recorded in `scratch/phase4_guest_media_v2_checkpoint.txt`.
