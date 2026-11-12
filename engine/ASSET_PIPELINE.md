# Native asset pipeline — SDK 0.10.0

The native engine imports triangulated OBJ geometry with an explicit AI-BS material table, cooks a checksummed mesh and previews the cooked package through DX12. This first material model is opaque base color and normalized emission. It uses the existing vertex-color renderer. Texture coordinates are validated when present in OBJ but are not retained. Textures, UV/tangent storage, PBR, transparency and automatic collision binding remain later work.

The deployed Studio97 Assets tab is integrated into **Engineering & Specialized Labs → AI-BS Game Engine Build → Assets**. It offers **Cook new asset pack**, **Open asset pack**, **Preview selected** and **Stop preview**. Studio97 packaging and frozen-workflow verification passed; all five existing launchers now open97. Studio96/95 and SDK 0.9/0.8 remain preserved.

The larger environment plan, including modular kits, maps, lighting and collision authoring, is in [environment_asset_plan.md](../docs/game_engine/environment_asset_plan.md).

SDK 0.10 adds [persistent chapter placement](PERSISTENT_PLACEMENT.md). Its project-owned immutable packs, AIBD2 records and Preview/Apply/Save workflow extend the standalone inspection path described below. See [Creator quickstart](CREATOR_QUICKSTART.md) for the chapter workflow and `BUILD_STATUS.md` for current release verification. The standalone showcase still does not edit a chapter.

## Source and material preparation

Export triangle faces with finite positions and usable normals, or let the importer generate face normals. Coordinates are meters with **+Y up**. Import performs no hidden axis or unit conversion. Supported geometry records are `v`, `vn`, `vt`, triangle `f` and `usemtl`; object/group/smoothing records are inert metadata. An OBJ `mtllib` declaration is also inert: its file is never opened. Supply every used material through the explicit `.aibmat` table.

The table begins with `AIBMAT 1`. Each subsequent material row has a visible ASCII name of at most 64 bytes, three base-color components and one emission value. Names are unique and have no whitespace or `#` comment marker. Every numeric value must be finite and within `[0,1]`.

```text
AIBMAT 1
copper 0.65 0.22 0.065 0
pcb 0.025 0.19 0.085 0
power_trace 0.20 0.70 0.40 0.65
```

Emission controls the existing surface-color blend. It is not a light source or proof of indirect illumination. Unsupported texture/material features are not imported from external MTL files.

The supplied teaching fixture is original procedural geometry, not manufacturer CAD. It includes a board, heatsink fins, fan, capacitor banks, contacts, connectors and screws: **4,788 triangles and eight materials** inside a 12×12×8-meter envelope. Its source files are:

- [motherboard.obj](assets/source/motherboard.obj)
- [motherboard.aibmat](assets/source/motherboard.aibmat)
- [motherboard-LICENSE.txt](assets/source/motherboard-LICENSE.txt)

Its stable asset UUID is `8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264`. Regenerate the same source bytes with `python -B engine/tools/make_motherboard_asset.py` from the repository root. The generator uses no downloaded meshes, images, CAD or model weights.

## Cook, inspect and preview

Run these commands from `C:\AI-BS` after installing SDK 0.10. The output parent must exist; the selected output folder must be new. Even an existing empty folder is rejected.

```powershell
$assetTools = 'C:\AI-BS\engine\install\0.10.0\release\bin'
$pack = 'C:\AI-BS\engine\assets\cooked\my-motherboard-part'
New-Item -ItemType Directory -Force 'C:\AI-BS\engine\assets\cooked' | Out-Null
& "$assetTools\aibs_assetc.exe" `
  --source 'C:\AI-BS\engine\assets\source\motherboard.obj' `
  --materials 'C:\AI-BS\engine\assets\source\motherboard.aibmat' `
  --asset-id '8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264' `
  --name 'Motherboard cooling assembly' `
  --license 'C:\AI-BS\engine\assets\source\motherboard-LICENSE.txt' `
  --output $pack
& "$assetTools\aibs_assetc.exe" --inspect $pack
& "$assetTools\aibs_motherboard.exe" --asset-showcase --asset-root $pack `
  --asset-id '8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264'
