# Evaluation guidance integration — 2026-10-30

The supplied evaluation resources now contribute five reviewed, attributed reference passages to AI-BS's existing local Qwen/chat/coding retrieval collection. The curated [guidance card](LLM_EVALUATION_GUIDE_2026-10-30.md) covers executable build evidence, grounded output review, task-specific rubrics, repeatable comparisons, retrieval attribution, language, creative editing and architecture. The [source catalog](llm_evaluation_sources_2026-10-30.json) distinguishes ten retrieved resources from seven unreviewed discovery links. Source summaries were curated; notebooks, linked code and datasets were not executed or installed.

The work also fixed a concrete reporting defect in `scripts/agent_sync/sync_gateway.py`: a successful run previously printed a fixed “47/47” count and a live-isolation claim. It now retains the configured command, return code, duration, full captured output, output hashes and observed unittest counts. Zero tests, skips and expected failures are incomplete; malformed summaries, failures, timeouts and execution errors cannot pass. Subtest event counts do not create invented successful-case counts. Model-quality fields remain advisory and explicitly `not_run`, outside the executable acceptance gate.

The importer now accepts `--source-card` for one explicitly selected prose document. This mode preserves paragraph/word boundaries without changing historical chunking. Apply still requires a byte-identical reviewed corpus and the verified existing local operator principal, makes an online SQLite backup, stores owned records and confirms readback. It performs no archive scan in this mode.

## Verified results

- **70 focused tests passed in 1.316 seconds** with synthetic stores and mocked inference. The expected fallback500 fixture message is not a provider incident. Command and observed output: `backups/evaluation_guidance_20261030/tests.json`.
- Exactly **5 new rows** were added for `local_admin` to `historical_knowledge_v1`; all **360,849 previous vault rows** remained identical across every column, including ownership and hidden status. Total vault rows: **360,854**.
- All five stored contents, hashes and source metadata match the reviewed records. Zero duplicate fingerprints were found. The five sanitized passages reassemble without character loss; the original card hash is unchanged.
- All **2,006 previously assessed historical source hashes** still match. Existing originals, previous imports and both dry runs remain preserved.
- Direct owned retrieval returned the new card for `observable_test_evidence` in a bounded 1,400-character context. Unbound and unrelated-owner retrieval returned no references.

## Evidence and repeatability

The exact imported corpus SHA-256 is `81ab8e57f7ca257834f7bfcc00b59bb2711fb2ced6153cf0d7909f6af3523da8`. The source card SHA-256 is `8fdbcf7cc52424ace2f15bc1b812f2dbc58830bc68fd91a5700d6b58bbe3052f`.

- `learning/historical_knowledge/20261030_evaluation_review_v2`: reviewed manifest and exact corpus.
- `learning/historical_knowledge/20261030_evaluation_import`: applied manifest, corpus, record-ID/hash receipt and online database backup.
- `backups/evaluation_guidance_20261030`: original dirty-file snapshots, before/after manifests, narrow source diff, diagnostics, tests and independent verification script/results. Private corpus/database artifacts remain ignored by Git.

For another explicitly reviewed card, choose fresh directories:

```powershell
python -X utf8 scripts/import_historical_knowledge.py --source-card learning/NEW_CARD.md --output learning/historical_knowledge/NEW_REVIEW
# Inspect the exact records and sources before applying.
python -X utf8 scripts/import_historical_knowledge.py --source-card learning/NEW_CARD.md --output learning/historical_knowledge/NEW_IMPORT --apply-local-admin --reviewed-manifest learning/historical_knowledge/NEW_REVIEW/manifest.json
```

This is local reference and source integration. Model weights, environment settings, activation flags and shared services were unchanged. No judge framework, external trace upload, cloud sync, live inference, loaded application/browser check or VM acceptance suite was run. No measured quality gain or release acceptance is claimed. The next evaluation step is to define a representative task set and fixed rubric, then compare baseline and candidate visible outputs under recorded, equivalent conditions; execution evidence remains a separate requirement.
