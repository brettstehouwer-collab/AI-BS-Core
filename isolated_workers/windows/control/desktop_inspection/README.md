# Current desktop inspection candidate

This separate candidate collects read-only evidence for the preserved `AIBS_PostDrivers_20261024` graph. Existing recovery/setup/desktop controllers do not import it. It provides no VM start, snapshot restore, media attachment, guest command, task transfer, credential mechanism or accepted execution provider.

The entry is `../Inspect-CurrentWorkerDesktop.ps1`. Its actual worker path has **not run**. Infrastructure tests, host refusal and static review must not be reported as worker adoption or any of the fourteen containment cases.

The entry requires the existing x64, medium-integrity, nonadministrator `aibs_vm_worker` account before source imports, compilation, native VM queries or inspection evidence writes. The two helper sources and installed Oracle executable are hash pinned; the executable also requires its reviewed valid Oracle signature. Use a fresh PowerShell process with `-NoProfile` if an operator later runs the entry, so an existing in-memory query type cannot substitute for the pinned source. Do not run it under the operator account or alter the identity guard.

Only two native operations exist: fixed-UUID `showvminfo --machinereadable` and fixed-child-disk `showmediuminfo`. Each query has a 20-second deadline, a 1 MiB combined captured-output bound and a 64 KiB stderr bound. The entry uses an overall monotonic query budget. File I/O, signature validation, compilation and OS scheduling are not certified hard real-time boundaries. A terminated client does not establish VBoxSVC or descendant termination.

`DesktopProfile.ps1` validates the fixed current VM, disk/snapshot ancestry and current hardware independently of historical snapshot hardware. It permits only the two reviewed diagnostic/wheel images by exact path, length and hash. The optical UUID must agree between the real current registry/XML and fresh native observations; no guest or command-line argument selects it. Any graph or hardware transition requires a separately reviewed profile change. Pure fixtures using changed UUIDs are explicitly synthetic.

Inspection evidence stays under the private worker/SYSTEM/Administrators runtime directory. An exclusive lease, attempt/query intents, complete bounded native results and committed completion evidence distinguish a completed read-only inspection from incomplete or quarantined history. Preserve uncertain history for review; do not delete files to enable another attempt. Raw VM metadata/output remains local and is not part of the cloud engineering summary.

An exit of zero means only that this fixed read-only inspection finished. The report retains `TaskAuthority`, `ProviderAccepted`, `RuntimeVerified` and `LicensingVerified` as false. Guest runtimes/imports, supported Windows licensing/expiry, credential exclusion, protected transport, disposable task execution, cancellation/recovery and all fourteen real containment cases still require independent evidence.

Tests use trusted fixed native fixtures or pure metadata/XML/policy data. They never invoke VBoxManage as the operator or run guest/project code. Relevant evidence is in the dated `phase4_desktop_profile_*`, `phase4_desktop_query_*`, `phase4_desktop_entry_policy_*` and root `phase4_desktop_preflight_*` backup directories.
