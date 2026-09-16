# AI-BS SKILL: Static Analysis & Security Audit (/audit)

## Objective
Execute a rigorous, read-only pre-flight inspection across modified files and repository architecture before production builds, staging commits, or deployments. Identify syntactic errors, AST defects, exposed secrets, circular dependencies, and unlinked assets.

## Trigger Conditions
- Operator enters `/audit` or `/audit [target_directory|file]`.
- Triggered automatically as Step 4a before executing `npm run build` or `firebase deploy`.

## Execution Protocol

### 1. Scope Determination
- Query Git status to isolate unstaged, staged, and untracked modifications:
  ```powershell
  git status --porcelain
  ```
- If no files are specified, scope defaults to all modified files since the last checkpoint commit in `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.

### 2. AST & Syntax Inspection
- **Python**: Execute AST integrity validation:
  ```powershell
  python -m py_compile <target_file.py>
  ```
- **TypeScript/JavaScript**: Execute type and lint verification without emitting build artifacts:
  ```powershell
  npx tsc --noEmit
  ```

### 3. Secret & Credential Scanning
Scan scoped diffs against regex patterns for high-entropy strings and credentials:
- Private Keys (`BEGIN (RSA|EC|OPENSSH) PRIVATE KEY`)
- API Tokens (`ghp_`, `sk-`, `AIzaSy`, Bearer JWTs)
- Raw Database connection strings containing embedded passwords.
- **Enforcement Rule:** If an exposed secret is detected, abort immediately with status code 1. Do not log the secret in plain text.

### 4. Dependency & Mirror Integrity
- Audit `package.json` and `requirements.txt` for undeclared imports used in mutated files.
- Verify that targeted changes do not break file-path symmetry across designated frontend mirror paths.

## Output Format
Generate a Markdown summary to stdout and write the log to `.aibs/audit_report.json`:

```markdown
### AI-BS Audit Report: [PASS | FAIL]
- **Target Scope:** [Files scanned count]
- **AST / Syntax Check:** [Clean | Errors flagged with line numbers]
- **Secret Scan:** [Clean | Violation detected]
- **Dependency Scan:** [Clean | Missing dependencies listed]
- **Actionable Remediation:** [Concrete command or code fix, if failed]
```
