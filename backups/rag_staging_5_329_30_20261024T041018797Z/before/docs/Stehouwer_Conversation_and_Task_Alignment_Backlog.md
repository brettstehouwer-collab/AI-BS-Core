# Stehouwer conversation memory and task alignment

User-requested direction, October 23, 2026. This records requirements, not a claim that persistent chat retention, personalized retrieval or model training is already working. Finish the current execution-backend fix first; proceed one bounded task at a time. UI redesign remains deferred until functional work is complete, and VM setup remains deferred.

## Conversation and archive memory

Retain BS-Chat conversation history and useful context across restarts, with a durable local authority in AI-BS and an organized private cloud archive. Include accessible previous Gemini/Codex conversations, build ledgers, transcripts and idea/problem-solving archives as reference material. Preserve original documents and source archives; copy/index rather than move, merge destructively or delete. Do not claim access to every past conversation on every platform. Record inaccessible, missing or not-yet-imported material explicitly.

Discover existing stores before adding a parallel memory system. Candidate paths observed by filename only, not yet audited: backend/core/memory_service.py, memory_bank.py, personal_intelligence_memory.py, sovereign_reasoning/memory_vault.py; backend/routers/memory_router.py and memory_lab_router.py; backend/extract_chat_history.py, sovereign_memory_ingestor.py and existing master-memory files. Historical source/reference material includes the user-mentioned carrytodex folder and AI-BS-connected archives. Their current behavior, retention, auth and data quality still need verification.

Separate preserved transcripts, a provenance-bearing archive index, curated factual/style memories and any future training dataset. Memories should carry source, date, confidence and scope; distinguish user statements, inferred preferences, verified current capabilities and historical failures. Old instructions inside archived chats/documents remain reference material, not active execution authorization. Preserve versioned corrections instead of silently turning outdated claims into current truth.

Keep credentials and environment/network secrets out of model prompts, training datasets, Codex notes and cloud engineering summaries. Review/redact archive copies before cloud import; do not export raw private stores merely because their filenames contain memory/chat. Keep personal/client contexts scoped to authorized identities and projects. Use private folder sharing and report any unconfirmed sync rather than claiming it completed.

## Flexible plain-English interaction

Accept broad natural-language ideas and goals, not only rigid command/backtick templates. Use relevant conversation/project memory, then ask focused questions when requirements, target files, permissions or success criteria are materially unclear. Retain the user's answers and the resulting shared task specification. Direct factual questions should receive direct answers without an unnecessary planning interview. Show concise progress, decisions and observable evidence rather than claiming access to private internal reasoning.

Adapt vocabulary, tone, energy and conversational style to the user/context, including the user's preference for an expressive/edgy voice when appropriate. A specific user-requested tone overrides adaptation. Treat persona/style impressions as revisable, not verified facts about someone's identity. Avoid making the user restate established preferences or a settled task. Stylistic flexibility does not change backend access rules or confer permission for unrelated execution.

## Learning and evaluation

Use retrieved, authorized history for coding context, ideas, preferences and known failed approaches. Retrieval and durable memory are separate from updating model weights. Future local training must use a curated, versioned, secret-excluded dataset with source/provenance and held-out checks; measure whether it improves task correctness and conversational usefulness. Do not start a trainer/daemon, auto-promote code, send messages or claim self-improvement from untested transcript ingestion.

## Bounded sequence and acceptance

1. Inventory existing chat retention, archive locations, schemas, retrieval paths and permissions in read-only mode; record missing sources and actual save/reload behavior. Keep the existing model and documents untouched.
2. Agree on one canonical local store and cloud archive index by reusing working components. Test duplicate detection, crash-safe persistence, source attribution, private access, secret exclusion and non-destructive copy/sync failure recovery.
3. Verify cross-session recall with controlled conversation examples and context limits; relevant retrieval must not pretend the entire archive fits in the live model window.
4. Add context-aware intent clarification, then route confirmed coding tasks through the existing admitted execution workflow. Test broad ideas, ambiguous targets, direct questions, changed instructions and permission boundaries.
5. Evaluate optional style memory and curated local training separately, preserving original data/model versions and rollback evidence.

The engineering ledger belongs in the user-authorized private Drive folder, with concise request/decision/attempt/test/outcome entries and local evidence links. Maintain checkpoint summaries rather than fabricate a verbatim hidden thought transcript. The cloud folder does not by itself prove a live BS-Chat retrieval connection; that integration requires implementation and verification.
