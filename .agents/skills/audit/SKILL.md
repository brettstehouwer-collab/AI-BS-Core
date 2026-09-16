---
name: audit
description: Pre-flight AST, syntax, dependency, and secret scanning before builds or deployments.
---

# AI-BS SKILL: Static Analysis & Security Audit (/audit)

## Objective
Execute a rigorous, read-only pre-flight inspection across modified files and repository architecture before production builds, staging commits, or deployments. Identify syntactic errors, AST defects, exposed secrets, circular dependencies, and unlinked assets.

## Trigger Conditions
- Operator enters `/audit` or `/audit [target_directory|file]`.
- Triggered automatically before executing `npm run build` or `firebase deploy`.

## Execution Protocol
1. **Scope Determination:** Inspect `git status --porcelain` for modified or untracked files.
2. **AST & Syntax Inspection:** Run `python -m py_compile <target_file.py>` and `npx tsc --noEmit`.
3. **Secret & Credential Scanning:** Scan for high-entropy tokens (`BEGIN PRIVATE KEY`, `ghp_`, `sk-`, `AIzaSy`, Bearer JWTs, database passwords).
4. **Dependency & Mirror Integrity:** Verify undeclared imports and multi-mirror byte symmetry.
