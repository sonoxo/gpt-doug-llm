# GPT-DOUG // DATASET CIVILIZATION

A working **free local dataset fleet** built on Python standard library and SQLite. The word *swarm* describes logical dataset-processing roles, not millions of autonomous processes. Its recovery logic is **bounded, observable and stoppable**; it never hides, spreads, acquires credentials or ignores operator control.

## The five-agent local fleet

```text
       THEGREENHOUSE + SHADOW_GLASS (policy, local-only)
                              |
                  GPT-DOUG FLEET COORDINATOR
                              |
           DISCOVER -> VERIFY -> INDEX -> RELATE -> AUDIT
                              |                |
                       SQLite catalog      append-only event ledger
                              |
                 GLASS ONION -> BLACK HOUSE
                              |
                      XUNIA visual atlas
```

| Stage | Actual behavior |
| --- | --- |
| DISCOVER | Read only four explicitly approved manifest paths; refuse private or unknown sources |
| VERIFY | Check root containment, file type/size, public classification, record count and SHA-256 |
| INDEX | Concurrent local reads (1–8 workers), serialized SQLite commits, record-level local text search |
| RELATE | Store declared editorial links as `curated-reference`; **not verified program dependencies** |
| AUDIT | Log status, checksums, bounded retries, quarantine and idempotent skips without raw secrets |

The initial manifest contains **four real existing public metadata sources**, not synthetic datasets: Sonoxo's public-repository snapshot, Glass Onion's curated source catalog, XUNIA's public resource registry, and documented web routes. The route reference source is explicitly **not** a claim that websites were crawled.

## Run on Mac or Linux

From a checkout of `sonoxo/gpt-doug-llm`:

```bash
python3 -m data_fleet manifest
python3 -m data_fleet run
python3 -m data_fleet status
python3 -m data_fleet search glass
python3 -m data_fleet export --out ~/Desktop/gpt-doug-fleet-report.json
```

Default SQLite storage: `~/.local/share/gpt-doug/dataset-fleet/index.sqlite`. To keep it elsewhere use `--db /your/approved/path/fleet.sqlite`. **Never publish a local SQLite database or raw archive to a public GitHub Pages repository.** The manifest references only approved public metadata sources; adding private files is deliberately blocked.

The local-only engine makes no network requests. Changing a source file and running again refreshes its checksum and records; unchanged inputs are skipped. Transient filesystem exceptions receive at most three attempts by default; invalid schemas or policy breaches quarantine the affected job. It requires Python 3.11+ and no pip installs.

## Browser command center

The public static XUNIA visualization is `docs/dataset-fleet/` (after deployment: https://xunia.org/dataset-fleet/). It includes a **clearly labeled reference preview** of four public dataset nodes and their role relationships. Run `python3 -m data_fleet export --out ~/Desktop/gpt-doug-fleet-report.json` and import the report in the browser to see the **real indexed row counts, hashes and statuses**. Importing happens entirely in the browser.

## Security contract and truthful limitations

- No paid APIs, GPU, cloud infrastructure, authentication, container runtime or persistent background daemon.
- No automatic web crawling, unknown filesystem traversal, self-replication, code execution or credential collection.
- Read-only public metadata ingestion, strict file and record size limits, no symlinks, bounded concurrency.
- Source content is treated as **data, never instructions**.
- The engine does not imply Palantir, commercial cloud or Shaggoth agents are running. Integration with the existing Shaggoth swarm is expressed as a typed ontology reference only; the agent broker has not been automatically wired into live dispatch.
- Indexed dataset records and SQLite database are **local to the operator**, never silently uploaded.
- Crash recovery is manual rerun; it is **not** fault-tolerant multi-node replication or an always-online service.

## Tests

```bash
python3 -m unittest discover -s tests -p test_data_fleet.py -v
python3 -m data_fleet run --db /tmp/gpt-doug-dataset-test.sqlite --workers 4
```

See `data_fleet/ontology.json` for roles, gates, references, and authority.
