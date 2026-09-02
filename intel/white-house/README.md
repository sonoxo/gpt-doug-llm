# 🏛️ THE WHITE HOUSE DAILY → THE BLACK HOUSE

**First-party public-source watch for GPT-DOUG-LLM / RVIA.**

This lane applies the same operating concept described by Palantir's August 27, 2026 AI FDE + Automate announcement — **when this happens, do that** — using an independent GitHub Actions implementation.

## Automation

```text
DAILY SCHEDULE
    ↓
WHITEHOUSE.GOV FIRST-PARTY PAGES
    ↓
DISCOVER + DEDUPE
    ↓
CAPTURE TITLE / DATE / CATEGORY / URL / BODY HASH
    ↓
MISSION TAGGING
    ↓
SHADOW GLASS SOURCE DISCIPLINE
    ↓
THE BLACK HOUSE DAILY ARTIFACT
    ↓
GIT COMMIT + PUSH
```

GitHub workflow: [`../../.github/workflows/white-house-daily.yml`](../../.github/workflows/white-house-daily.yml)

Collector: [`../../scripts/white_house_daily.py`](../../scripts/white_house_daily.py)

Daily output: [`./daily/`](./daily/)

## Authoritative source set

The automation reads only these public first-party White House pages:

- https://www.whitehouse.gov/news/
- https://www.whitehouse.gov/fact-sheets/
- https://www.whitehouse.gov/releases/
- https://www.whitehouse.gov/briefings-statements/
- https://www.whitehouse.gov/remarks/
- https://www.whitehouse.gov/research/
- https://www.whitehouse.gov/presidential-actions/executive-orders/
- https://www.whitehouse.gov/presidential-actions/presidential-memoranda/

## Intelligence rule

```text
WHITE HOUSE PUBLICATION = VERIFIED FACT THAT THE WHITE HOUSE PUBLISHED IT
WHITE HOUSE ASSERTION ≠ INDEPENDENTLY VERIFIED FACT
```

Every collected item is labeled `SOURCE_STATEMENT` until an analyst or downstream agent corroborates the underlying claim against additional evidence.

The daily job does **not** perform partisan persuasion, sentiment targeting, voter profiling, or demographic political messaging. It is a provenance-first official-source monitor.

## What is stored

For each newly discovered publication:

- title;
- canonical source URL;
- publication category;
- publication date when exposed by the source page;
- retrieval provenance;
- source tier `T1_OFFICIAL_PRIMARY`;
- SHA-256 of normalized article text;
- mission-relevance tags;
- optional HTML meta description;
- explicit `independent_verification: false` state.

Full article text is not copied into the repository.

## Mission tags

The deterministic collector can tag items for downstream routing when titles/descriptions mention:

- AI / machine learning;
- cyber / cryptography / zero trust;
- defense / military / national security;
- space / NASA / satellites;
- technology / semiconductors / quantum / compute;
- supply chains / critical minerals / industrial base;
- energy / power-grid issues;
- intelligence / counterintelligence.

Tags are routing metadata, not analytic conclusions.

## Palantir Automate alignment

Reference: https://www.palantir.com/docs/foundry/announcements#configure-business-automation-with-automate-in-ai-fde

Palantir documents AI FDE Automate as supporting time schedules and object-set conditions, effects through actions/AIP Logic/notifications, scoped automations, retries/fallback actions, pause/resume/expiration, and downstream workflow testing.

This repository maps that concept as:

| Palantir AI FDE / Automate concept | Independent Black House implementation |
|---|---|
| scheduled condition | GitHub Actions cron |
| object/source condition | newly discovered canonical URL |
| effect | write daily JSON + Markdown |
| scope | `sonoxo/gpt-doug-llm` repository |
| retry/failure evidence | GitHub Actions job status + collection gaps |
| downstream effect | daily git commit/push |
| reviewable history | Git commit history + source hashes |

This mapping is conceptual and does not imply a live Palantir enrollment or Palantir endorsement.

## Schedule

The workflow runs at `12:00 UTC` every day and can also be started manually with `workflow_dispatch`.

Because GitHub Actions scheduled execution can be delayed by platform load, the timestamp stored in each artifact is the actual retrieval time, not an assumed execution time.

## Independence

The Black House / RVIA / GPT-DOUG-LLM project is independent and open source. References to the White House, Executive Office of the President, Palantir Technologies, Foundry, AIP, AI FDE, or Automate identify public source material and architectural inspiration only. They do not imply affiliation, endorsement, certification, contract status, privileged access, or government authority.
