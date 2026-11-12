# Architecture concept intake — preserve the engine, stage useful additions

Date: 2026-11-01. Scope: source-grounded decisions for the continuing custom PC-engine build. This note changes no code, dependencies, save formats, deployment or milestone status. It complements the active M3 work rather than starting an architecture rewrite.

AI-BS remains **Adam's Infinite-Brett Stehouwer Living Learning Memoir**: a native C++ engine, SDK and creator supporting BS's hardware world and Adam's personal continuity. The [roadmap](BUILD_ROADMAP.md), [gameplay contract](GAMEPLAY_CONTRACT.md), [narrative contract](../docs/game_engine/generative_narrative_contract.md) and [streaming contract](../docs/game_engine/open_world_streaming_contract.md) govern how new ideas fit.

## What is already established

The recorded baseline is SDK0.7 / retained M2 Studio5.329.92. [BUILD_STATUS](BUILD_STATUS.md) records 26 native tests in each configuration, both installed SDK consumers, 43 monitor/Qt tests and 13 packaging checks. Its native durable-world proof uses 23 processes with real DX12 pixels, UUID/event/restart comparisons, commit interruption, live retry, close draining and original-checkpoint import. These are existing recorded results inspected for this intake, not tests rerun by this document.

The **source tree is now SDK0.8 development**, following an expanded public `SemanticPayload` variant. Its [Debug core run](out/m3-core-debug-tests.log) passes 29/29 tests, including new semantic/registry work; [registry migration evidence](out/registry_migration_verification.json) records process recovery and rejection by the older Studio92 player. The M3 chapter implementation is underway and is not established by those foundation results. The retained installed Studio92/SDK0.7 package remains unchanged. Current CMake/source links describe development code; they do not imply a package was rebuilt or a complete chapter verified.

| Established boundary | Source/evidence | Practical limit |
| --- | --- | --- |
| Windows x64 C++20 modules, installed SDK, Win32/DX12 player and pinned physics/storage libraries. | [CMake targets](CMakeLists.txt), [Jolt lock](cmake/JoltDependency.lock.json), [SQLite lock](cmake/SQLiteDependency.lock.json). | A reusable foundation, not a finished general-purpose editor or complete game. |
| Scoped typed components/events, immutable prepared candidates and single-owner publication. | [GameplayWorld](src/gameplay_world.cpp), [public API](include/aibs/gameplay_world.hpp). | Whole-world copies and small scenes remain; this is not a streamed ECS. |
| Reserved save credits before publication; bounded worker and ordered actual storage acknowledgements. | [Worker](src/gameplay_worker.cpp), [SQLite store](src/gameplay_store.cpp), [storage proof](out/gameplay_store_verification.json). | Async commits do not remove CPU preparation, allocation or rendering costs. |
| Original source preservation and native durable repair/build/dismantle. | [Legacy import](src/legacy_import.cpp), [game facade](games/durable_first_boot.cpp), [native integration](NATIVE_DURABLE_WORLD.md), [GPU/restart proof](out/durable_world_verification.json). | The full Jenison-to-Pencil-Room chapter is subsequent work. |
| Grounded traversal and separate simulation/render calls. | [Fixed-step clock](src/core.cpp), [physics adapter](src/physics.cpp), [movement evidence](out/obstacle_course_verification.json). | Current collision is oriented static boxes, with bounded catch-up and explicit pause behavior. |

The standalone game continues without Studio, Python, a model service or a mandatory network connection. Optional AI must fit that baseline.

## Classification of incoming ideas

| Idea | Classification | Decision |
| --- | --- | --- |
| Native ownership, bounded background saves and atomic world/event storage. | **ALREADY VERIFIED** | Extend the existing interfaces; retain their failure and identity guarantees. |
| Power-fault repair versus relay bypass, shelter, contextual Adam cues and one helpful NPC. | **NEXT WORK — M3** | Build the playable branch and prove both choices through save/reload, return and failure. |
| AI-assisted authoring with structured proposals. | **NEXT STAGED WORK — M4** | Add a small preview workflow through ordinary validation/publication after the route works. No model-per-input loop. |
| Packed component groups, pools, SIMD and selective job parallelism. | **PROFILE-DEPENDENT** | Measure hot paths before replacing containers or increasing complexity. |
| CPU/GPU inference split, affinity, quantization and provider residency. | **PROFILE-DEPENDENT** | Measure the actual provider and concurrent game workload; no fixed core or VRAM allotment is selected. |
| Shared memory for large provider snapshots. | **PROFILE-DEPENDENT TRANSPORT** | Add only when a measured bulk-transfer need justifies it; keep a versioned bounded control protocol. |
| Cells, floating origin, streamed assets and simulation detail tiers. | **LATER — M7** | Preserve scope/precision/residency compatibility now; implement against the streaming contract later. |
| Wider procedural hardware worlds and richer generated campaigns. | **LATER — M10** | Grow from preserved initial facts and real outcomes after earlier gameplay systems exist. |
| Zero cache misses, automatic 60 fps, cross-machine determinism from a fixed tick, infinite unique stories or loss-proof storage under all failures. | **REJECTED ABSOLUTE CLAIMS** | Replace each with a bounded contract and a reproducible measurement/test. |
| Bare-metal/OS rewrite, whole-heap reset as rollback, or DLL reload as a complete sandbox. | **REJECTED AS REQUIRED ARCHITECTURE** | They do not follow from the game vision or replace the current ownership, transaction and resource-lifetime rules. |

