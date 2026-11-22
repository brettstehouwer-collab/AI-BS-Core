# Textured asset development contract

SDK 0.11 is a source development build. Studio97 / SDK0.10 remain the retained
release. This work does not yet expose textured placement in the chapter creator.

## Owned data and wire format

`ImageAssets` decodes bounded 8-bit PNGs through WIC. Complete RGBA8 mip chains
retain explicit sRGB color, linear data or normal-map semantics. Color mip
filtering uses linear light and premultiplied alpha; normal mips renormalize
vectors. Dimensions, byte counts and decoded budgets precede pixel allocation.

`SurfaceAssets` retains per-corner UVs, tangents and handedness independently of
legacy geometric deduplication. The caller explicitly selects OBJ UV origin;
cooked UVs use top-left origin. Degenerate UVs retain an explicitly invalid
normal-map tangent flag. Geometry transforms use the existing validated mesh
projection. Imported detail does not create collision.

`AIBSurf2` contains a 48-byte little-endian header: eight-byte magic, uint32
version2, uint32 payload length and32 SHA-256 bytes. Its payload embeds an
unchanged AIBMesh1, per-corner attributes, complete image mip chains and material
albedo image indices. It contains no external image paths. The whole file is
bounded to32MiB. Decode rejects trailing bytes, nonfinite values, negative zero,
unknown flags/enums, malformed dimensions/counts and invalid material bindings.

The four-file surface pack contains `catalog.aibcat`, `<sha>.aibsurf`,
`LICENSE.txt` and `provenance.json`. The canonical catalog is:

```text
AIBCAT 2
surface <UUID> <SHA256> <same SHA256>.aibsurf
```

The sorted filename/length/digest manifest uses `AIBPACK 2`. Legacy AIBCAT1,
AIBMesh1 and AIBPACK1 retain their exact format. Persistent references remain
the same UUID/payload-SHA/pack-SHA triple; authoritative catalog kind and payload
magic must agree. License edits create a distinct pack identity, while edits
inside a pinned store invalidate its reference.

## Surface cooking

Use the explicit native mode with a triangulated OBJ and AIBMAT2 table:

```powershell
aibs_assetc --cook-surface --source board.obj --materials board.aibmat --asset-id UUID --name "Board" --license LICENSE.txt --output NEWFOLDER --uv-origin bottom-left
```

```text
AIBMAT 2
pcb 1 1 1 0 board.png
metal 0.5 0.5 0.5 0 board.png
plastic 0.1 0.1 0.1 0 -
```

Texture names are bounded PNG basenames relative to the material declaration;
`-` selects a constant. Repeated filenames share one embedded image. No external
OBJ material library is loaded. The output is a fresh four-file directory.
`--inspect` validates either pack version. `--stage-store` and `--inspect-store`
require explicit `--profile warm-beginning` for typed surfaces. Source paths
are not required after cooking/adoption. The legacy cooker command remains.

## Budgets and publication

Legacy staging remains64MiB. Explicit `AssetContentProfile::warm_beginning`
permits128MiB encoded dependency closure and separately bounds decoded
dependency residency to128MiB. Deduplicated packs are charged once. Modern
surfaces cannot enter the legacy staging profile. Existing merge behavior can
retain unused verified dependencies; it never changes an existing pack.

The DX12 texture layer owns descriptor heaps, texture resources, staging data,
vertices and draws. It preserves SceneMesh callers and offers combined
`set_scene(base,textures)` publication so rejected resources cannot publish
half a scene. Composed descriptors/draws/vertices and actual GPU allocation sizes
are independently bounded. Texture uploads finish before publication.

The shader samples albedo with explicit transfer functions. Authored point/key
lighting, exposure and one bounded directional shadow map now have a separate
lighting contract in LIGHTING.md. Tangents are preserved for later normal
mapping. Full PBR and roughness/metallic/AO sampling remain future work.

## Remaining checkpoint3 acceptance

Modern profiles now connect to AIBD3, private dependency validation, deduplicated
typed placement projection and native creator Preview/Apply/Undo/Redo/Save/reopen
and isolated Play. The source integration has process and GPU proofs, including
corrupt-pack rollback; consult timestamped reports under out/warm_beginning.
Re-run affected GPU checks after renderer changes and complete frozen packaging
before promoting launchers. Current technical pixel proofs do not establish
final art quality, performance targets or completion of checkpoints3–8.
