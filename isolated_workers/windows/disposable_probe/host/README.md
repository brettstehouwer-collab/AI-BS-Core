# Fixed disposable diagnostic host controller

This is a narrowly scoped infrastructure probe. It does not admit candidate jobs,
execute the number-summary fixture, change the integration guest, use port18443,
apply production files, deploy AI-BS, or connect the VM page.

`DisposableProbe.psm1` exposes five fixed operations:

1. `New-AIBSProbeRequest`: controller SID1001 creates an immutable, expiring request
   and permanent reservation with a random challenge. Modes are `success`,
   `timeout`, or `cancel` only.
2. `Start-AIBSProbeTransport`: controller SID1001 verifies the protected transport
   policy, profile, module, entrypoint and PowerShell executable. It uses the
   controller's DPAPI-protected secure string to launch exactly
   `AI-BS\aibs_probe_host` (SID1006), checks the actual process token SID and
   bounds output and elapsed time. There is no scheduled-task dependency.
3. `Invoke-AIBSWorkerProbe`: only the exact standard SID1006 with a medium token
   may use VBoxManage. It validates the separate VM, an accepted powered-off
   snapshot, the sealed base hash, current disk ancestry, no network/clipboard/
   shared folders/USB/VRDE, guest identity, exact probe binary and fixed commands.
   It restores the accepted snapshot before and after each probe and requires
   confirmed final poweroff. Uncertain cleanup quarantines the attempt.
4. `Complete-AIBSProbeRequest`: controller SID1001 collects the bounded worker
   result and signs a receipt with a key unreadable by SID1006.
5. `Test-AIBSProbeReceipt`: controller SID1001 verifies the receipt scope and HMAC.

All attempts and dispatches use CreateNew permanent files. An expired request,
an existing claim, a duplicate dispatch, or a reservation without an authenticated
terminal receipt prevents automatic replay. An interrupted or quarantined attempt
requires explicit reconciliation; creating a new attempt does not bypass it.

## Protected deployment contract

The only operational root is
`C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1`.

| Relative path | Required access |
| --- | --- |
| `policy`, `deployment`, `requests` | Controller/System/Administrators write; dispatcher read/execute |
| `state`, `receipts` | Controller/System/Administrators write; dispatcher cannot modify |
| `private\host_credential.dpapi`, `private\receipt.key` | Controller/System/Administrators only; key exactly32 bytes |
| `credentials\guest.txt` | Controller/System/Administrators write; dispatcher read only |
| `vbox_home`, `worker_state`, `worker_outputs` | Dedicated dispatcher may write; no other untrusted writer |
| `worker_claims` | Dispatcher create/write only; no DELETE, DELETE_CHILD, WRITE_DAC or WRITE_OWNER; inheritable OWNER RIGHTS ReadPermissions suppresses a created file owner's implicit DACL authority |

Protect relevant parent directories too. Reject reparse points, multiple hard
links, unexpected owners and untrusted write/replacement permissions. At a volume
root, DELETE is not treated as a usable rename/delete route; DELETE_CHILD,
WRITE_DAC and WRITE_OWNER remain checked. Do not change drive-wide ACLs merely
to remove an inapplicable volume-root DELETE observation.

Operational code runs from `deployment\host\DisposableProbe.psm1` and
`deployment\host\Invoke-WorkerTransport.ps1`; the private runtime is
`deployment\pwsh\pwsh.exe`. A protected `policy\transport.json` must have exactly
`schema_version:1`, `module_sha256`, `entry_sha256`, and `pwsh_sha256`.
`Start-AIBSProbeTransport` requires that file's independently retained SHA256.
The source checkout is not an operational exchange root.

`policy\profile.json` has exactly these fields:

```text
schema_version state vm_uuid image_id image_base_path image_base_sha256
system_disk_uuid accepted_snapshot_uuid vbox_path vbox_sha256 vbox_user_home
guest_executable guest_executable_sha256 guest_username guest_sid dispatcher_sid
controller_sid vm_memory_mib vm_cpus
```

