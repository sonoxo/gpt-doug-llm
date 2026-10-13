# GPT-Doug × Lattice — 50 offline developer tools

**Status:** 50 executable local Python utilities, not 50 authenticated Lattice API integrations. No network, weapons, robot control, video ingress, task dispatch, or Lattice authentication is performed. The samples are **synthetic** and **not valid Lattice API payloads**.

## Why these groups?

The official Lattice developer documentation has Entities, Tasks, Objects and Video API families, plus Python SDK, sandbox and authentication guidance:

- [Lattice docs index](https://developer.anduril.com/llms.txt)
- [Entities](https://developer.anduril.com/guides/entities/overview)
- [Tasks](https://developer.anduril.com/guides/tasks/overview)
- [Objects](https://developer.anduril.com/guides/objects/overview)
- [Video](https://developer.anduril.com/guides/video/overview)
- [SDK setup](https://developer.anduril.com/guides/getting-started/set-up)
- [Lattice Sandboxes](https://developer.anduril.com/guides/developer-tools/sandboxes)

The code intentionally mirrors *concepts*, not official request/response classes. It uses existing `kraken_lattice_preview` and `kraken_robot_sim` for local data.

## Run without an account or paid resources

```bash
python3 -m research_lab.lattice_50_tools list
python3 -m research_lab.lattice_50_tools run entities.health --agents 1000 --ticks 100
python3 -m research_lab.lattice_50_tools run tasks.backlog
python3 -m research_lab.lattice_50_tools run objects.integrity
python3 -m research_lab.lattice_50_tools run video.status
python3 -m research_lab.lattice_50_tools run developer.auth
python3 -m unittest discover -s tests -p 'test_lattice_50_tools.py' -v
```

Interactive local browser panel (50 clickable buttons):

```bash
python3 -m research_lab.lattice_50_tools serve --port 8765
```

Open `http://127.0.0.1:8765`. The server binds **only** to loopback, and the UI only executes local read-only preview functions. Press Ctrl+C to stop. No third-party JavaScript or CDN dependencies. All outputs identify the offline/synthetic mode.

## Exact tool catalog (50)

| Module | Tool names |
|---|---|
| Entities (10) | `entities.list`, `entities.get`, `entities.search`, `entities.count`, `entities.roles`, `entities.validate`, `entities.low_battery`, `entities.positions`, `entities.health`, `entities.provenance` |
| Tasks (10) | `tasks.list`, `tasks.get`, `tasks.search`, `tasks.status`, `tasks.count`, `tasks.validate`, `tasks.backlog`, `tasks.completion_rate`, `tasks.workload`, `tasks.timeline` |
| Objects (10) | `objects.list`, `objects.get`, `objects.search`, `objects.types`, `objects.total_size`, `objects.checksums`, `objects.validate`, `objects.integrity`, `objects.expiring`, `objects.manifest` |
| Video (10) | `video.list`, `video.get`, `video.status`, `video.protocols`, `video.resolutions`, `video.bandwidth`, `video.frames`, `video.stale`, `video.validate`, `video.manifest` |
| Developer (10) | `developer.catalog`, `developer.docs`, `developer.sdk`, `developer.auth`, `developer.sandbox`, `developer.limits`, `developer.schema`, `developer.audit`, `developer.privacy`, `developer.health` |

## Important implementation notes

- The underlying Kraken preview serializes **at most 10 virtual units**, even if you ask for 1,000. `entities.roles` and `entities.health` show full-fleet summary values, but all other per-entity tools operate on the sampled preview. Do not treat preview ratios as complete-fleet metrics.
- `tasks.*` creates 10 or fewer local example *workflow records*. `tasks.count` distinguishes these records from the simulator's total task counters. No task is dispatched.
- `objects.integrity` validates locally regenerated synthetic manifests. The official Lattice Objects API has a less-than-1-GiB object limit and SHA-256 checksum fields; this utility does not upload files.
- `video.frames` and `video.bandwidth` are calculated assumptions, not captured images or live measurements. All virtual streams use the string `synthetic` for their protocol, not RTSP or SRT.
- `developer.auth` reports only whether environment variables are present; **it never exposes credential values**. Do not paste tokens into chat or commit them to Git.
- This is deliberately **not** a production Lattice SDK integration. Actual sandbox access depends on Lattice Developer Program approval; an authenticated adapter would need separate schema validation, scoped API credentials, and human review.

## Future, separately authorized milestones

1. Obtain official developer program and free Lattice Sandbox access (see link above).
2. Test official Python REST SDK (`pip install anduril-lattice-sdk`) in an isolated environment.
3. Add schema-valid **read-only** entity retrieval to a dedicated sandbox adapter using authorized test data.
4. Add automated contract tests and per-environment access restrictions before considering any write API.
