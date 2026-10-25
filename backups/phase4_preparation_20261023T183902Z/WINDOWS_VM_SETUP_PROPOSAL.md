# Phase 4 Windows worker setup proposal

Revision 1 | October 23, 2026 | Application v5.329.17 | Status: proposed, not installed

## Task 1 completed: concrete setup proposal

Fresh read-only inventory: Windows 11 Home build 26300; 61.6 GB visible memory; 32 logical processors; firmware virtualization enabled. Free space: C 186.3 GB, D 56.5 GB, E 107.5 GB, F 61.4 GB. Prior scoped inventory found no VirtualBox, VMware, Hyper-V commands or Sandbox in checked locations; this turn does not establish exhaustive software absence. Build 26300 compatibility must be tested before use.

## Recommended configuration for review

Use the Oracle VirtualBox base package with a properly licensed Windows 11 guest. Do not assume the host activation covers a guest. Confirm guest entitlement/media before provisioning; no price or free license is promised. Do not install the separately licensed Extension Pack for this workflow.

Proposed initial allocation: one worker, 4 virtual CPUs, 8 GB RAM, dynamically allocated 64 GB guest system disk plus a disposable differencing disk. Proposed storage C:/AI-BS/isolated_workers/windows; do not create or move VM storage yet. Keep at least 80 GB host free; budget actual base image, task overlays and retained evidence before proceeding. This is a conservative starting configuration, not benchmark evidence. Keep Ollama on the host; no GPU passthrough or model copies in the guest.

Install only required host components; omit USB, bridged/host-only networking and Python bindings where supported by the reviewed installer. Do not disable existing Windows/WSL/VBS protections to resolve a compatibility issue without review. Run the worker controller as an ordinary dedicated OS user. The FastAPI web process must not receive administrator or unrestricted hypervisor credentials.

Prepare Windows and matching Guest Additions with required runtimes in a maintenance session using reviewed media. If setup/activation/update needs networking, obtain a separate maintenance-network authorization; no generated code runs in that session. Patch and record hashes/version identifiers, then shut down and pin an immutable clean base image. Clone a fresh disposable guest for each task. Guest tasks run as a nonadministrator; admin-capable provisioning credentials never enter generated-code environments or logs.

For task guests: all network adapters disabled (NAT is not isolation), no shared folders, shared clipboard, drag/drop, USB, remote display, host disks or personal folders. Use narrowly scoped Guest Control copy/execute operations for approved task inputs/outputs. This transport requires a prototype and security verification; it is not implemented. Do not mount C:/AI-BS, Drive, OneDrive, document vaults, model stores or credential directories. Never expose localhost backend/Ollama APIs to the guest.

## Installation decision and rollback

Approval is needed for hypervisor installation, kernel drivers, a possible reboot, guest licensing/media and any maintenance network session. The current request to do two tasks authorizes this preparation, not those host changes. After review, pin the exact official package version, verify the publisher signature and official SHA-256 checksum, record installer options and compatibility results, and separately approve any unexpected reboot/network changes. No downloads/installations/purchases occurred in this task.

Before installation save the current service state and boot/network configuration. On failure stop the worker and leave expanded execution disabled; preserve images, logs and task evidence. Uninstalling drivers or restoring host settings requires a reviewed rollback action. Never roll back by deleting documents or resetting the shared repository. Existing trusted-host workflow remains explicitly labeled; it cannot be used as fallback for VM-required tasks.

## Provisioning acceptance, all pending

1. Confirm guest licensing and official media integrity; demonstrate build-26300 compatibility without weakening host security.
2. Record host/guest/runtime versions, base-image hashes, installer signature and enabled VM device configuration.
3. Demonstrate ordinary-user guest execution and independent host-controller identity.
4. Run the denial/limits/recovery cases in ISOLATED_WORKER_CONTRACT.md; retain evidence even on failure.
5. Enable only the new isolated route after all gates pass. Phase 5 remains disabled until then.

## Official sources reviewed

- [Oracle VirtualBox 7.2 Security Guide](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/Security.html): least privilege, official checksums, optional Windows driver components and network risks. NAT can reach host loopback.
- [Microsoft Hyper-V installation requirements](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/get-started/Install-Hyper-V): Home cannot install the Hyper-V role.
- [Microsoft Windows 11 licensing guidance](https://www.microsoft.com/licensing/guidance/Windows-11-Licensing-for-Virtual-Desktops): rights depend on the license and virtualization method. Confirm the applicable entitlement rather than extrapolating commercial guidance to this personal setup.

The VirtualBox recommendation and resource allocation are engineering proposals. No claim of installed compatibility, license entitlement or successful isolation is made.