The state must be `PROVISIONED` after actual installation, account/protection
verification and an accepted powered-off snapshot. Missing or PREPARED policy
returns `ISOLATION_UNAVAILABLE`. Integers must be JSON integers. Digests are64
lowercase hex digits, UUIDs canonical lowercase, and timestamps explicit UTC with
seven fractional digits. No profile supplied by a guest is authority.

The fixed VM is `e5a2fe34-7b90-460c-83af-903d51b4bb16` and the integration UUID
`6c5a53da-ab80-4ecb-8be6-4059266f736e` is explicitly rejected. Image ID is
`aibs-fixed-probe-win11-eval-e5a2fe34-7b90-460c-83af-903d51b4bb16`; resource
allocation is4 CPUs/4096MiB. The original diagnostic planning value was8192MiB;
live installation preflight refused it with only7.3GiB free host RAM. The revised
diagnostic-only profile requires6GiB free before launch, retaining a2GiB host
reserve. It does not change any general candidate resource profile. The64GiB base must be sealed against dispatcher
modification. Current writable differencing disks must form a bounded ancestry
ending at that pinned base, with all paths under `E:\AI-BS-DisposableProbe-v1`.
At least40GiB free space on E is required before launch. The base is streamed
through SHA256 and held read-only for the attempt, never loaded into a byte array.

Guest executable is exactly `C:\AIBSProbe\DiagnosticProbe.exe`, launched as the
actual standard guest `aibs_vm_worker` with its separately pinned guest SID.
The16 public arguments are fixed by the module; no caller supplies an executable,
command, environment, directory or script. Success expects stdout `probe\n`,
stderr `diagnostic\n`, and child exit7. Timeout expects the trusted guest's fixed
sleep child to be terminated by its job. Cancel terminates the owned VBoxManage
wait then powers off and restores only this VM; guest child-tree cancellation
is confirmed through VM lifecycle, not a claim that killing VBoxManage killed it.

Each GuestControl operation has30seconds,131072 combined transport bytes and no
inherited host environment. Initial guest child output is4096 bytes combined,
with2seconds, one process,256MiB memory and25percent CPU rate. The guest agent
implements those child limits; host checks the exact report. General candidate
console/artifact limits remain1MiB combined console,20 files,2MiB/file,16MiB total;
this diagnostic collects no returned artifact files.

## Evidence and remaining acceptance

The host receipt HMAC binds the exact task/attempt/challenge, profile, image,
configuration and result evidence. The receipt explicitly labels standard-host
worker observations and guest reports. Image/VM arguments echoed by the guest
are not independent measurements. An authenticated collection receipt or matching
digest does not establish safety or full containment acceptance.

`Test-Infrastructure.ps1` exercises trusted host code with deterministic request
clocks, synthetic and measured VBox metadata, HMAC tampering, actual harmless
host infrastructure processes and mocked VM lifecycle calls. It does not call
VBoxManage or execute a guest or candidate. Failures and successes remain under
`host\evidence`. Actual disposable-VM installation, standard-account execution,
process/job limits, timeout/cancel, receipt readback and snapshot lifecycle must
still be measured before calling the first diagnostic accepted. The fourteen
candidate containment cases and number-summary's retained seven tests remain
separate gates.

GuestControl syntax follows the [official VirtualBox manual](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/vboxmanage.html).
The installed VBox7.2.22 `showmediuminfo` uses raw colon metadata and does not
accept `--machinereadable`; the adapter preserves that observed distinction.

## Separate bootstrap observation and baseline preparation

`Readback-And-SnapshotWorker.ps1` describes its scope by default. Execution is
restricted to the protected PowerShell7 deployment and exact dispatcher SID. It
requires a separately published, hash-pinned one-use bootstrap grant; this is
independent of diagnostic job authorization. Its fifteen exact JSON fields are:

```text
schema_version state purpose attempt_id challenge issued_at expires_at vm_uuid
dispatcher_sid vbox_sha256 host_entry_sha256 host_module_sha256
guest_readback_sha256 guest_probe_sha256 accepted_snapshot_name
```

