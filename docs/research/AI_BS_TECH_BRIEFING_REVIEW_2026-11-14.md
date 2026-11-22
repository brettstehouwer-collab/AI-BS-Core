# AI-BS technology briefing review — November 14, 2026

Review time: 2026-11-14T11:54:14Z. Input: user-supplied November 13 briefing, attachment `927458dd-14d5-4480-8802-7911221474a0/Pasted text.txt`. Scope: five specific November 12 claims, primary-source web evidence only.

**Result: four announcement/initiative claims corroborated; one scientific claim UNVERIFIED.** Google's benchmark version is inconsistent across its own announcements and remains unresolved. Corroboration confirms what the publishers announced; it does not independently reproduce performance, establish AI-BS compatibility, or authorize execution.

These are **Goal 10 research backlog candidates only**. They do not change the current chat/creative acceptance priority or authorize installations, model calls, benchmarks, provider switches, migrations, deployment, or architecture changes. No AI-BS runtime/source implementation or private data was inspected in this review.

## Evidence

| Claim | Status | Primary evidence and limits |
| --- | --- | --- |
| IBM LLMON, Granite 4.1 3B/8B experimental previews | VERIFIED announcement; performance vendor-reported | IBM's November 12 article identifies both preview models and its toolkit. It describes reserved-token markup and explicit bindings between instructions, requirements and data. IBM reports improved resistance on static indirect-injection benchmarks and comparable general capability. It explicitly treats the behavior as learned rather than enforced and the models as experimental, unsuitable for production. The 8B model card independently identifies IBM's team and November 12 release date. [IBM announcement](https://huggingface.co/blog/ibm-granite/llmon-an-llm-native-markup-language-now-in-granite), [8B model card](https://huggingface.co/ibm-granite/granite-4.1-8b-llmon-preview). |
| Gemini 4 Hydrogen and Antigravity Orchestrator | VERIFIED announcement and vendor claim; benchmark version UNVERIFIED | Google's November 12 model announcement supports the API release, one-million-token context, four thinking levels, and claimed near-Carbon task success with 24% less quota and 19% faster completion. However, it associates those figures with Terminal-Bench 4.0; the same-day Antigravity article associates them with 4.1. Preserve this discrepancy instead of choosing a version. Neither source establishes local downloadable weights or the user's account eligibility. [Google model announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/), [Antigravity announcement](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity). |
| World Labs Atlas tools, Chisel, meshes and Blender integration | VERIFIED product claims; usability untested | World Labs' Atlas page names Viewfinder image reconstruction, Chisel scene layout, splat-to-mesh conversion, and developer APIs/integrations including Blender. Its earlier Atlas introduction is dated September 1, 2026. A November 12, 2026 related-article entry on its Marble page links to the Atlas release page. This supports the briefing's distinction between model introduction and tool release. Export fidelity, licenses, API/account access, Unreal collision quality and performance were not tested. [Atlas tools](https://worldlabs.ai/atlas), [September model introduction](https://worldlabs.ai/blog/atlas), [dated release link on World Labs' own site](https://worldlabs.ai/blog/marble-world-model). |
| Nature Materials Ru–O–Cr electrolysis, 55.7× reduced dissolution and 285 h at 1 A/cm² | UNVERIFIED | The single focused search returned no primary result. The supplied attachment gave no paper title, DOI, authors or exact URL. No matching paper or supporting information was retrieved. The numbers, comparison catalyst, publication date, test conditions and peer-review attribution remain uncorroborated in this bounded review. An empty search result is not evidence that the claim is false. |
| SGLang Consortium founders | VERIFIED announcement; no runtime comparison evidence | LMSYS' November 12 announcement names NVIDIA, AMD, Intel, Google, Meta, Cloudflare, Modal and RadixArk, announced at the inaugural summit. It describes joint roadmap work while maintainers retain technical/code-acceptance responsibility. Formation does not establish SGLang performance against AI-BS's current runtime. [LMSYS announcement](https://www.lmsys.org/blog/2026-11-12-sglang-consortium/). |

## Proposed backlog experiments and dependencies

All entries below are PROPOSED and unexecuted. No acceptance result is implied.

| Candidate | Dependencies to resolve first | Proposed acceptance evidence |
| --- | --- | --- |
| Structured context/injection evaluation | Confirm existing AI-BS prompt/tool permission boundaries and current retrieval contracts; preserve SQLite provenance and separate Chroma bins. Review exact model revision, license, tokenizer, special tokens, chat template, runtime support and memory budget. Use synthetic data and an isolated harness. Application permissions remain independently enforced. | A frozen corpus such as 100 legitimate tasks and 100 synthetic injection cases; same tasks across baseline/candidate; task and attack success, false refusals, tokens and latency. Include adaptive/multi-turn cases separately because IBM's cited results emphasize static attacks. Record configurations and failures. |
| SGLang versus current local inference baseline | Inventory the actual current engine and exact model/quantization before comparison. Verify upstream hardware, CUDA, OS/WSL and model support; isolate environment/ports and GPU scheduling; preserve the working runtime. Neither Windows support nor 4090 fit was qualified here. | Comparable weights, quantization, prompts, context lengths, concurrency and sampling; prefill/decode throughput, p50/p95 latency, peak VRAM, error rates and task completion. An incompatible configuration is a reported limit, not grounds for changing the baseline. |
| Atlas-to-Unreal asset evaluation | Confirm authorized Atlas/API access and export rights, supported Blender/Unreal versions, nonprivate reference assets, and isolated test-project storage. No assets were uploaded or exported. | Import success; mesh/poly counts, UV/material behavior, units/scale, collision/navigation correctness, cleanup time and measured frame cost against a conventional reference asset. Visual examples alone do not qualify game assets. |
| Multi-model orchestration comparison | Reconcile Google's benchmark-version discrepancy; preserve official-client/provider-owner boundaries and existing quotas. Assess account/model availability only in separately scoped work. API availability does not authorize credential changes or provider requests. | A separately approved, reproducible workload comparing task completion, human correction, elapsed time and actual quota/cost. Google's workload-specific percentages are hypotheses, not AI-BS targets or results. |
| Electrolysis research follow-up | Obtain exact paper title/DOI and supporting information before treating the numerical claim as evidence. | Verify comparator, dissolution measurement, catalyst loading, cell conditions, uncertainty and durability definition. No AI-BS implementation dependency is established. |

## Retrieval and preservation record

Five focused searches were issued: four in one parallel batch, then the consortium query. The strongest official announcement pages were retrieved directly; additional primary model-card and World Labs introduction/date evidence came from search-returned page content. No secondary reporting was used. This is a bounded review, not an exhaustive literature search or independent benchmark audit.

Queries:

1. `IBM LLMON "Granite 4.1" 3B 8B November 12 2026` — restricted to ibm.com and huggingface.co.
2. `"Gemini 4 Hydrogen" "Antigravity Orchestrator"` — restricted to Google announcement domains; the linked Antigravity article was then read directly.
3. `World Labs Atlas Chisel Blender November 12 2026` — restricted to worldlabs.ai and docs.worldlabs.ai.
4. `"ruthenium" "55.7" "285" chromium Nature Materials` — restricted to nature.com; zero results.
5. `SGLang Consortium November 12 2026 founding NVIDIA AMD Intel Google Meta Cloudflare Modal RadixArk` — restricted to lmsys.org and sglang.io.

Canonical repository observed: `C:/AI-BS`, branch `codex/audit-v532976-20261031`, commit `64fad2871e0a716d9964f506bdef1050612b173d`. The two assigned research paths did not exist before this review. Only this Markdown file and its matching JSON were created. No backup upload or restore verification was performed. Full-source hashing and broad handoff reconciliation remain the owning agent's session-close responsibility under the development bypass; this research note is not a release/handoff acceptance receipt.

Exact next research step: retain these candidates in Goal 10; resolve the DOI and Google benchmark-version gap if a later authorized research phase selects them. Current implementation acceptance work retains priority.

