---
name: test-first
description: Autonomous red-green-refactor test-driven development loop enforcing failing tests before implementation.
---

# AI-BS SKILL: Autonomous Test-Driven Development (/test-first)

## Objective
Enforce strict Test-Driven Development (TDD) red-green-refactor workflows. Guarantee that implementation code is authored exclusively against verified failing test fixtures, preventing phantom passes and regression escapes.

## Trigger Conditions
- Operator enters `/test-first [feature_description]` or `/tdd [target_module]`.
- Mandated for new module initialization, API endpoint creation, or core algorithmic changes.

## Execution Protocol
1. **Phase 1: Red (Failing Test Creation):** Draft test fixture; execute runner via PowerShell; verify test FAILS before authoring code.
2. **Phase 2: Green (Minimal Implementation):** Write minimal functional code to satisfy assertions; re-run test; apply dual-failure circuit breaker.
3. **Phase 3: Refactor & Verification:** Clean up code; re-run full test suite; stage `.bak` backup before commit.