The state is `AUTHORIZED_FIXED_BOOTSTRAP_ONLY`, purpose
`bootstrap_readback_snapshot_v1`, and snapshot name
`AIBS_ACCEPTED_DIAGNOSTIC_V1`. Source and executable SHA256 values are mandatory;
the canonical attempt/challenge and UTC validity window bind this operation and
expire within ten minutes. The grant is protected host data, never supplied by
the guest. A permanent claim and exclusive provisioning/VM leases precede any
VM operation. Partial operations and their results remain in a fresh
`worker_outputs\bootstrap-<attempt>` directory.

The entry inspects only the new VM and removes known installation optical media
while it is powered off, before the first standard-account session. It starts
that VM only, then delivers the pinned `Guest-BootstrapReadback.ps1` source to
the fixed Windows PowerShell runtime. The readback does not launch
`DiagnosticProbe.exe`; it measures its hash, the actual standard token and
native denied-access checks on executable/runtime files, relevant parents and
credential-bearing setup records. Runtime hashes and the bootstrap report are
returned as guest observations. The guest source remains below10KiB and is
never invoked on the host.

A clean guest shutdown must be observed before taking the accepted powered-off
snapshot. A forced fallback retains a blocked result and cannot create an
accepted baseline. Successful preparation returns
`SNAPSHOT_PROPOSED_AWAITING_CONTROLLER_SEAL`; it does not publish a profile or
authorize a diagnostic. The controller must independently protect the base
file and relevant parents against dispatcher replacement, stream and retain
the base SHA256, validate the snapshot/disk ancestry, review the bounded
readback, and only then publish the pinned `PROVISIONED` profile. An expired,
failed or interrupted bootstrap attempt remains retained and cannot be replayed.

`Start-BootstrapPreparation.ps1` is the separate controller-only publisher and
launcher. Its execution switch is accepted only from the protected deployment;
all five caller-supplied pins must match the admitted module, fixed bootstrap
entry, guest readback source, VBoxManage and PowerShell executable. It creates
the permanent reservation before publishing the one-use grant, reads the host
dispatcher's private DPAPI credential without exposing plaintext, and launches
only that entry under the actual standard dispatcher SID. The existing grant
path is never overwritten. Bounded launch stdout/stderr and owner/lifecycle
identity are retained separately from the worker's bootstrap report. No
Task Scheduler acceptance is assumed. The launcher does not seal an image or
publish an execution profile; the remaining exact contract is in
`CONTROLLER_SEAL_CONTRACT.md`.

## Controller image sealing implementation

`Seal-WorkerImage.ps1` implements that separate controller phase. Its default
only describes scope. Operational use requires the protected PowerShell7 copy,
controller SID1001, the exact successful bootstrap attempt/grant, and seven
source/runtime/executable pins. It retains the protected controller launch and
independently revalidates the standard guest proof. No VM is started or restored.
It holds controller/dispatch/provisioning/VM leases throughout the phase.

`Inspect-SealedWorker.ps1` accepts only a fresh five-minute controller grant and
permanently claims its seal/phase under standard dispatcher1006. Its fixed
operations read the exact new VM and disk ancestry and perform native access
opens. `SealPolicy.ps1` validates raw output against parsed configuration and
an acyclic chain ending at the pinned base. Preflight, protected-access and final
observations must bind the same powered-off snapshot/configuration/chain.

The controller preserves original base/store owner and DACL before protection,
then holds a streaming read handle over the64GiB base through final inspection.
Thirteen real native access observations must confirm the standard dispatcher
can read the base but cannot modify or replace it or its relevant parents.
Only Win32 access-denied5 counts as denial. Volume-root DELETE is excluded;
DELETE_CHILD/DACL/owner remain required. No global drive ACL is changed.

After acceptance, the controller binds retained evidence and exact profile bytes
to a private-key HMAC receipt. A matching predeployed four-field transport policy
is held and preserved byte-for-byte, including its actual measured hash. Changed
transport pins fail closed. Absent transport and the new nineteen-field profile
use CreateNew; existing profiles are refused. Interrupted or failed sealing
retains evidence and original ACLs for review without automatic ACL rollback.

`Test-SealInfrastructure.ps1` checks these pure policies, ACL construction and
protected-entry gates. Its fake metadata and ACL objects do not mutate ACLs,
operate a VM, hash an actual image or demonstrate effective containment. Source
readiness does not establish successful installation, sealing or diagnostics.
