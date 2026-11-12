# Historical SDK proposal versus current source

The newly supplied M0/SDK note matches the October 31 proposed planning suite. The user has clarified that old notes are references and later rules prevail. No engine migration, rebuild, provisioning or save-store change was performed from this note. Current source remains SDK 0.17.4 and the retained M5/opening roadmap; all human/release gates remain separate.

| Historical proposal | Current inspected source / retained gap |
|---|---|
| C++20, Windows x64, DX12, offline standalone player | Retained in `engine/CMakeLists.txt`; standalone runtime/game executables do not require Python/Qt/model/HTTP services. Offline here is capability-specific, not a global prohibition on approved cloud integrations. |
| Ninja and vcpkg manifest mode | Current presets use Visual Studio 17 2022/x64 Debug/Release. No `engine/vcpkg.json` found; do not replace working tooling from the proposal. |
| SDL3 | Current platform is Win32 (`src/platform_win32.cpp`, user32/gdi32 links). |
| DirectXMath, ImGui, PIX/RenderDoc | DirectXMath used in renderer; ImGui not found in current targets. Actual capture/debug qualification is separate. |
| EnTT, D3D12MA, DirectXTex | Not found in inspected dependency paths. Current World uses engine-owned entities/std::map; do not label it EnTT-backed. |
| cgltf | Pinned cgltf 1.15 in `cmake/CgltfDependency.cmake` / CharacterImport. This does not prove every proposed static/PBR/DDS pipeline. |
| Jolt / fixed simulation | Jolt integrated. FixedStep 60 Hz has four outer catch-up ticks; character advance separately permits eight internal ticks. |
| miniaudio / Audio alias | Current backend is XAudio2 with AudioAssets/Codec/Playback and MemoryPlayback; no current `AIBS::Audio` alias. |
| Lua after M6 | Explicitly proposed/deferred; no current Lua dependency found. |
| Core/World/Render/Assets/Physics/Gameplay | Real current CMake targets. |
| UI/Animation/AI/Adam aliases | Not current CMake targets. Related HUD, character, guarded authoring and AdamMemory/Guide/CompanionRuntime behavior has its own actual surfaces. |
| `World::CommitTransaction`, `TimelinePreviewController` | Exact proposed names not found. Current CreatorSession apply/undo/redo and validated authoring/gameplay publication are the actual interfaces. |
|16 types / 82 attributes | Those counts belong to explicitly PROPOSED `docs/game_engine/component_contracts.json`, not a proved runtime registry. |
| MasterDbSaveStore/LocalSaveStore, backend `engine_game_*` | Proposed classes/schema are not current engine classes. Actual GameplayStore takes an explicit database path and uses scoped `aibs_gameplay_*` tables, receipts, recovery and explicit migrations. Never move original saves into a backend master database merely to match this note. |
| Five complete terrain/volume/mesh/modular workspaces | Retained scope; current authoring/placement/assets do not prove all modes. Terrain/mesh/volume expansion remains in M7 roadmap. |
| M0 skeleton / `src/main.cpp` / headless-test next | Superseded: current `src/main.cpp` absent and CMake contains many runtime/test targets. Dated SDK 0.17.0 reports 128 tests per configuration and consumer checks, not rerun in this comparison. |

Source anchors: `engine/CMakeLists.txt`, `CMakePresets.json`, `include/aibs/engine.hpp`, `src/render_dx12.cpp`, `src/platform_win32.cpp`, `cmake/CgltfDependency.cmake`, physics/audio/gameplay sources, `docs/game_engine/authoring_and_world_building.md`, `component_contracts.json`, and `engine/milestone_queue.json`.

Current entry points: `docs/game_engine/PROJECT_INDEX.md`, `docs/agent_sync/current_long_term_goal.json`, latest `docs/CODEX_HANDOFF.md`, and the master ecosystem architecture. Preserve authored assets, original saves, failed evidence and pending creator/RTX/opening acceptance. Do not restart M0 or turn this historical dependency wishlist into an adopted migration.
