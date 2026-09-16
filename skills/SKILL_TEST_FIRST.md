# AI-BS SKILL: Autonomous Test-Driven Development (/test-first)

## Objective
Enforce strict Test-Driven Development (TDD) red-green-refactor workflows. Guarantee that implementation code is authored exclusively against verified failing test fixtures, preventing phantom passes and regression escapes.

## Trigger Conditions
- Operator enters `/test-first [feature_description]` or `/tdd [target_module]`.
- Mandated for new module initialization, API endpoint creation, or core algorithmic changes.

## Execution Protocol

### Phase 1: Red (Failing Test Creation)
1. **Target Isolation:** Identify the module under development (e.g., `src/services/telemetry.py` or `backend/core/telemetry.py`).
2. **Fixture Generation:** Draft a new test file under the appropriate `tests/` or `scratch/` directory (e.g., `tests/test_telemetry.py`).
   - Define minimal, deterministic inputs and assertions covering edge cases, null states, and boundary conditions.
3. **Execution & Failure Verification:**
   - Execute the test runner via host PowerShell:
     ```powershell
     pytest tests/test_telemetry.py
     ```
     or
     ```powershell
     npm test -- tests/telemetry.test.ts
     ```
   - **Hard Rule:** The test **MUST fail** due to missing implementation (e.g., `AttributeError`, `NotImplementedError`, or assertion mismatch). If the test passes immediately, reject the test structure as invalid and revise.

### Phase 2: Green (Minimal Implementation)
1. Write the minimal functional code required to satisfy the assertions.
2. Maintain strict scope: do not write speculative features, secondary abstractions, or unprompted helpers.
3. Re-run the test suite.
4. **Circuit Breaker:** If the test fails twice consecutively on the same error signature, halt execution, inspect the stack trace, and adjust the implementation.

### Phase 3: Refactor & Verification
1. Clean up implementation: eliminate duplication, enforce monosemic naming, and optimize performance.
2. Re-run the entire test suite to guarantee zero regression:
   ```powershell
   pytest tests/
   ```
3. Create a `.bak` backup of modified files before committing changes to Git.

## Output Format
Publish the final execution result directly to `task.md` and log:

```markdown
### TDD Cycle Completed: [Module Name]
- **Failing Baseline:** [Initial error signature / test assertion that failed]
- **Implementation:** [Surgical diff summary of applied code]
- **Passing Result:** [Total tests passed, execution duration in ms]
- **Verification Command:** `[Exact command to re-run test suite]`
```
