# Windows exchange file primitive

`ExchangeFiles.cs` is a dormant, reviewed-source file primitive. It opens only a
caller-provisioned fixed NTFS root, pins volume/file identity, walks directory
components by native relative handles and rejects reparse points. The caller must
supply an explicit path allowlist from its trusted manifest. Directory creation,
source selection, credentials, ACL provisioning, TLS and worker admission remain
outside this primitive. Root provisioning must never select the project, originals,
private stores or model directories as an exchange root.

Publication requires exact bytes/SHA-256, uses native create-new semantics, flushes
and reads back the file through its handle before returning a receipt. It never
overwrites an existing file. Reads require exact length/hash and refuse multiple
hardlinks. File lengths are capped at1MiB; aggregate bounds remain the protocol's
responsibility. Roots and intermediate directories stay open while an operation
runs; a per-session lock serializes operations and disposal to prevent handle reuse.

Windows allowed a disposable directory rename despite open handles. The test
therefore proves object confinement rather than claiming renames are impossible:
publication follows the original pinned object, and a replacement directory at
the old name cannot reuse that identity. Junction escapes and hardlinked files
are refused using actual Windows fixture operations.

This is not an execution/apply interface. Receipts always deny both authorities.
Failed/interrupted creates may leave partial files as retained evidence, with no
successful receipt and no overwrite retry. Multi-file publication, durable delivery
receipts/recovery, source binding and protocol/worker integration are still needed.
Successful infrastructure tests under the current user do not establish standard
worker ACLs, guest containment or acceptance of the current VM configuration.

Tests preserve all disposable files, hardlinks and junctions under Record112:

    powershell.exe -NoProfile -File C:\AI-BS\isolated_workers\windows\control\exchange_io\Test-ExchangeFiles.ps1

Native API references:
- https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile
- https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfileinformationbyhandle
- https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers
