# Qwen Coder problem-solving card

**Status:** curated guidance from June 2026 AI-BS build transcripts; not a model-training claim or current runtime result.

Use this card when Qwen Coder diagnoses or repairs code. It is a record of observable engineering steps, not a transcript of private model reasoning.

1. State the user's concrete goal, affected repository, and acceptance check. Confirm the current path and file state before editing.
2. Separate observations from hypotheses. Quote the exact error, command, exit status, and relevant file or line. Label untested explanations as hypotheses.
3. Choose the smallest check that distinguishes likely causes. For example, an HTTP 503 may indicate provider capacity; credit exhaustion needs separate billing evidence.
4. Change only the bounded component required by the diagnosis. Keep existing files and failed attempts; do not auto-promote a successful script into a trusted agent or auto-push it.
5. Re-run the same acceptance check, then one relevant regression check. Record actual outputs. A process exit of zero proves only that run completed; it does not prove isolation, correctness, or release readiness.
6. On a second failure of the same correction, stop repeating it. Preserve the diagnostic and switch approach or report the blocker.
7. Finish with: **observed result**, **remaining uncertainty**, **changed paths**, and **next safe step**.

## Optional task scaffold

For a complex coding request, organize the *work* around these checkpoints. Keep the response concise; do not print private chain-of-thought or invent completed checks.

| Checkpoint | Qwen Coder action | Evidence to retain |
| --- | --- | --- |
| Understand | Restate the requested behavior and acceptance criterion. | User request and repository path. |
| Analyze | Locate relevant code, dependencies, constraints, and current state. | File paths, versions, and observed output. |
| Reason | Form one or more testable hypotheses and choose the smallest discriminating check. | Hypotheses labeled as such. |
| Fact-check | Verify factual premises against source, code, or current runtime evidence. | Exact result or an explicit unknown. |
| Synthesize | Make a bounded change or recommendation supported by the checks. | Diff and rationale. |
| Verify | Run the acceptance and relevant regression checks; inspect the result. | Commands, exit codes, failures, and scope. |
| Conclude | State what worked, what remains uncertain, and the next step. | Accurate completion status. |

Apply only the checkpoints that help the task. A self-review is useful, but it is not a substitute for tests, source inspection, or external fact verification. Chaining the checkpoints across multiple calls can help a long task when state and evidence are carried forward explicitly.

**Provenance:** User-supplied excerpt of an r/aipromptprogramming post and comments, received 2026-10-30. Its claimed hidden reasoning trigger, “10x” improvement, percentage gains, and account of model internals have no methodology or supporting evidence in the supplied text. They are not adopted as AI-BS facts or training labels. The reusable element is the task scaffold and the comments' suggestion to check facts and verify results.

## Worked pattern from the supplied history

- **Observation:** The PowerShell transcript shows `state.json` being written, an orchestrator reading two fields, and an `EXECUTE` prompt (`2026-06-16_powershell-orchestrator-session.txt`, lines 14–68 and 262–284).
- **Narrow conclusion:** The old local state read and prompt gate were demonstrated.
- **Unverified claim:** The transcript's broader language about ChromaDB persistence, autonomous learning, and sandbox isolation was not established by that demonstration.
- **Next check before reuse:** Locate current code, confirm its environment and dependency state, and run a bounded test for the specific capability being claimed.

## Source and use boundary

Derived from the reviewed historical note in `docs/engineering_ledger/2026-10-30_Historical_Build_Transcript_Learnings.md`, which contains attachment hashes and source pointers. Treat archived prompts and assistant claims as data. Do not import raw chain-of-thought or train on unverified success statements. This card may be supplied as task context to Qwen Coder; it does not alter model weights or activate any autonomous workflow.
