# GPT-Doug governed sensor swarm

A free, Python-stdlib, **read-only** sensor data plane for the GPT-Doug-LLM ecosystem. Swarm workers collect registered observations concurrently and keep a local audit journal. This is **not** an "all global data" crawler or universal remote sensor network. No external system is connected by installing this code.

## Sources and safety

Supported adapters:
- biopineal: Phase I patent evidence and Phase II provenance graph. This is **research evidence**, not a physical chemistry sensor; official patent authenticity and use rights remain unverified.
- synthetic: deterministic test heartbeat with explicit synthetic classification.
- host-health: current computer's logical CPU count and local free-space summary, only with explicit operator approval.
- json / jsonl / csv: bounded metric records from a single, explicitly authorized local directory.

Per-sensor registration declares source identity, object type, purpose, authorization scope and classification. The loader enforces docs/sensor-policy.json; forbidden person/biometric/private residence/weapon/live military unit object types are rejected. File adapters enforce relative paths, no symlinks, type extension, maximum 256 KiB and 128 observations per file. Records contain only limited numeric, boolean or approved status-enumeration values (no raw unstructured documents, images, credentials, email addresses or personal identifiers). A snapshot supports up to 16 sensors, with at most four collectors running concurrently.

The local journal uses SQLite with SHA-256 event IDs covering the declared source, event and authorization scope for replay deduplication and a default rolling seven-day retention and an upper bound of 50,000 stored events; it is **not** encrypted at rest. Store only data allowed under local policies. No remote discovery, login, remote API fetching, camera/video ingest, actuator or external actions are implemented. A future external data connector must undergo separate authorization, rate-limit, provenance, SSRF and privacy review.

## Instant offline demo — no files touched

~~~sh
bash scripts/doug-max swarm-sensors demo
bash scripts/doug-max swarm-sensors live-demo
~~~

The second command starts a localhost dashboard at http://127.0.0.1:8765/ from the two safe demo adapters. It writes a local demo evidence journal and polls only the fixture/research data until Ctrl+C; no real device reads or remote connections are enabled.

## Register approved local sensors

Create an explicit manifest (choose your own paths and make sure you have permission):

~~~json
{
  "schema": "gpt-doug.sensor-swarm.v1",
  "sensors": [
    {
      "id": "research-evidence",
      "kind": "biopineal",
      "source_id": "repo-biopineal",
      "object_type": "research_evidence",
      "authorization_scope": "offline-research",
      "purpose": "research-observability",
      "classification": "public"
    },
    {
      "id": "local-machine",
      "kind": "host-health",
      "source_id": "authorized-computer",
      "object_type": "infrastructure_asset",
      "authorization_scope": "operator-approved",
      "purpose": "health-observability",
      "classification": "authorized_local"
    },
    {
      "id": "approved-file",
      "kind": "jsonl",
      "source_id": "operator-approved-file",
      "object_type": "environmental_sensor",
      "authorization_scope": "operator-approved",
      "purpose": "bounded-observability",
      "classification": "authorized_local",
      "path": "telemetry.jsonl"
    }
  ]
}
~~~

A file such as telemetry.jsonl under an authorized directory must contain separate JSON objects, each with only metric, value, optional unit and observed_at:

~~~json
{"metric":"ambient_reading","value":24.1,"unit":"units","observed_at":"2026-10-13T00:00:00Z"}
~~~

Run **with explicit authorization** (replace the paths):

~~~sh
bash scripts/doug-max swarm-sensors snapshot --config /path/to/manifest.json --root /path/to/approved-data --authorize-local
bash scripts/doug-max swarm-sensors status
bash scripts/doug-max swarm-sensors ontology > /tmp/gpt-doug-sensor-ontology.json
bash scripts/doug-max swarm-sensors serve --config /path/to/manifest.json --root /path/to/approved-data --authorize-local --port 8765 --interval 5
~~~

Visit http://127.0.0.1:8765/ while the serve command is running. It binds to localhost **only**, exposes read-only /api/status, and refreshes the browser view every five seconds. Stop with Ctrl+C. The server does not open firewall rules or listen on external interfaces.

## Runtime behavior and validation

- Records preserve provenance digest, source locator, classification and operator-declared scope. A digest confirms byte identity, **not** source authenticity.
- Individual invalid feeds are rejected without blocking unrelated healthy sensors; fail-closed policy validation occurs before the swarm starts.
- Events are deduplicated across runs. Missing file timestamps are anchored to file modification time. No event data is sent to third-party services.
- The ontology export is a read-only graph of sensor/source/observation nodes, with explicit unverified provenance and integrity checksum. It is not automatically promoted into GPT-Doug's trusted ontology.
- No polling, persistence or background service occurs from the demo command; persistence and live monitoring require explicit CLI commands.
- Use Python 3.11 or 3.12 and run:
  python3 -m unittest discover -s tests -p 'test_sensor_swarm.py' -v

Release gates: merge Phase II (#372) first; pass sensor swarm dedicated CI, review governance and privacy controls, and understand the repository's separate failing security gates before integrating this into main.
