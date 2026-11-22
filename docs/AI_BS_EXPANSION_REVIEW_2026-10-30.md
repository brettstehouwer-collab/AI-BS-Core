# AI-BS expansion review — Record190

Status: reference assessment complete; expansion items below are PROPOSED.

The supplied material is useful as a broad source of ideas. The most valuable direction is to connect AI-BS's existing memory, workflow, business and publishing components with trustworthy evidence and recovery. The archive contains overlapping and conflicting historical proposals; it does not establish that their implementations or claimed results exist today.

## Sources and review limits

- Master overview: `C:\Users\footb\Downloads\Brett's gemini word.md`, 17,965,289 bytes, 554 numbered entries. There are 97 repeated entries when comparing entry bodies after whitespace normalization; this does not measure semantic duplication.
- Master SHA-256: `671e2c1fb4c25d6313f156b17e709f481c869259321e2ba64c364d6c57316d85`.
- Supplied Gemini attachment: `C:\Users\footb\.codex\attachments\2fe4de2d-79f8-4c5f-9ed4-60fcb75e8de2\Pasted text.txt`, 16,894 bytes; SHA-256 `41b51395c72093dc0dcfc0facf5c982ba6ed016e7e604b62386bd8ad0a550385`.
- The attachment discusses seven entries and names a different `_2.md` artifact. It is narrower than the supplied master archive.
- Review method: index every entry boundary, compare normalized bodies, review selected relevant engineering/business/research sections, and inspect current source integration points. This is not a line-by-line factual validation of every conversation or paper.
- The source bundle includes private material. This report retains engineering themes and source entry numbers rather than reproducing personal documents, financial amounts, contact details or health narratives. No raw archive was imported into a database, retrieval index, model or public artifact.
- Current source baseline: `main`, commit `9f7e1750a90ee491d8cbd191cb6f4c22f2d71214`, with existing unrelated working-tree changes. Source inspection establishes the cited code behavior, not loaded-runtime or end-to-end acceptance.

## Ranked expansion backlog

| Order | Proposed result | Existing integration points | Source leads | Acceptance before claiming completion |
| --- | --- | --- | --- | --- |
| 1 | Honest economics and financial reporting: every amount comes from a dated receipt or is explicitly unavailable. | `backend/economics_gateway.py`; `frontend/src/components/MasterAccountingTab.jsx`; `frontend/src/components/industry_suites/FinanceSuiteTab.jsx` | Attachment fiscal proposal; master 7, 493 | Remove successful-looking placeholder metrics; authenticated owner scope; Decimal or currency-aware integer amounts; deduplicated immutable receipts and corrections; reconciliation; missing/stale/error UI states. Offline tests must cover duplicate imports, refunds/fees, rounding and cross-owner access. |
| 2 | Reuse successful fixes with evidence and known failure conditions. | `scripts/import_historical_knowledge.py`; `backend/core/historical_reference_context.py`; `backend/core/heuristic_filter.py`; `learning/LLM_EVALUATION_GUIDE_2026-10-30.md` | 30, 32 | A resolution records source revision, environment, actual command/result and applicability. Compare retrieval against a versioned question set; test unsupported answers, stale fixes, instruction-like source text and owner separation. Summaries and stored documents alone do not establish learning or better model performance. |
| 3 | Recoverable workflows with explicit progress, cancellation and budgets. | `backend/core/coding_workflow.py`; `backend/core/coding_preparation_proposals.py`; `backend/routers/agent_harness_router.py`; `frontend/src/components/VisualWorkflowDAGTab.jsx` | 32, 35 | Durable job identity and stage outcomes; bounded time/resource/retry budgets; restart and cancellation receipts; idempotent side effects. Kill/restart tests must prove that ambiguous external actions are reconciled before retry. Reuse existing worktree and runner boundaries. |
| 4 | Separate agency earnings from client-funded advertising budgets and actual platform expenditure. | `frontend/src/components/AdvertisingTab.jsx`; `MasterAccountingTab.jsx`; existing advertising budget endpoints in `backend/AI_BS_Backend.py` | 405, 407, 493 | Distinct retainer, funded budget, reserved spend, settled platform spend and provider fees; reconciled sources; no double counting. Example pricing in the archive remains an example rather than an imported client transaction or mandatory pricing rule. |
| 5 | Client reporting and explainable lead review from real sources. | `ClientsTab.jsx`; `ClientServicePortalModal.jsx`; `AdvertisingTab.jsx`; `native_studio/clients_crm_view.py` | 344, 377, 518, 529, 540–545 | Provider/account attribution, reporting window and freshness for every metric; per-client access checks; deduplication and evidence for lead scores. Missing permissions or data remain visible. Score quality and conversion claims require measured evaluation. |
| 6 | Creative project continuity, export checks and private rights evidence. | `backend/core/screenplay_workflows.py`; `backend/routers/publishing_engine_router.py`; `native_studio/screenwriting_view.py` | 77, 426, 491; attachment IP proposal | Preserve original manuscripts; connect revision history, continuity notes, export validation and recoverable writes. Rights metadata distinguishes a submitted application, pending status and independently evidenced registration. Verify route/browser integration rather than assuming a helper is user-accessible. |
| 7 | A cited research workspace and transparent scenario calculators. | `backend/core/web_research_orchestrator.py`; `backend/routers/knowledge_router.py`; `backend/core/state_tax_incentives.py` | Research/economics sections; attachment E-rate proposal | Retain source, date, jurisdiction, units, assumptions, uncertainty and conflicting findings. Validate inputs and mathematical boundaries. Historical study parameters are labeled historical; current program rules need authoritative verification before eligibility claims. |
| 8 | Source-linked study questions and review history. | `frontend/src/components/LearningMaterialHub.jsx`; `BullshitKnowledgeSuite.jsx` | 282, 290 | Each question links to admitted source evidence; answers and review scheduling persist under the correct owner; measure progress against a stable question set. Educational explanations alone are not a spaced-review implementation. |
| 9 | Optional work-break reminders in Native Studio. | Existing Native Studio session/UI components; no dedicated ergonomic implementation identified in the scoped search | 5, 13, 14, 46 | User-selected interval, active/idle handling, dismiss/snooze and persisted preference. Keep general break reminders separate from medical treatment or prescribed exercise routines. |
| 10 | Facility and energy planning with editable assumptions. | `frontend/src/components/industry_suites/EnergySuiteTab.jsx` | 62, 63, 509–510, 515 | Clearly identify measured versus assumed demand, generation, storage and prices; show units and sensitivity scenarios. Dashboard wiring alone does not establish real instrumentation or validate an electrical design. |