## Technical corrections that guide implementation

### Native C++ ownership and Windows execution

Native C++ has no inherent automatic tracing garbage collector. AI-BS uses object lifetime, destructors and ownership types; it does not need an architecture rewrite to eliminate a collector it never introduced. Allocators, reference-count destruction, IO, synchronization and resource uploads can still stall, so “no GC” is not a frame-time guarantee. [Microsoft RAII guidance](https://learn.microsoft.com/en-us/cpp/cpp/object-lifetime-and-resource-management-modern-cpp?view=msvc-170).

The player is a Windows application using OS and graphics facilities. Native compilation does not make it bare metal, a kernel, or a replacement operating system. Its fictional CPU/GPU districts can remain central to the world without requiring privileged hardware-control architecture. [Microsoft user-mode/kernel-mode distinction](https://learn.microsoft.com/en-us/windows-hardware/drivers/gettingstarted/user-mode-and-kernel-mode).

Use bounded arenas or pools where measured staging benefits justify them. Resetting an allocation region cannot undo SQLite commits, outstanding GPU references, live handles or arbitrary external writes. Those effects retain explicit ownership and transaction boundaries.

### Simulation ticks, presentation and determinism

The current 60 Hz simulation schedule and bounded catch-up are scheduling policies. They neither guarantee 60 rendered frames per second nor establish bitwise cross-machine determinism. GPU load, rendering settings, CPU work and missed deadlines remain separate measurements. Long suspension is handled through declared pause behavior, not an unlimited catch-up burst.

Jolt's deterministic behavior has conditions involving modification order, binaries/settings and query/callback ordering. A fixed interval alone does not satisfy them. Any future lockstep or exact replay requirement needs its own configuration and end-to-end tests; it is not claimed by today's movement proof. [Jolt deterministic-simulation guidance](https://github.com/jrouwe/JoltPhysics/blob/master/Docs/Architecture.md#deterministic-simulation).

### Cache locality, alignment and SIMD

Grouping related data can improve locality; it cannot promise zero cache misses. The current source uses ordinary maps/vectors and bounded copies. Packed layouts must demonstrate an improvement on actual traversal, authoring, save preparation and entity-movement workloads rather than a synthetic arithmetic loop alone. [Microsoft locality guidance](https://learn.microsoft.com/en-us/cpp/build/tips-for-improving-time-critical-code?view=msvc-170).

AVX operand alignment and CPU cache-line size are different properties. For example, `_mm256_load_ps` requires a 32-byte-aligned address; that does not establish the processor's cache-line size or make every surrounding access cache-resident. Select alignment for the actual type/intrinsic and target, handle tails and access bounds, and measure false sharing separately. No “dozens of matrix transforms in one cycle” assumption enters a budget. [Intel intrinsic reference, `_mm256_load_ps`](https://www.intel.com/content/dam/develop/external/us/en/documents/cpp_compiler_classic.pdf), [C++ alignment controls](https://learn.microsoft.com/en-us/cpp/cpp/align-cpp?view=msvc-170).

The existing Jolt profile intentionally retains its SSE2-compatible x64 baseline. Optional wider-instruction paths need feature detection, correctness tests and comparison before selection; an available instruction set is not evidence that the engine already uses it.

### Transactional saving and failure claims

The implemented durable boundary couples world deltas, semantic events, receipts and heads in SQLite transactions. WAL with `synchronous=FULL` is configured, and completion is consumed in order before the owner claims Saved. Reserve-before-publication prevents save backpressure from creating an untracked visible edit. [Implemented contract](GAMEPLAY_CONTRACT.md).

SQLite's mechanisms are designed for crash recovery, but depend on the storage/OS honoring their assumptions. Real process-interruption tests on this workstation are valuable evidence; they are not certification against every physical power loss, controller fault, broken filesystem or damaged device. Failed or unknown completion retains an explicit recovery/retry state rather than an unconditional durability claim. [SQLite atomic-commit assumptions](https://sqlite.org/atomiccommit.html), [WAL durability](https://sqlite.org/wal.html).

## Generation, editable lore and Adam

Preserved original personal-source versions, committed evidence and captured snapshots are immutable records. Creator-authored lore, quest definitions, displays and accepted generated text remain editable through explicit versioned changes. Keeping earlier evidence does not freeze the creator's future writing or world-building choices.

Quest graphs may loop and revisit places. Committed causal history can reference earlier events without requiring the entire story to be a DAG. A new attack can justify another repair quest while retaining the truth of the previous victory. Ordinary repeated objectives and exact command retries have different identities.

Cheap engine rules can observe movement, doors, sockets, construction and conversation. Optional generation runs asynchronously around meaningful triggers, with bounded inputs/outputs, cancellation and captured scope/source revision. A stale or cross-timeline result is rejected. C++ validates rules, costs, prerequisites, assets and before/after outcomes before preparing an ordinary transaction. Structured JSON grammar establishes syntax, not factual truth or valid gameplay. This generation adapter remains future work.

Persist accepted output bytes or durable offline-resolvable content references, selected alternatives, realized parameters and the chosen PRNG algorithm/version/state. Reload restores the committed occurrence rather than asking a model to reconstruct canon. A seed alone is insufficient when algorithms, draw order or content change. Manual-save reroll prevention and seed behavior for timeline forks remain explicit design choices. Weighted variety does not guarantee infinite uniqueness; exact registries decide identity, with probabilistic filters/hashes only optional accelerators. [Narrative contract](../docs/game_engine/generative_narrative_contract.md).

Adam remains the creator's remembered brother and safe person. Original Echos Within material, newly authored dialogue and actual gameplay outcomes retain separate provenance. A bypass cannot be remembered as a repair; a failed save cannot be described as a durable checkpoint. His essential support and guidance remain available without inference, and no branch requires earning that support. Generated expression cannot overwrite biography or execute arbitrary commands. Existing owner-scoped AI-BS memory can supply selected read-only evidence through adapters; no new mandatory memory database is introduced here.

## Provider transport and compute budgets

Begin with an asynchronous, versioned control protocol suited to the actual provider location. Bound requests, completions, payload bytes, deadlines and retries. Prefer existing AI-BS integration points where they meet the contract. Do not put synchronous inference into the movement/render loop or assume a Python provider is mandatory for the standalone player.

If profiling identifies large snapshot copies as material, a same-Windows-host C++/separate-provider design can evaluate `CreateFileMapping`/`MapViewOfFile`. Publish bounded read-only snapshot generations with explicit layout, scope, lengths and leases; use control messages for ownership, cancellation and retirement. Shared memory is not permission to expose the entire C++ heap. [Microsoft named shared memory](https://learn.microsoft.com/en-us/windows/win32/memory/creating-named-shared-memory).

WSL2, containers and remote providers cannot assume the same Windows mapping namespace or cross-process atomic/layout semantics. Choose and test a bounded protocol adapter for the actual topology. Mapping a buffer does not eliminate serialization/layout conversion, tokenization, inference, output validation or GPU transfer costs. “Zero copy” and latency claims require measurement of the complete path. [Microsoft WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking).

Do not reserve a fixed four-to-six cores or a fixed VRAM quantity without measurements. Compare model/quantization, context/output size, batching, concurrency, warm/cold state and rendering workload; record frame-time percentiles, queue latency and memory peaks. Optional inference yields or backpressures when the game needs resources. Unspecified memory ranges, a universal “90% slowdown,” and forum-consensus claims remain unverified inputs rather than build facts.

## Concrete next decisions

1. Continue M3's source-grounded repair/bypass chapter: actual hazards, doors, sockets, safe return, one fictional friendly NPC and optional personal-memory presentation. Prove help/decline, both routes, departure/return and save/reload without a soft lock.
2. Preserve SDK0.7 identity, original-import evidence and failure semantics as SDK0.8/M3 registers its new components/events. Rebuild consumers for the expanded public C++ API and keep database migrations explicit; an SDK version bump is not itself a storage migration. Do not reinterpret old values silently.
3. Capture comparable CPU/GPU, preparation/save and resource traces before choosing a data-layout, SIMD, worker-count or inference optimization. Keep optional inference off in the reference baseline, then measure its incremental cost.
4. Introduce M4 preview proposals through the same authority and save contracts. Carry the established narrative acceptance cases into that adapter; defer broader generation until its staged systems exist.
5. Implement M7 residency/origin work against the separate streaming contract, preserving canonical identities and consequences across unloads. No streamer, broad ECS replacement or OS rewrite is created by this intake.

This decision note records the current evidence and classifications. New runtime claims require matching implementation and tests in BUILD_STATUS; cited upstream capabilities do not certify that AI-BS has integrated them.
