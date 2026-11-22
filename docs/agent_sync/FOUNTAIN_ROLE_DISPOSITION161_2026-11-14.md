# Remaining legacy role mismatch disposition — source161

A read-only classification of the retained authorized edited manuscript-copy fixture accounts for all53remaining mismatched role tokens across16source-paragraph/parser-element pairs. Source packet and canonical Fountain hashes remained unchanged. No source text, content fingerprints or occurrence identifiers were serialized.

| Source role → parser role | Tokens | Observed plain-text context |
|---|---:|---|
| Character → Action | 14 | Isolated source cues have blank lines after them;13tokens are uppercase name bases and1is not. Plain Fountain supplies no adjacent speech to identify these as cues. |
| Action → Scene Heading | 6 | The source Action matches the heading syntax and has surrounding blank lines. It contains no explicit Action marker to preserve its source role. |
| Dialogue → Action | 30 | Source Dialogue follows source Action rather than an adjacent cue; plain text lacks the retained typed relationship. |
| Scene Heading → Action | 3 | The isolated source heading matches neither current nor case-insensitive heading-prefix recognition. It has no forced-heading marker. |

These observations explain why a generic parser cannot reliably reconstruct all source roles from this flattened projection. They do not establish the intended dramatic role independently of the PDF-derived source map. Adding heuristics to recognize these particular manuscript lines would substitute guesses for retained typed metadata. No further parser rewrite is justified by these cases alone.

Disposition: retain source161's qualified dialogue-boundary fix; keep legacy reflow explicitly lossy and unqualified for role fidelity. For controlled role-preserving work, use the existing preserved FDX import, typed edits and preserved FDX export. Preserve the existing edited plain working copy separately; this review did not transfer its edits, create a rich replacement or rewrite any old source packet. Such a transfer would need explicit edit-range/source-map qualification and must not silently assign roles.

This completes the requested diagnostic/disposition for the remaining53, not full creative acceptance. Real-owner/native workflow, external Final Draft rendering and rich FDX PDF fidelity remain open. The current rich PDF route intentionally rejects preservation export with422; explicit legacy reflow remains separate. Next inspect the existing rich FDX document model and professional PDF renderer, define a supported typed-rendering contract with explicit rejection for unsupported features, and implement a focused subset using existing primitives. Do not route rich documents through heuristic Fountain parsing or claim full original-layout fidelity from a new professional-layout renderer.

Application source remains5.329.161; no version bump for this evidence-only checkpoint. Native/web156 candidates, hosted146, services, keys, ownership and user data remain unchanged. No inference, stopped UI probe retry or manual gameplay request. The original ten-goal/six-addition program stays ACTIVE/incomplete.

Evidence: `backups/fountain_roles161_20261114_v01/classification.json`. A scoped three-member report/aggregate/checkpoint archive excludes manuscript text, private stores, raw logs and earlier restricted payload. A Drive roundtrip receipt proves only those selected bytes; it is not a private manuscript backup. Closing pointers may postdate archive sealing. Source discovery also encountered nonexistent guessed helper filenames; those diagnostics remain local, no missing implementation was invented or executed.
