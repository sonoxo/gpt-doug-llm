# Sonoxo Fleet Upgrade Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task.

**Goal:** Provide read-only evidence about Sonoxo GitHub upgrade readiness and create safe dependency-update PRs for first-party repositories.

**Architecture:** GPT-Doug-LLM provides the inventory and a read-only scheduled report; each Sonoxo-authored repository uses its own Dependabot and CI. Existing upstream forks retain upstream ownership and do not receive blind upgrades.

**Tech Stack:** Python standard library, unittest, GitHub REST, GitHub Actions, Dependabot.

**Spec:** `docs/SONOXO_FLEET_UPGRADES.md`

## Global Constraints

- Scanner uses GET requests only and workflow permission `contents: read`.
- No automatic merge or deployment; breaking changes require review.
- Preserve upstream fork branches, attribution and licenses.
- Do not claim private repos were covered by the public-owner API.
- CI failures are blockers, not checks to bypass.

## Review Focus

- Multi-page GitHub repository listings without truncation
- Forks classified upstream-sync-first
- HTTP failures reflected as inspection-error
- Repositories with no manifests classified for manual review
- Repository `.github` absent or inaccessible

---

### Task 1: Read-only scanner

**Files:** `scripts/sonoxo_fleet_upgrader.py`, `tests/test_sonoxo_fleet_upgrader.py`

**Interfaces:** `list_owner_repositories(api, owner)`, `classify_repository(repo, root_names, github_names, read_error=None)`, `scan_repositories(api, repositories)`, `render_markdown(records, owner)`

- [x] Write tests first and observe failure.
- [x] Implement public pagination, classification and JSON/Markdown output.
- [x] Run 11 focused unittest cases locally.
- [ ] Confirm PR workflow tests on Linux.

### Task 2: Scheduled reporting and documentation

**Files:** `.github/workflows/sonoxo-fleet-upgrade-audit.yml`, `docs/SONOXO_FLEET_UPGRADES.md`

- [x] Add pull-request tests, Tuesday schedule and manual dispatch.
- [x] Keep GitHub token read-only and report-artifact output.
- [x] Verify YAML structure and Python syntax locally.
- [ ] Confirm scheduled report is active only after approved merge.

### Task 3: Baseline dependency PRs

**Files:** Per-repository `.github/dependabot.yml`; `gpt-doug-llm/.github/dependabot.yml`

- [x] Inspect original versus upstream fork, root manifests and existing Dependabot.
- [x] Open isolated draft PRs for eight suitable first-party repositories.
- [x] Check current CI outcomes; record failures and no-check projects.
- [ ] Merge only after independent review and required checks.

### Task 4: Related CI fault isolation

**Files:** Per-repository separate repair PRs.

- [x] Identify GPT-Doug shell syntax and privileged workflow trigger failures from logs.
- [x] Identify Eyeris submit-versus-select ambiguity and incorrect privacy assertion.
- [x] Create separate reviewable fix PRs.
- [ ] Verify all associated CI and integrate only through reviewed merges.
