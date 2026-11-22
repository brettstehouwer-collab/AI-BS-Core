# Native character cooking and typed inspection

The character mode is separate from the existing OBJ and surface cook modes:

```text
aibs_assetc --cook-character --source MODEL.glb --asset-id UUID --name TEXT --license RIGHTS.txt --output NEWPACK
  [--clip SOURCE_INDEX NAME loop|once] [--resource URI FILE] [--bake-rate 1..60]
```

Source, asset identity, display name, rights declaration and output are required.
Named scalar options occur once. At most eight explicit clip mappings retain
their requested order. The default bake rate is30; supported rates are1..60.
Clip indices are complete unsigned integers and playback mode is explicitly
`loop` or `once`. Omitting clips produces a bind-pose resource rather than
guessing animation names. A companion model that needs four presentation clips
must explicitly map `idle`, `walk`, `catchup`, `guidance` in that order.

`--resource URI FILE` provides at most96 exact input resources for JSON glTF.
Input files may live outside the source directory, but their URI keys must pass
the importer's canonical relative-URI profile. The cooker reads only files
explicitly named on its command line; the importer never falls back to nearby
files, a URI loader, data URLs or network access. GLB assets use embedded buffers
and images and therefore reject external resource options. Duplicate keys,
missing resources and supplied-but-undeclared resources are rejected.

The source document and all explicit resources share one32MiB input limit.
Lengths are checked before file allocation, and each following resource is read
under the remaining aggregate budget. Inputs and output parents must be regular
and unredirected under the existing native path policy. The rights declaration
is nonempty UTF-8, without NUL, and at most64KiB. It is copied byte-for-byte;
the cooker does not infer ownership or permission from its text.

## Pack publication and provenance

The importer and AIBChar2 encoder complete before any output staging begins.
The existing sibling staging owner writes and reads back exactly four files:

- `catalog.aibcat`, one canonical `AIBCAT 2` record of kind `character`;
- `<complete-payload-sha256>.aibchar`;
- unchanged `LICENSE.txt` supplied by the caller;
- bounded UTF-8 `provenance.json`.

The staged pack is independently inspected through the typed store reader
before its sibling directory is atomically renamed to the fresh final path.
Existing output directories/files are never overwritten. A rejected request
removes only exact staging files created by its owner and its empty staging
directory. Authoring inputs and existing immutable packs are not modified.

Provenance contains exact document/resource byte counts and hashes, URI keys,
the importer's complete `AIBS_GLTF_SOURCE 1` manifest digest, asset identity,
ordered clip choices, bake rate, actual joint remap and uniform clip intervals.
It records cgltf1.15 commit360db1a95480fe102ae9c69b27c5d101167ff5ba and verified
header SHA e378a21c084bf1f288bb799de827bb26906efb024255f1ecf1705ea13f11c6ec.
The full cgltf MIT notice is retained with the engine dependency and installed
SDK licenses; the pack's rights declaration remains the caller's asset license.

The recorded opaque-image policy ignores source alpha and canonicalizes it to255
before linear-light sRGB mip generation. Hologram opacity remains instance data.
The documented four-weight quantization policy, handedness conversion and
coherent bind-shape treatment are explicit. Absolute source/resource host paths
are not inserted into provenance, and original reference files are not copied
merely because a source file lives beside them.

Import diagnostics distinguish the actual private-parser allocation peak from
the conservative engine-owned live upper bound. Neither value is labeled as
whole-process, opaque WIC or GPU memory. Complete payload and decoded charges
are reported separately; actual renderer allocation admission remains the
renderer owner's responsibility.

## Inspection and staging

`--inspect PACK` now reads a typed character pack and reports its immutable
asset/payload/pack digests, `sha256`, name, `kind:"character"`, vertex/triangle,
material, joint, clip and owned image counts, logical mip bytes and decoded
storage. Surface and mesh row formatting retain their prior behavior.

`--inspect-store STORE --profile warm-beginning --ref UUID PAYLOAD_SHA PACK_SHA`
verifies the requested reference against generic typed inspection before
returning character metadata. It deduplicates references and enforces the
existing128MiB encoded and decoded closure limits. `--stage-store` uses the same
explicit modern profile for character dependencies. Legacy inspection/staging
continues rejecting characters rather than treating a skeleton as static
scenery. Generic immutable adoption retains its canonical four-file manifest.

## Verification artifacts

The real previous CLI rejected `--cook-character`; its RED is retained at
`D:/AI-BS-Game-Resources/workshop/character-cooker-test/cli-red.log`. An isolated
strict MSVC object compilation also verifies the new source without modifying
the shared build or running a GPU process.

`tests/verify_character_cooker.py EXE EVIDENCE_DIRECTORY` generates owned
synthetic GLB/glTF data with four named, in-place clips, coherent inverse binds,
UVs and a2x2 PNG containing source alpha. Loop clips return to their initial
rotation. The process proof checks actual cooking, canonical digests,
deterministic fresh outputs, complete provenance/diagnostics, typed inspection,
adoption/staging, source deletion and a fresh inspector, corrupt immutable
dependencies, strict options and licenses, aggregate byte limits and failed
output preservation. Each process is joined and raw logs remain in its unique
evidence directory. It uses no family references, model inference or network.

Actual green process results are recorded by the coordinated central run;
source presence or object compilation alone is not a cooked-character pass.
The cooker itself does not establish Adam likeness, native animation rendering
or the completed packaged opening.
