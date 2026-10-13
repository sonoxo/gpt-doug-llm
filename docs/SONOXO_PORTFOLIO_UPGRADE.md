# GPT-Doug — Sonoxo GitHub Fleet Upgrade

## Scope and measured baseline — 2026-10-13

The authenticated GitHub owner inventory identified **210** accessible Sonoxo-owned repositories, of which **206 public** and **4 private**. This public repository contains **only the 206 verified-public metadata records**; no private repository names, paths, code, pull-request titles, credentials, or access details are recorded in the public artifacts.

The owner-wide open PR search observed **68** PRs, **51** of which map to the public inventory; only those 51 public PR references are stored here. PR counts are a point-in-time observation, not an assertion of merges or code health.

The publicly indexed repositories have different default branches (`main`, `master`, `develop`, `development`, `Main` and others). Never hardcode `main` when proposing changes to individual repos.

### Data provenance

- `data/sonoxo_fleet/observed_public_repositories.json`: GitHub owner inventory, strictly public rows, observed date, exact default-branch labels and size metadata.
- `data/sonoxo_fleet/observed_open_prs.json`: public-only PR references, each validated to a GitHub Sonoxo repository path.
- `sonoxo_fleet/core.py`: bounded snapshot validation, SHA-256 digest, full public portfolio review plan and **explicitly opt-in read-only GitHub API refresh**.
- `sonoxo_fleet/viewer.py`: self-contained local repository/PR visualization, no CDN, remote scripts, browser network API or mutation controls.
- `.github/workflows/sonoxo-portfolio-audit.yml`: artifact-producing PR review and scheduled public inventory sync, repository token scoped to contents:read.
- `.github/workflows/ecosystem-readme-refresh.yml`: hardened diagram workflow; review artifacts instead of direct pushes, destructive resets and checkouts with persistent write credentials.

### Local use

```bash
cd ~/Downloads/gpt-doug-warfighter
python3 -m sonoxo_fleet status
python3 -m sonoxo_fleet audit --output build/sonoxo-fleet
open build/sonoxo-fleet/portfolio.html
```

To regenerate existing outputs safely, append `--force` to the **local output command only**. It does **not** mean a Git push/force merge. For an explicit fresh public API read:

```bash
python3 -m sonoxo_fleet sync-public --output build/sonoxo-fleet-live
open build/sonoxo-fleet-live/portfolio.html
```

If the API rate-limits unauthenticated reads, a user may set a scoped GitHub credential in their own local environment or run the scheduled read-only GitHub Actions job. Do not paste tokens into chat, GitHub code, generated HTML or CI logs. The public refresh intentionally never lists private repositories.

Run tests and verify reproducibility with:

```bash
python3 -m unittest discover -s tests -p 'test_sonoxo_fleet.py' -v
python3 -m compileall -q sonoxo_fleet
```

## Actual upgrade policy

The user requested ecosystem-wide updates. A universal bulk merge is **not** a valid proof that independently maintained third-party forks and private projects will run correctly. The first deliverable is a source-backed inventory, a review queue, and a safe CI policy. Individual code or dependency upgrades must have separate commits and PRs in the **correct** repository/default branch.

Upgrade gate sequence:

1. Verify repository ownership, upstream fork status, legal license and supported SDK/API version.
2. Inspect the repository's actual default branch and tracked build/test commands; preserve forks and experimental branches.
3. Open a dedicated minimal change on a feature branch; make dependencies lockfile-aware and obey pinning.
4. Run relevant formatting, builds, tests, vulnerability checks and security reviews; record failures without hiding them.
5. Require human review and branch protection/required checks; merge only after approvals.
6. Observe deployed health independently where deployment is authorized; source code/CI passing is not real-world compliance or operational approval.

**Do not automatically merge or mutate all 210 repositories.** Never use force push or auto-merge as a substitute for per-repo testing. Never enable unauthorized remote network control, third-party software mirroring or new secrets. Privately owned repositories must be assessed in authorized private workflows and must **not** be indexed in a public artifact.

### Review priority

Current known integration points include GPT-Doug, ZYRA, XUNIA, ATAK-CIV, ATAK-Maps, geospatial visualization, MECHA/Fabrication Brain, and defensive test infrastructure. This is a **prioritization map, not an assertion** that all integrations are merged into their default branches.

Existing review work:

- GPT-Doug Fabrication Brain: https://github.com/sonoxo/gpt-doug-llm/pull/358
- TAK-GEO CoT/GeoJSON viewer: https://github.com/sonoxo/gpt-doug-llm/pull/359
- ATAK-Maps ontology atlas: https://github.com/sonoxo/gpt-doug-llm/pull/360
- TAK documentation registry: https://github.com/sonoxo/gpt-doug-llm/pull/361
- Civilian ATAK third-party source: https://github.com/sonoxo/atak-civ/pull/1

The linked branches are **review proposals**, not proof of release or signed ATAK software. Protected TAK resources and any proprietary vendor integration remain subject to applicable licenses, security reviews and government-authorized build environments.

## Uploaded USPTO source — architectural research only

The user also supplied text copied from USPTO Patent Public Search. It identifies **US 20260304275 A1**, published **2026-10-01**, titled **“Systems and Methods for Controlling Communications, Power, and Computing.”** Its abstract references transportable/body-worn communications, consolidated status dashboards and modular systems. Other search results include **US 20260288998 A1**, concerning geospatial pattern privacy, and **US 20260101211 A1**, concerning radio-frequency anomaly detection.

These are **third-party public patent references**, not Sonoxo-owned code, a patent license, production integration proof, or a legal freedom-to-operate opinion. Concepts independently eligible for review include **read-only health summaries**, **data provenance**, **operator review gates**, **network-link availability displays**, **simulated maintenance alerts**, and **privacy-respecting geospatial dashboards**. Do not copy claim language into implementations, assume use rights, or deploy autonomous RF/vehicle/network control from patent descriptions. Any novel commercial embodiment requires independent IP and safety review.

## Result interpretation

The read-only fleet dashboard is a real local application generated from versioned data, but it is **not** a 210-repository code upgrade, a network-connected situational awareness console, a remote build farm, or a deployed monitoring agent. CI artifacts represent public metadata only. The remaining work is intentionally staged as separate, testable PRs.
