# Personal memory ownership and reference authority

Target: source v5.329.39, one bounded Phase 4 prerequisite. The global manual archive, unified/vector recall, full browser acceptance and model training remain separate pending work.

## Verified defects and decisions

The legacy personal engine defaults to brett/stehouwer_publishing; read/relevant/activity/delete SQL filters only the tenant, ignoring the user parameter. The personal API accepts caller-supplied tenant/user labels without its own administrator dependency. Dispatcher and cross-model calls omit identity, so default personal data enters every caller's model prompt. Automatic regex extraction pins directive-like text, and the formatter calls records verified directives that MUST guide the answer. This does not establish provenance or authorization.

Reuse the existing administrator principal resolver and private conversation authorization. Bind a server-verified principal to request context; copy that context into existing asyncio.to_thread calls and reset it after the request. Map the explicit local administrator key to its historical brett namespace, preserving existing data. Each Firebase principal gets its own stable user namespace; do not infer ownership of historical records from a header, email, body field or display name. No automatic history migration.

All personal reads, searches, updates, events and deletion predicates require the admitted client AND user. Supplied legacy client/user fields may only match that identity. Add an independent authenticated scope dependency on the personal router. Missing verified scope cannot read legacy default data; automatic background logging skips rather than invent an owner. Existing authorized explicit deletion semantics are not exercised against production records in this task.

Personal memories are historical unverified references, with source/record/outcome labels and a bounded prompt size. Pinning affects ranking only. Automatically extracted claims remain unpinned/unverified; timestamp collisions cannot overwrite earlier extracted claims. Known credential patterns/environment secrets are excluded from derived prompt/claim extraction; raw conversations remain in their existing preservation path. Pattern scanning is not a guarantee of detecting every secret. No archived statement can grant backend privileges or change execution approval rules.

## Acceptance

Use synthetic actual SQLite/FTS, extracted actual engine/middleware source, standalone real FastAPI personal routes and controlled verified-principal delegates. Test same-tenant different-user isolation, forged tenant/user labels, no-scope behavior, actual async/thread/stream context propagation and reset, standalone API denial, bounded/unverified prompt references, unpinned inference, credential exclusion and collision preservation. Do not import the real personal singleton while testing fixtures.

Before controlled live changes, retain a consistent private local snapshot of the existing personal database plus the existing vault/master/document backups. Verify current data without printing private facts. Restart only the identity-verified quiescent main service with the six activation flags disabled, then check access, local-admin history compatibility, ordinary chat and preservation. Actual Firebase browser access remains pending saved localhost permission. No global multi-user privacy, RAG quality, model-weight training, VM isolation or publication claim.
