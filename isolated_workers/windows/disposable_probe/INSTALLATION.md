# New offline worker installation

`Install-WorkerOS.ps1 -Install` is a fixed demand-only operation for the protected
standard host launcher, SID ending 1006. It targets only VM
`e5a2fe34-7b90-460c-83af-903d51b4bb16` in the isolated VirtualBox registry. The
integration guest is never adopted, stopped, started or changed. The default
invocation describes the operation without calling VirtualBox.

The controller must deploy the installer and `Bootstrap-GuestProbe.ps1` read-only
under `deployment`, deploy the reviewed executable as
`deployment\DiagnosticProbe.exe`, and copy the pinned Oracle additions ISO to
`identity\VBoxGuestAdditions.iso`. It must create protected
`identity\install_manifest.json` with exactly this structure and three unique
entries (replace only the bootstrap source hash with its measured deployment hash):

```json
{
  "schema_version": 1,
  "vm_uuid": "e5a2fe34-7b90-460c-83af-903d51b4bb16",
  "files": [
    {"relative_path": "deployment\\Bootstrap-GuestProbe.ps1", "sha256": "<measured-bootstrap-sha256>"},
    {"relative_path": "deployment\\DiagnosticProbe.exe", "sha256": "82c6b2510807246aaa99668bb4416ec99c4ce3ecbc7d007cfe4165d14aaf1531"},
    {"relative_path": "identity\\VBoxGuestAdditions.iso", "sha256": "fc41354d8b974051fa33ca5a4f9c999a58c6e0dfc595b02a924a544392234b3d"}
  ]
}
```

The plan may remain `PREPARED`; readiness instead requires the retained prepared
VM checkpoint and a fresh exact-UUID powered-off machine inspection. Installation
checks the hardware/sharing/NIC profile and current storage/RAM. It holds pinned
media and payload files against write/delete, excludes the provisioning lease,
and creates one durable `installation.started` marker. An interrupted or failed
attempt is retained and cannot be silently retried or adopted. The controller
must review any partial attempt rather than deleting this marker to retry.

The fixed diagnostic profile uses exactly 4 GiB guest RAM, four vCPUs and a 64 GiB
virtual disk, with EFI, Secure Boot and TPM 2.0. Before setup it requires at least
6 GiB currently free host RAM (4 GiB guest plus 2 GiB reserve) and 40 GiB free
storage. The 4 GiB allocation meets the published
[Windows 11 minimum memory requirement](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements).
This revision replaces the earlier 8 GiB diagnostic allocation after the fresh
host RAM check refused installation before its durable start marker was created.
The earlier evidence remains retained. This profile covers the fixed diagnostic
only; it does not approve general candidate execution or resolve its full resource
profile.

The bundled Windows answer template is independently pinned. Its two default
LabConfig bypass blocks are removed, and a one-logon bootstrap limit is inserted.
There is no TPM/CPU/RAM/storage/SecureBoot bypass. Actual guest bootstrap checks
SecureBoot and TPM before deployment. The custom postinstall script installs
Oracle-signed additions from the pinned optical media, with TXS explicitly off,
and performs no dependency downloads or network activation.
The guest independently checks the wrapper executable and two current
publisher/root certificate hashes from that ISO. It imports only those pinned
certificates into the new guest and then requires the exact Oracle signer and a
valid signature. No expired SHA1 certificate set or network certificate fetch is
part of the bootstrap. Host observations of those inert media bytes are retained
under `backups/disposable_probe_install_review_42a4ec7536f4453296d3eeefcf789246`.

The disposable installation answer files and auxiliary optical media necessarily
contain disposable bootstrap credentials. Their contents and the generated
postinstall script are private data: do not print, commit, upload or include them
in a public ledger. The custom script never dumps the environment, password or
full command output to the installation log. It stages bootstrap material in an
admin/SYSTEM-only guest directory. The standard guest account cannot read it.
Bootstrap also protects retained Windows Panther/setup records and known Sysprep
answer files against standard-user reads; it preserves those files as evidence.
After successful installation the host must detach every installer/auxiliary
optical medium while the new VM is powered off, before starting the worker. The
host retains its protected installation evidence. Do not expose those media to
the worker or copy their contents into result artifacts.

Bootstrap creates a new local standard `aibs_vm_worker` with the separately
provided guest credential, deploys the exact reviewed diagnostic executable to
admin/SYSTEM-owned `C:\AIBSProbe` with worker read/execute only, disables bootstrap
and the built-in administrator, clears automatic-login credential fields, writes
`C:\AIBSProbe\bootstrap.json`, and shuts down the new VM. It does not execute the
diagnostic executable. The host must read back and independently verify account
SID/token, executable/runtime/parent permissions, sharing/network state, attached
media, VM identity and a clean image/snapshot before issuing a fixed diagnostic
grant. A bootstrap report is unsigned guest observation, not acceptance or
execution authority.

Installation is asynchronous after VM startup. A caller must inspect the exact
VM lifecycle; termination of a VBoxManage client does not prove VM shutdown.
Timeouts retain the attempt and report that lifecycle review is required. The
installer does not automatically reset, power off, remove media, rebuild or retry
after a failure. Guest Additions installation has a ten-minute wait; any partial
guest install remains evidence. An installer or evaluation image compatibility
failure must be diagnosed, not worked around by reintroducing hardware bypasses.

These are new installation sources and infrastructure checks only. They establish
neither a completed Windows installation nor actual worker containment. The first
probe, cancellation/timeout, receipts, fourteen containment cases, candidate tests,
host application/deployment and UI wiring remain separately measured milestones.

`Observe-InstallScreen.ps1 -Observe` is a separate fixed observation for the same
protected standard host launcher and exact new VM. It reads bounded machine state
before/after and, only when running, captures one display-0 PNG (maximum 2 MiB)
under a unique `worker_outputs\install-observation-*` evidence directory. Each
hypervisor command is limited to ten seconds and 128 KiB combined console output.
It sends no keys, starts/stops no VM, and invokes no guest program. Powered-off
state is retained without attempting a screenshot. The screen and machine-state
files are private installation observations; their existence does not establish
installation completion or candidate execution. The observer defaults to a
description without VM calls, and its pure infrastructure test never invokes the
observer entry or hypervisor helper.

Every observer command now retains its exit code and bounded raw stdout/stderr
as base64 in `command-*.private.json`, including failures of the first state
read and screenshot. These private diagnostics are excluded from ledgers/cloud
records. A display with zero dimensions may not support screenshots yet; a
failed screenshot does not establish an installation failure. Diagnose retained
stderr before proposing another observation. The original minimal process
environment remains: the successful first state read did not establish that
missing profile variables caused a screenshot failure.
