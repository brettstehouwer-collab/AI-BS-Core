# Historical knowledge integration — 2026-10-30

Imported **8,116 distinct reference passages** into `backend/stehouwer_vault.db`, collection `historical_knowledge_v1`, owned by the existing verified `local_admin` principal. This is retrieval context for local inference; model weights were not trained or replaced.

The importer assessed 2,060 source files and retained SHA-256 evidence for 2,006 readable, admitted-for-assessment originals. All 2,006 source hashes still matched after import. Visible Antigravity/Gemini messages, explicit plans and walkthroughs, historical project documents, Google Takeout Drive/Sites text, exported code, and curated build lessons contribute to the corpus. The supplied reasoning-prompt discussion contributes the existing Qwen problem-solving card, with its unsupported performance claims clearly separated from the useful work scaffold.

| Reference kind | Distinct passages |
| --- | ---: |
| Antigravity visible user messages | 1,656 |
| Antigravity visible assistant responses | 2,582 |
| Antigravity explicit artifacts | 238 |
| Historical project documents | 3,361 |
| Gemini CLI visible messages | 190 |
| Google Takeout Drive/Sites text | 38 |
| Historical chat-memory exports | 32 |
| Exported Gemini code, retained as unexecuted reference | 8 |
| Curated engineering and problem-solving guidance | 11 |

## How the program uses it

`backend/core/historical_reference_context.py` queries only the current authenticated owner's records. It removes conversational filler from the query, ranks a bounded candidate set by the vault's lexical coverage, and supplies at most three attributed excerpts, 1,200 characters each and 6,000 characters total. These are historical, unverified references; current instructions and backend permissions remain authoritative. This is lexical retrieval, not an accuracy score or a semantic-search benchmark.

The normal `/api/chat` and `/api/chat/completions` router captures references before returning either a streaming or nonstreaming response. The coding path captures references before launching its inference worker and passes only bounded reference text, never an identity credential. The worker's existing allowed-file, no-test-edit, cancellation, and execution-backend restrictions remain in force. Other verified owners can retrieve their own records through the same hooks; this corpus is not copied to unrelated Firebase accounts or exposed anonymously.

The corpus can support language, dialogue, screenplay work, creative planning, music production, coding, architecture, debugging, and project history when the request matches relevant text. Historical outcomes still require present-day verification. No answer-quality improvement or live model acceptance was measured.

## Preservation and review

The import added exactly 8,116 rows. An independent comparison against the SQLite online backup confirmed all **352,733 existing rows unchanged**, all new records fully readable with matching content hashes and source metadata, and zero duplicate import fingerprints. Foreign-owner and unauthenticated retrieval returned no references. Five local retrieval probes covered screenplay pagination, Python verification, architecture, language/dialogue, and creative music topics, returning three bounded references each in 0–0.016 seconds in that run.

The filter suppressed 2,788 duplicate chunks and 489 telemetry/unknown-memory entries. It rejects known credential patterns, explicit private-reasoning markers, sensitive personal topics and document classes, and redacts contact details and URL capabilities. Private contact lists, leads, résumés, signed contracts, addressed financial correspondence, account configuration, hidden model thoughts, tool/function payloads, duplicate full transcripts, synthetic fixtures, media, and binary database payloads were not imported. These conservative checks are not a guarantee that every historical statement is accurate or every possible private phrase has been recognized. Two invalid JSONL lines remain unchanged in their originals; their file/line locations are in the manifest diagnostics.

The final corpus is a strict subset of the independently reviewed filtered corpus. Superseded dry runs are preserved under the ignored checkpoint backup directory and were never imported. Corpus files, manifests, database backups, and private review artifacts are ignored by Git in their task directories. Nothing was committed, published, sent externally, executed from an archive, or used to activate an autonomous/outbound feature.

## Evidence

- `20261030_import/manifest.json`: source paths, hashes, exclusions, parser diagnostics, and corpus hash.
- `20261030_import/records.jsonl`: exact imported corpus; SHA-256 `725ce0cf152f895b2c9c1cc6e454cf3eaa12b764e1ba992c1635fcab2a641583`.
- `20261030_import/import_receipt.json`: all vault IDs and readback hashes.
- `20261030_import/vault_before.sqlite3`: SQLite online backup including committed WAL state.
- `../../backups/historical_knowledge_20261030/verification.json`: independent database, source-preservation, and retrieval evidence.
- `../../backups/historical_knowledge_20261030/source_changes.patch`: narrow diff against the original dirty working bytes.
- `../../backups/historical_knowledge_20261030/diagnostics.json`: resolved fixture/setup issues and retained review findings.

Validation: 54 importer/integration/local transport/GPU dispatcher tests and 27 existing owned-vault tests passed, entirely with synthetic test stores and mocked inference. Deadline expiry and cancellation during reference retrieval stop the coding worker before launch; the worker timeout uses the remaining budget after lookup. A final listener inventory confirmed no backend listener on 8080; loopback Ollama 11434, gateway 8000, and frontend 5173 remained present. No shared service was restarted. Source integration and direct database retrieval are verified; loaded application/browser/model behavior is not yet verified.

## Repeatable import

Use fresh output directories for each run. Review the dry-run corpus first, then require identical record bytes during apply:

```powershell
python -X utf8 scripts/import_historical_knowledge.py --output learning/historical_knowledge/NEW_REVIEW
python -X utf8 scripts/import_historical_knowledge.py --output learning/historical_knowledge/NEW_IMPORT --apply-local-admin --reviewed-manifest learning/historical_knowledge/NEW_REVIEW/manifest.json
```

Apply requires the existing configured operator credential to resolve to `local_admin`. The importer makes an online database backup before writing and confirms each record by full readback. A changed corpus aborts before vault mutation. Exact repeated records are idempotent; changed source hashes or provenance are separate evidence versions and can produce additional records. No scheduled ingestion, cross-owner sharing, provider call, or weight-training job was enabled.


## Evaluation guidance addition — Record186 (20261030T065933Z)

The original 8,116-record import and table above remain unchanged. A subsequent reviewed card added **5 public-guidance reference passages**, for 8,121 passages across these two batches. See [integration report](../LLM_EVALUATION_INTEGRATION_2026-10-30.md), [guidance card](../LLM_EVALUATION_GUIDE_2026-10-30.md) and [source catalog](../llm_evaluation_sources_2026-10-30.json).

The new batch is owned by the verified local_admin principal in the same historical_knowledge_v1 collection. Its manifest/receipt/online backup are in `20261030_evaluation_import`; the reviewed corpus is `20261030_evaluation_review_v2`. The first dry run remains preserved and unimported. Corpus SHA-256: `81ab8e57f7ca257834f7bfcc00b59bb2711fb2ced6153cf0d7909f6af3523da8`.

Independent read-only verification confirmed all 360,849 prior vault rows unchanged, five exact added records, no duplicate fingerprints, 360,854 total rows, all 2,006 previous source hashes unchanged, and bounded retrieval of the new card with empty unbound/foreign-owner results. Seventy focused offline tests passed; no live model-quality or loaded-application acceptance was run. Evidence is in `backups/evaluation_guidance_20261030` from the repository root. No model weights, services, activation flags or outbound settings changed.

For future single-card imports, add `--source-card learning/NEW_CARD.md` to both dry-run and reviewed-apply commands above and use fresh output directories. This preserves the existing reviewed-corpus, principal, backup and readback requirements while avoiding a full archive rescan.
