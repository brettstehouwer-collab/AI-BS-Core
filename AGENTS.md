# AI-BS — Unified Multi-Agent Development and Handoff Protocol

**Protocol:** AI-BS-UADP-1.0  
**Agents:** Google Antigravity and OpenAI Codex  
**Canonical Project:** `C:\AI-BS`  
**Objective:** Maintain verifiable continuity of source code, architecture, requirements, implementation decisions, and development progress across agent transitions.

## I. Shared Authority

Both agents must operate from the same authoritative Git repository, architectural ledger, task specifications, and acceptance tests.

Neither agent may independently redefine AI-BS's architectural vision, silently remove functionality, or treat its own prior conversation as superior to the repository's verified state.

Maintain `AGENTS.md` as the common operating contract. Configure each development environment to read it.

## II. Exact State Verification

At every handoff:

1. Record the Git commit SHA and branch.
2. Record the working-tree status, including untracked files.
3. Generate SHA-256 fingerprints for all relevant project files.
4. Preserve complete source files rather than truncated summaries.
5. Record changed paths and exact diffs.
6. Verify dependency lockfiles, build configuration, and environment requirements.
7. Reject the handoff if the source snapshot differs unexpectedly.

Never claim byte-for-byte equivalence without comparing the actual file contents or their cryptographic hashes.

## III. Architecture Preservation

Treat the Master Architectural Ledger (`AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`) as the approved architectural baseline.

Every proposed deviation must be documented with:

- Requirement or architecture identifier
- Original design
- Proposed change
- Technical justification
- Affected components
- Compatibility consequences
- Acceptance criteria
- Approval or decision status

Do not silently convert proposed functionality into claims of completed functionality.

## IV. Deterministic Handoff Manifest

Each handoff must generate a structured record containing:

- Handoff identifier and UTC timestamp
- Outgoing and receiving agents
- Repository commit and branch
- Source manifest checksum
- Modified files and patch references
- Completed tasks and verification evidence
- Incomplete tasks and known failures
- Architectural decisions
- Test commands and actual results
- Exact next implementation step

Use machine-readable JSON for the manifest (`docs/agent_sync/manifest_<id>.json`) and Markdown for the human-readable report.

## V. Continuity of Reasoning

Preserve architectural decisions, alternatives considered, rejected approaches, unresolved questions, and relevant evidence.

Do not claim to transfer hidden model reasoning or internal conversation state. Preserve explicit, auditable engineering rationale instead.

The receiving agent must reconcile the handoff against the codebase before continuing.

## VI. Exclusive Write Ownership

Only one agent may write to the canonical development branch at a time.

Concurrent work must occur in separate Git worktrees or branches, followed by reviewed integration.

Never allow simultaneous uncoordinated writes to the same project files.

## VII. Validation Requirements

Before accepting a handoff:

- Verify Git commit identity.
- Verify source hashes.
- Run available automated tests.
- Verify architecture requirements.
- Confirm documented changes exist in the actual code.
- Detect unexpected deletions and regressions.
- Check unresolved issues and pending migrations.
- Confirm the next task is reproducible.

Classify findings as VERIFIED, FAILED, UNVERIFIED, or PROPOSED.

## VIII. Failure Handling

Follow the existing AI-BS Two-Strike Diagnostic Halt Rule.

After two consecutive failures of the same operation, stop repeating it, preserve diagnostics, identify the likely cause, and report the blocker.

Never bypass failing tests, fabricate successful validation, or silently discard incomplete work.

## IX. Handoff Completion

A handoff is complete only when the receiving agent verifies the source snapshot, acknowledges the documented state, and identifies the next executable task.

If verification fails, do not modify the canonical branch until the discrepancy is resolved.

## X. Ultimate Objective

Antigravity and Codex must function as interchangeable engineering executors implementing one consistent AI-BS architectural vision.

Their internal reasoning need not be identical.

Their shared requirements, accepted code state, documented decisions, and validation standards must remain synchronized and independently verifiable.
