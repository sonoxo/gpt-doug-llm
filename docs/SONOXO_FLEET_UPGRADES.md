# Sonoxo fleet upgrade process

**Control plane:** `sonoxo/gpt-doug-llm`.

This tool inventories **public repositories owned by Sonoxo** using GitHub's public user API. A repository token increases API quota but does **not** extend this scanner to private repositories. Review private repositories separately using an explicitly authorized account. This is a read-only readiness report, not a deployment or cross-repository updater.

## Run locally

```bash
python -m unittest discover -s tests -p 'test_sonoxo_fleet_upgrader.py' -v
GH_TOKEN="${GH_TOKEN:-}" python scripts/sonoxo_fleet_upgrader.py --owner sonoxo --output-dir reports/sonoxo-fleet
```

The token is optional for public repositories; unauthenticated API rate limits may prevent a complete scan. Results are saved to `audit.json` and `audit.md`. An inspection error produces a non-zero exit code, rather than reporting false compliance.

The scheduled GitHub Actions workflow runs **each Tuesday** (UTC schedule) or by manual dispatch. It uses only repository read permissions and GET requests. It cannot modify files, merge PRs, manage credentials, deploy software or automatically update packages.

## Review and rollout

1. Inventory every visible public repository and preserve fork/archived status.
2. Prioritize original Sonoxo code and existing update PRs; do not duplicate Dependabot configurations.
3. For a fork, compare current upstream and local branches first. Preserve licensing, attribution and fork-specific changes; do not blindly overwrite it.
4. Propose minimal native Dependabot entries for *observed* manifest ecosystems, grouped nonmajor updates and bounded open-PR counts.
5. Run project CI, code review and security checks before merging. Major dependency changes and production deployments need dedicated approval.
6. Record exact failing checks and limits. A created Dependabot PR or passing scanner test is not proof of successful dependency migration.
7. Use per-repository GitHub-native permissions. Do not put a fleet-wide personal access token in workflows.

## Audit limitations

Only root manifests and `.github/workflows` are classified. Nested monorepos, vulnerabilities, exact version freshness, runtime behavior, API contract breaks and private repos require separate inspections. A `--limit N` run is explicitly partial. Unavailable repos are reported as `inspection-error`, and results are not called complete if the scan fails.

## Release boundary

Upgrade PRs are reviewable proposed changes. Nothing is automatically merged or deployed. Any cross-repository rollout needs verified CI outcomes and an explicit authorized merge/deployment decision.
