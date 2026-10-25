# Windows desktop and offline provisioning review

October 24, 2026. Application source v5.329.48; plan 1.63. This records provisioning progress, not containment acceptance.

## Verified desktop and preservation

After the operator reported completing Windows installation, Codex inspected the existing worker-owned guest console. Windows reached its desktop. No account, password, security-question or consent input was automated. The desktop visibly reports **Windows License is expired**, with build `26100.ge_release.240331-1435`. Activation status, evaluation eligibility and remaining lifetime have not been independently queried inside the guest. Do not treat the filename of the installation ISO as proof of the installed guest build or entitlement.

Created the online snapshot `AIBS_Desktop_PreProvision_20261024`, UUID `dca55e17-086c-46f4-8cd9-aaf98154e2a5`, on the same VM `6c5a53da-ab80-4ecb-8be6-4059266f736e`. The completed snapshot has state file `Snapshots/2026-10-24T17-28-04-378390900Z.sav` (3,394,215,059 bytes). The active child disk is now `7dd3e9fa-d52e-4e63-b9b8-4fa5663ffe84`. Prior disks and snapshots remain preserved. This snapshot preserves an expired-watermark desktop; restoring it does not establish valid licensing or extend evaluation rights.

The previous recovery/setup guards pin older disk, snapshot and DVD identities. They must fail closed against this changed configuration. Do not replay them or loosen their checks to accommodate arbitrary identities. A reviewed transition must validate the actual current graph before any future controller use.

## Offline ISO attached

Rehashed `C:\AI-BS\saved_data\phase4_offline_media\AIBS_Windows_Guest_Provisioning_v1.iso`: 70,387,712 bytes, SHA-256 `50f4ac4e873bdeaf088b7ae57160cb438f08269f401d811f84053f3a725a33f0`, matching the earlier independent seven-payload sector readback.

Attached this existing ISO through the worker-owned VirtualBox console optical-drive picker. Current DVD UUID is `0b72ff83-f6d1-4b14-81d7-c637268365b1`. The persisted configuration names the exact ISO, and the live VirtualBox log records that exact path with `ReadOnly = 1`, `Type = DVD`, followed by `RUNNING`. No host directory was shared. Current persisted hardware has zero enabled network adapters and zero shared folders; clipboard remains its disabled/default configuration. These are configuration observations, not behavioral containment results.

## Installer source review

The agent's separate `saved_data/phase4_offline_media/Install-GuestProvisioningPackage.ps1` has SHA-256 `4be5cb8433931ca4c32d5342951377b431b409b2ee791b0977c20d9ef7bd762e`. The PowerShell AST parser reports zero syntax errors. Codex has not executed it. It is beside the ISO, outside its verified seven-file payload set.

Before adopting this automation:

- Add a guest-only identity and scope check before any all-user installation or PATH changes. Never execute it on the AI-BS host.
- Bound installer, package and verification lifetimes; handle timeout and reboot-required outcomes explicitly. Current `Start-Process -Wait` calls have no deadline.
- Use fixed expected runtime paths and assert exact versions and successful exit codes. Current PATH-based resolution and stored version strings do not establish the intended installed runtime.
- Retain a result in an explicitly created guest-only directory, including failure details and a nonzero process exit on failure. Current catch records failure without an explicit failing exit; its final result is omitted if `C:\AI-BS` does not already exist.
- Use exact wheel versions/paths, disable network/index/config surprises, and verify installed package metadata and imports. Preserve the pinned wheel hashes.
- Correct the statement that digests were verified against official signatures: this script compares hashes; it does not perform Authenticode verification. Earlier separate verification established valid installer publishers, official Node/wheel digest comparisons and a locally pinned Python digest. Do not claim an independently published Python digest comparison.
- Deliver the reviewed script as a new, versioned, independently read-back media artifact. Preserve v1 unchanged. Do not assume React/esbuild dependencies or a guest-control service are included.

## Current execution gate

The operator explicitly approved launching the verified Node.js 24.22.1 and Python 3.13.17 installers in this guest. That approval persists; do not ask again for those installations. An actual Windows permission/authentication prompt still requires the operator under Computer Use's mandatory restrictions.

Guest mouse clicks did not reliably open File Explorer after two attempts; repeating them stopped. Keyboard capture was reported by the hypervisor, but the application-launch chord did not establish progress either. Native hypervisor menus worked and the snapshot/media operations were verified separately. The operator was asked to open This PC and the AIBS_PROV DVD inside the VM so installation can continue from an observed folder. No installer has been launched or reported successful at this checkpoint.

Keep expired/unactivated base images unavailable for task admission, as required by `WINDOWS_EVALUATION_REVIEW.md`. Do not alter clocks, rotate clones, restore snapshots to extend evaluation, or enable networking without scoped authorization. Legitimate activation/licensing, exact runtimes, protected guest control/transport and the actual 14 cases in `ISOLATED_WORKER_CONTRACT.md` remain open. Configuration, a desktop and passing host mocks do not complete them.

Evidence directory is recorded in `scratch/phase4_desktop_provision_checkpoint.txt`; it contains source/document originals, before hashes, desktop metadata, the persisted VM configuration and snapshot/media metadata. Screenshots were inspected through the tool, without saving or re-emitting screenshot payloads. No generated fixture code was executed on the host.
