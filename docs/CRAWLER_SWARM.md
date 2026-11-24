# GPT-DOUG-LLM MAX / Kraken Authorized Crawler Swarm

A **real**, bounded multi-worker public-web metadata collector using only the Python standard library. It composes `scripts/xunia_web_mirror.py` and `scripts/xunia_authorized_crawl.py` rather than replacing their safety checks.

## Run immediately (offline)

```bash
python3 scripts/gpt_doug_crawler_swarm.py --demo --out crawler-demo.json
python3 -m unittest discover -s tests -p 'test_gpt_doug_crawler_swarm.py' -v
```

The demo performs zero network requests and is marked `synthetic: true`.

## Crawl only approved domains

Save the following as `crawler-targets.json` and replace `example.org` with a hostname **you own or are explicitly permitted to crawl**:

```json
{
  "schema": "gpt-doug.crawler-swarm.v1",
  "targets": [
    {"id": "owned-site", "base_url": "https://example.org/", "allow_host": "example.org", "authorized": true, "max_pages": 6, "max_depth": 1}
  ]
}
```

Then:

```bash
python3 scripts/gpt_doug_crawler_swarm.py --manifest crawler-targets.json --authorized --workers 3 --out crawler-evidence.json
```

## Scope and guarantees

- Up to **4 parallel workers** across **different exact allowlisted HTTPS hosts**. A host can have only one worker; each worker pauses at least 2 seconds between pages.
- Maximum 12 hosts, 12 pages per host, 96 total pages per run, depth <=2. Reads only pages and link metadata; no forms or authenticated access.
- Reuses XUNIA's `robots.txt`, `noindex`, `nofollow`, DNS scope validation, redirect restriction, max response size, and private/admin path exclusion. Robots unavailability blocks crawling except confirmed 404.
- Output contains titles, URLs, SHA-256 content digests, link graph, and **numeric neural-ready features**, never page body text. Evidence is **unverified**, not promoted into a trusted ontology automatically.
- Each host's failures are isolated and recorded as an exception class without copying raw exception messages, which can contain sensitive URLs.
- No external API keys, cloud expenses, auto-posting, bot replication, persistent background service, or automatic publication of third-party content.
- Known limitation: the underlying stdlib fetcher checks DNS before connection but does not completely prevent DNS rebinding. Use only trusted authorized hosts and do not execute this in a privileged network context.

**Integration:** use the generated `targets[].evidence[].neural_features` as optional local input to a separately validated neural relevance model; do not mistake this metadata indexing for a trained neural model. The existing KRAKEN LIVE stream-health neural model is a separate diagnostic component, not connected automatically to this crawler.
