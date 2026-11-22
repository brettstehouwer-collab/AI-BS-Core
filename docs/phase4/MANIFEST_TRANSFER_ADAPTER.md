# Manifest-bound project transfer adapter

Record120, October 26, 2026. Source and synthetic host infrastructure verified;
guest delivery and all fourteen actual VM containment cases remain NOT RUN.

`backend/core/coding_vm_transfer.py` bridges the existing project-admission
contract to the narrower provisional transport. It preserves the original
schema1/schema2 inputs and version1 returned-artifact formats. It does not change
the diagnostic listener, codec, native file primitive or execution provider.

## Contract preserved

The adapter accepts at most20 project files,2MiB per file and16MiB total.
Canonical project paths remain at most240characters and retain valid Unicode
and allowed dotfiles. Existing credential-path, immutable verification/dependency,
selected-file and admission checks still apply. Source data is supplied explicitly;
the adapter never searches a repository or opens a source path.

Each project file becomes one or two transport parts of at most1MiB. Empty files
retain an explicit empty part. Transport paths use an opaque admission/direction
identifier plus fixed numeric file/part indexes, under `inputs/` or `outputs/`.
Original project names appear only in manifest data and cannot select transport
destinations. The manifest is at most256KiB and fits within one transport file.
The maximum possible40data parts plus one manifest fit the existing64-path bound;
the16MiB aggregate project bound further limits simultaneously large files.

Send one manifest/part per existing scoped-codec packet so each packet stays
within that codec's1MiB file and8MiB aggregate bounds. Packet authentication,
confidentiality, fresh nonces and durable claims remain caller responsibilities.
This adapter is not connected to a network route;18443still permits only its
three diagnostic operations.

## API and validation

`prepare_vm_transfer(envelope, contents, admission, direction=...)` first calls
the existing input or returned-artifact validator, then returns immutable byte
parts and a canonical manifest. The host admission must already come from
authenticated host policy. A copied guest manifest does not create authority.

`restore_vm_transfer(manifest_bytes, chunks, admission, direction=...)` rejects
oversized/noncanonical/duplicate-field metadata, wrong direction/admission binding,
unexpected part layouts and missing/extra/changed chunks. It bounds all original
file sizes before concatenation, then reruns the complete original validator,
including whole-file hashes and immutable verification/dependency checks.
Returned data carries execution/applyfalse and verificationnot_run. It cannot
issue a verification seal or prove that program checks ran.

## Evidence

`backups/manifest_chunk_transfer_20261026_record120` retains:

- The initial failing import and first green11-case adapter run.
- A41-case regression run covering codec, adapter and disposable SQLite replay
  behavior; all passed. Original codec/replay sources are unchanged.
- A retained synthetic Windows fixture with six actual handle-based publish/read
  roundtrips, altered-read-hash refusal and exact reassembly of a2MiB file whose
  original project path contains Unicode. An allowed dotfile name also survived.
  The fixture's admitted source/test bytes were copied as data and never run.
- Source/checkpoint hashes and a readback-verified private cloud handoff update.

The fixture ran under the trusted host provisioning context. It does not establish
standard-worker effective denial, authenticated guest delivery or VM containment.

## Remaining integration

The host worker's authenticated same-account disabled-task registration remains
pending. Complete protected runtime/dependency deployment and native broker
caller/root/ancestor/object-identity checks before using these files operationally.
Retain incoming packets before durable replay claims can strand a delivery;
implement durable per-transfer receipts, inspection, cancellation and recovery.
Rehash each part through the native regular-file/hardlink/reparse protections.
Provision exact per-attempt directories and independent clean licensed execution
images. Do not expose a public execution endpoint or substitute host execution.

Host apply/rollback remains a separate gate after actual isolated verification.


## Record122 update
Metadata-first inspect_vm_transfer and logical private-store/model suffix checks now precede collection. The new retained_inbox atomically stores packets and claims in a dedicated SQLite store.59combined infrastructure tests pass; no operational guest-delivery route or execution authority is enabled. See DURABLE_PACKET_INBOX.md and Record122 for actual host diagnostic/observer limitations and the delivered, unexecuted7test fixture.
