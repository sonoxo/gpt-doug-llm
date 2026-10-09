# GPT-DOUG Math Mitochondria Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a verified symbolic mathematics solver to the GPT-Doug brain with a safe CLI, and document lawful OGA-portal access roles.

**Architecture:** A pure bounded-AST parser converts mathematical expressions into SymPy algebraic objects. A solver computes scoped polynomial or linear-system results, verifies certificates, and distinguishes proven from incomplete/open claims. The existing `gpt-doug` CLI loads the engine lazily so SymPy remains optional.

**Tech Stack:** Python 3.9+, optional SymPy 1.12+, pytest, GitHub Actions.

**Spec:** `docs/MATH_MITOCHONDRIA_SPEC.md`

## Global Constraints
- No arbitrary Python execution from mathematical input.
- Never claim arbitrary open mathematical conjectures are solved.
- No implicit network action or agency authority from ALM paperwork.
- Additive changes to existing GPT-Doug CLI and optional dependency only.

## Review Focus
- Adversarial AST expressions: rejected without evaluation.
- Nonlinear and over-degree systems: explicit `outside_scope`.
- Extraneous, partial and non-real roots: never represented as verified real solutions.
- Missing variables/contradictions: distinct statuses.
- Provenance in saved results: only opt-in, never store an unverified theorem as an established fact.

---

### Task 1: Safe symbolic engine
**Files:** Create `gpt_brain/math_mitochondria.py`; Test `tests/test_math_mitochondria.py`.
**Interfaces:** `MathMitochondria.solve(list[str], variables=None, domain='real')`, `.verify(str)`, `.theory(str)` return JSON-serializable dicts.
- [ ] Write tests for exact roots, linear systems, identities, missing constraints, unsafe syntax and open theories.
- [ ] Run `pytest tests/test_math_mitochondria.py -q` and confirm expected missing-module error.
- [ ] Implement safe parser, bounded computation and substitution checks.
- [ ] Run tests and confirm green.

### Task 2: CLI + documentation
**Files:** Modify `gpt_brain/cli.py`, `pyproject.toml`; create CLI unit tests and `docs/ALM_OGA_ACCESS_ROUTE.md`.
**Interfaces:** `gpt-doug math solve ...`, `gpt-doug math verify ...`, `gpt-doug math theory ...`, optional `--remember` supported only for verified results.
- [ ] Add CLI tests for commands and non-authorized save attempts, verify red.
- [ ] Implement CLI adapter and optional SymPy dependency.
- [ ] Run complete math suite; capture local smoke output.
- [ ] Commit the patch to a GitHub feature branch and open a reviewable PR; no merge without review.