```

The preview places the selected asset above the motherboard's CPU area. Use WASD, right-mouse look and Space/Ctrl to move the free-flight camera; Esc or window close exits. This is a visual inspection scene. It does not place the asset into a saved chapter or change collision/picking geometry.

For a native GPU proof, add `--self-test --capture PATH.bmp --report PATH.json`. The self-test compares actual GPU readbacks with the base scene and a changed-material variant, checks camera input and reports DX12 debug errors. Use dedicated evidence paths. Graphics self-tests should run sequentially.

The cooker bounds OBJ input at 32 MiB and the material/license inputs at 64 KiB each. Mesh assets admit up to 100,000 vertices, 100,000 triangles and 64 materials. Redirected inputs/output parents reject. Cooking reads original inputs, stages four files in an owned sibling directory, flushes and verifies them, then publishes a fresh directory without replacing an existing pack. Failure cleanup targets only the cooker's own staging files.

## Published package and provenance

A successful pack contains exactly four files:

- `<SHA256>.aibmesh`: version1 little-endian mesh/material data with a payload SHA-256 checksum. The filename is the SHA-256 of the complete cooked file.
- `catalog.aibcat`: stable asset UUID, complete-file digest and digest-based relative filename.
- `LICENSE.txt`: the supplied license/rights declaration copied byte-for-byte.
- `provenance.json`: source, material and license byte counts/hashes; asset identity/name; importer format version; meters/+Y/no-conversion options; ignored external-material policy; cooked-file digest.

Catalog text is canonical ASCII with LF newlines and a final newline. It has this exact shape, with the placeholders replaced by a lowercase 64-character digest:

```text
AIBCAT 1
8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264 SHA64 SHA64.aibmesh
```

Catalog resolution rejects duplicate identities/digests/paths, directory traversal, redirected components, missing files, digest changes and mismatched decoded UUIDs. It has no source fallback. Checksums detect changed bytes; they do not authenticate an author or establish redistribution rights. The cooker records the declaration supplied by the user and does not infer a third-party license.

`--inspect PACKROOT` validates the catalog and loads each selected record through the native decoder. It returns JSON with `status` and an `assets` array containing `asset_id`, `name`, `sha256`, `triangles` and `materials`; the latter two are integer counts. The CLI accepts at most 64 catalog records and emits at most 64 KiB of complete UTF-8 JSON. Larger reports reject rather than returning a truncated inventory. The catalog SDK itself permits up to 1,000 records within a 1 MiB catalog.

## SDK and build commands

Include `<aibs/assets.hpp>` for `MeshMaterial`, `MeshAsset`, `import_obj`, validation, encode/decode, hashing and immutable new-file save/load. Include `<aibs/asset_scene.hpp>` for `AssetCatalog` and `append_asset_mesh`. Link `AIBS::Assets` for the codec contracts or `AIBS::AssetScene` for the catalog/render adapter, which includes its asset dependency.

```cpp
aibs::AssetCatalog catalog(pack_root);
const auto asset = catalog.load("8b2bc31a-3ec4-4f8f-bd4a-2ed1d69c8264");
auto scene = aibs::make_motherboard_scene();
aibs::append_asset_mesh(scene, asset, {-13, 2.8f, -5});
```

The adapter expands indexed triangles into the current `SceneMesh`, applying each triangle's material. Positive finite scale and a finite unit quaternion are supported; normals use the inverse transpose of scale and normalized rotation. Validation or allocation failure preserves the destination mesh. Calling this rendering adapter alone changes no entity, authoring history, Adam event, AIBSSAVE/AIBD/AIBA document or gameplay database. SDK 0.10 supplies the separate explicit authoring and dependency contract linked above.

Build and install to the versioned prefix, preserving the retained SDK 0.8 tree:

```powershell
Push-Location C:\AI-BS\engine
python -m cmake --preset windows-msvc
python -m cmake --build --preset release
python -m cmake --build out/windows-msvc --config Release --target RUN_TESTS
python -m cmake --install out/windows-msvc --config Release --prefix C:/AI-BS/engine/install/0.10.0/release
Pop-Location
python -m cmake -S engine/examples/sdk_consumer -B engine/out/sdk-consumer-0.10.0-release `
  -G 'Visual Studio 17 2022' -A x64 -DCMAKE_PREFIX_PATH=C:/AI-BS/engine/install/0.10.0/release
python -m cmake --build engine/out/sdk-consumer-0.10.0-release --config Release
python -m cmake --build engine/out/sdk-consumer-0.10.0-release --config Release --target RUN_TESTS
```

Use the matching Debug configuration and a separate `engine/install/0.10.0/debug` prefix for Debug verification. Asset tests are `asset_contracts`, `asset_scene_contracts`, `native_asset_cooker` and `native_asset_pipeline_gpu`; the cooker harness also proves deterministic packs, rejection boundaries and competing fresh publication. Build/test results and frozen deployment evidence are recorded separately from this guide.
