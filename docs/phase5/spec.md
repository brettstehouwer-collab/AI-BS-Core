# Selected project input preparation

Status: approved-plan implementation specification; execution remains unavailable.

Reuse `coding_vm_inputs.validate_vm_inputs`, `coding_vm_staging.stage_vm_inputs` and the existing artifact validator. Add input schema version2; retain version1 Python behavior. Do not introduce another task store, database, execution route or host runner. Keep exact host-admission JSON equality and the existing identities, hashes, file-count/byte/manifest/deadline limits. Actual authorization provenance, bounded wire decoding, secret-content scanning and runtime provisioning remain separate prerequisites.

New larger-project callers must explicitly require version2; retaining the legacy version1 Python-check format is not permission to bypass the newer protected-file policy. The pure validator cannot establish the caller's authority. Node test arguments are literal selected paths, with leading options and bracket/brace patterns rejected. Validate a detached JSON copy of the exact compared admission.

Version2 permits explicitly selected Python and JavaScript/JSX implementation files. At least one implementation file must be editable. Recognized test files/directories and package/build/test configuration, dependency manifests and lockfiles cannot be editable. Node modules, virtual environments and credential paths are excluded. Files must have collision-free canonical relative paths. Staging copies exactly the supplied approved bytes, including relevant uncommitted source content; no repository scan, HEAD substitution, dependency installation or ambient-file inclusion occurs here. This does not prove those bytes came from the current repository; authenticated snapshot admission must establish that.

Fixed verification profiles are selected by the operator and bound by the admission:

- Python: `python -m unittest` with explicit selected verification-module names.
- JavaScript: `node --test` with explicit selected `.js`, `.mjs` or `.cjs` verification files.
- Existing npm project: `npm run SCRIPT`, no additional flags; the root package manifest must contain that exact script and be an immutable dependency. An explicitly selected root npm lockfile must also be immutable. Package scripts remain untrusted code for the future guest; this validation does not make them safe on the host or prove their test coverage.

Require Python checks for editable Python and JavaScript checks for editable JavaScript. JSX requires an existing npm-project check; arbitrary transpiler/Node flags, shell commands, dynamic installation and model-selected checks are outside this profile. TypeScript/TSX comes later. Do not claim syntax, tests, installed dependencies or offline execution have been verified merely because a manifest passes.

Architecture decisions: reuse retained JSON evidence instead of new persistence; preserve exclusive staging and resource ceilings; reject before transfer rather than repairing/replaying a bad manifest; preserve immutable outputs through the existing admission hash/artifact validator. No network call, subprocess, environment read or filesystem access inside the pure validator. The existing `windows_vm` guard remains fail-closed, and the limited `trusted_host` workflow is unchanged. Real isolation acceptance, controller integration, larger-project execution demonstrations and release gates remain incomplete.

Verification: successful Python, native Node, React and mixed manifests; exact check/role/byte admission; protected test/lock/config rejection; malformed package data and unsupported commands; missing selected tests or runtime checks; path/collision/size limits; version1 regressions; actual synthetic Windows staging; and rejection of changed immutable returned files. Use synthetic code only; do not execute its commands. Preserve fixtures and before-images.

## Selected source capture (v5.329.41)

The Windows `coding_repository_snapshot.capture_repository_snapshot` helper now captures exact current selected source bytes under held read/directory handles, scoped by a trusted caller allowlist, with sizes/hashes and stable real Git HEAD. It rejects unsafe paths, ordinary link/swap attacks and recognized secret/binary content; returns SNAPSHOT_ONLY/authorizedfalse/executedfalse. It is not wired to authentication/admission yet. See [repository snapshot contract](REPOSITORY_SNAPSHOT.md). Authenticated policy/journal binding is next; all actual VM/larger-project execution gates remain incomplete.

## Authenticated prepare-only API (v5.329.42)

Preview/prepare/read/recover now bind the verified owner, server repository policy, exact selected source and fixed check profiles. Owner-scoped immutable records reuse the request journal; no VM image/admission is fabricated and no project checks run. See [prepare-only contract](PREPARE_ONLY_ADMISSION.md). API/source/live evidence is retained; frontend planning/history wiring and actual isolated execution remain pending.
