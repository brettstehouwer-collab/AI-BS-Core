# Bounded audit tool policy — Audit 212

- Query exact paths and named fields first; bound each displayed result to useful context (normally 200 lines / 4,000 tokens or less). Split independent investigations by subsystem instead of returning full recursive trees or whole documents.
- Store large manifests, diffs, and disassembly locally. Return the artifact path, count, status, and hash to the parent instead of echoing full bodies. Never print keys, passwords, tokens, or private media bytes.
- Parse application source and archives without executing their entrypoints. For behavior checks, isolate temporary files and replace external compiler, signing, network, device, and installer actions with explicit test fakes.
- After two failures of the same operation, stop repeating that operation, retain exact diagnostics, and choose an evidence-backed different method or report the limitation. Do not repeatedly control a desktop when capture/input is failing.
- Record UTC timestamps and actual runner durations where available; separate measured test time from unknown task elapsed time and provider-billed utilization. Do not invent usage totals or refunds.
- The observed ChatGPT Bad Request cause is UNVERIFIED. Payload bounding reduces audit output size, but it does not demonstrate or repair an OpenAI service fault. Keep that distinction explicit in the usage-review record.