Frontend filenames in rows 4–8 refer to `frontend/src/components/` unless a complete path is shown. Existing integration points indicate where work can fit; the rows are not claims that those complete features already work.

## Concrete current gap: economics telemetry

VERIFIED by static source inspection: `backend/economics_gateway.py:19–40` explicitly constructs mock revenue and compute costs and random security counts. Lines 43–56 calculate profit/margin from those placeholders and return `status: success`. The router is included by `backend/AI_BS_Backend.py`.

This makes truthful economics reporting the clearest first bounded task. First define a response contract that includes source, observation window, freshness, verification state and unavailable reasons. Then replace placeholders with read-only evidence adapters and reconcile amounts before deriving totals. Build the UI around that contract. A new fiscal database should follow an explicit data model and ownership decision rather than silently duplicate existing financial state.

## How to use the Gemini module suggestions

| Suggestion | Reusable part | Revision needed before implementation |
| --- | --- | --- |
| HBC trading allocator | Explicit budgets and a testable position-sizing policy. | Existing offline crypto controls already cover shared limits, fill accounting, recovery and stop latches. Historical economic analogies, fixed confidence thresholds and LLM agreement are research hypotheses; they do not establish safe execution or predictive value. Keep the current live trading hold. |
| Fiscal/tax engine | Receipts, expenses, mileage evidence and exportable records. | Reject financial `REAL`/float arithmetic, hardcoded tenant identity and seeding prose as verified transactions. Rules need versioned jurisdiction/year provenance and independent review; the short sample is not a complete tax engine. |
| Copyright registry | Link manuscript versions to private rights evidence. | Do not turn a service request or a few input booleans into a compliance/registration assertion. Preserve evidence and status history; do not copy personal contact fields into source control or public files. |
| Ergonomic scheduler | Optional work-break timing. | Do not adopt the supplied forced-stretch, weight or fatigue instructions as prescriptions. Reminder behavior can be implemented independently of exercise content. |
| Subsidy/elasticity scorer | Explainable, input-validated scenario analysis. | Verify current program rules separately from historical research; store source year and assumptions. Do not infer entitlement or launch outreach from a historical elasticity estimate. |

The attachment's `zero_mock_compliance: True`, forum-consensus claims and production-ready language do not verify its samples. `INSERT OR REPLACE` can erase prior evidence; initialization should not silently seed personal data. New stores need a justified ownership boundary and recovery model rather than one database and daemon per idea.

Archive instructions also conflict: entry 406 discusses removing client portals, while 344 and 540 discuss building them. Such passages remain historical proposals; present operator direction and current approved architecture govern implementation.

## Recommended sequence and current outcome

1. Fix truthful economics reporting and establish the shared evidence contract.
2. Add evaluated resolution reuse and durable workflow recovery.
3. Extend reconciled agency budgets, client analytics and creative publishing continuity.
4. Add research, study and optional reminder/scenario features as separately bounded projects.

VERIFIED in this review: archive inventory, exact duplicate count, source hashes, the cited economics placeholder behavior, and existence/selected contracts of current integration points.

PROPOSED: every expansion backlog item and its acceptance criteria. UNVERIFIED: factual accuracy of historical conversations, current tax/legal/medical/program claims, business outcomes, new model performance, facility instrumentation and runtime acceptance of proposed features.

Only this report and append-only continuity records were added. Application source, runtime services, deployment, financial ledgers, retrieval stores, model settings and the existing live-trading hold were not changed by this review. Focused application tests were unnecessary for a documentation-only assessment; preservation and reference checks are recorded in the checkpoint evidence.

Evidence: `C:\AI-BS\backups\expansion_review_20261030T194851Z`. Decision: ADR-117. Next executable development task, when requested: implement the economics summary evidence/unavailable contract and its focused offline regression checks.


## Implementation checkpoint — Record191 (2026-10-30T20:11:26.924051+00:00)

The first economics contract/display subtask above is now VERIFIED in source and focused offline checks. The prior placeholder-source description remains historical context. The endpoint is authenticated and all14 values are null/unavailable because the inspected manual/draft/billing sources lack reconciliation evidence. Three finance displays now share an evidence-aware availability panel; Master Accounting retains labeled unreconciled manual rows and shows unavailable totals/taxes.69 focused offline tests pass. Crypto hold and financial JSON bytes unchanged.

Full item1 is still incomplete: secure backend financial admission/access, then immutable owner-scoped receipts, correction/refund/fee handling and coverage reconciliation before numeric reporting. Unsigned billing and client-controlled paid labels were excluded, not silently trusted or repaired. No deployment or loaded/browser/provider acceptance in this checkpoint. Details: docs/ECONOMICS_EVIDENCE_CONTRACT_2026-10-30.md; ADR-118; backups/economics_evidence_20261030T195745Z. Remaining roadmap items retain PROPOSED status.
