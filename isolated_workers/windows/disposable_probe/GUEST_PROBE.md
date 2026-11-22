# Fixed disposable Windows probe

`GuestProbe.cs` is a narrow diagnostic executable, not a candidate runner. It has
three fixed child behaviors: `emit` writes `probe\n` to stdout and `diagnostic\n`
to stderr then exits 7; `sleep` sleeps ten seconds; `overflow` writes two MiB
across stdout and stderr. There is no arbitrary command, path, interpreter,
dependency installation, key or account provisioning interface.

Its exact ordered public arguments are:

```
--mode emit|sleep|overflow --attempt <lowercase-GUID-D> --challenge <64-lowercase-hex> --timeout-ms <500..30000> --output-bytes <4096..1048576> --worker-sid <bound-local-SID> --vm-id <lowercase-GUID-D> --image-sha256 <64-lowercase-hex>
```

The executable requires x64 Windows, VirtualBox SMBIOS, an authenticated local
`aibs_vm_worker` identity, the exact supplied SID, medium integrity, no elevated
token and no Administrators membership, including filtered membership. The known
host worker SID is explicitly refused. These checks do not prove VM identity;
the host must independently pin the new VM, clean image, standard guest SID,
executable bytes and protected runtime/source/ancestor permissions before launch.
SMBIOS and echoed image/VM fields are guest observations, not attestation.

The parent holds its own executable open without write/delete sharing, hashes
before and after, and launches only that executable with fixed child arguments.
Child context binds its parent PID/start time/path and an ephemeral environment
token. The child receives no inherited host/user environment or credentials.
Only its stdin/stdout/stderr handles are inherited. Stdin is NUL. Both streams
are collected as raw bytes under a single shared ceiling, never more than one
MiB combined. A Job Object is configured and read back before the suspended
child is assigned/resumed: one process, 256 MiB aggregate job memory, 25 percent
hard CPU rate and kill-on-close. These are the diagnostic profile, not acceptance
of any project workload profile. Timeout and infrastructure cancellation terminate
the job and verify an empty job. Host cancellation must additionally verify the
exact new VM/process lifecycle; killing a control client alone is insufficient.

The sole stdout envelope is bounded to 1,500,000 UTF-8 bytes because its retained
raw console bytes are base64 encoded. Exit 0 means a completed bounded report,
including TIMED_OUT or OUTPUT_LIMIT. Emit success requires state COMPLETED,
`child_exit_code:7`, exact output bytes and `termination_confirmed:true`. Exit 2
is preflight refusal; exit 3 is uncertain process control. The JSON is unsigned
guest-reported evidence. The host must validate it against the originating
attempt and actual VM/process observations, then produce its authenticated host
receipt. No guest report establishes candidate safety or application authority.

`Test-GuestProbeInfrastructure.ps1` compiles the guest source without invoking
its entry point, and compiles a separate trusted entry/harness against the same
native primitives. It tests exact parser/identity policy, combined output bounds,
native limit readback, exit 7, timeout, cancellation and output termination using
only an explicitly trusted test fixture on the host. Evidence and partial failures
are retained in a unique backups directory. These are infrastructure checks;
actual disposable VM checks and the fourteen containment cases remain separate.

Deployment must set protected admin/SYSTEM-owned executable/runtime paths and
ancestors, keep the signed-in integration guest intact, disable all guest NICs
and sharing surfaces, and permit only the distinct host-issued fixed probe. This
source does not implement a grant issuer, GuestControl credential protection,
network enforcement, host receipt signing, lease/replay store, candidate execution,
host staging/apply or general worker admission. Do not run the guest entry on the
trusted host. Host tests never invoke `AIBS.DisposableProbe.Program.Main`.
