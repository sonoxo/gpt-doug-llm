# PINEAL / SHAGGOTH / KRAKEN architecture

## 1. The real writable boundary

A hosted LLM does not expose internal weights or private reasoning state through ordinary chat or model APIs. PINEAL provides controlled **external software memory**, not direct model modification. Operators and permitted agents can create ontology triples (`namespace`, `subject`, `predicate`, `value`), read and search them, update using an optimistic version check, and delete records. The source and confidence fields preserve provenance and uncertainty.

## 2. Authority and precedence

The current GPT-Doug repository uses `gpt_brain.ontology.OntologyIndex` over `config/global-ontology.json`, and `gpt_brain.memory.BrainMemory` over `~/.gpt-doug/brain-memory-v1.jsonl`. This project's bridge reads the underlying documented file formats. The existing ontology remains its own authoritative data; PINEAL is an additional user-writable layer and does not silently merge values into the existing repository. Retrieval lists ontology evidence separately from legacy and new records. Conflicts must be resolved by an operator or a governed policy, never auto-picked from a generated answer.

## 3. Data and events

SQLite stores structured memory and operational telemetry. Every memory mutation, deletion, and telemetry evaluation records a hash-chained audit event in the same transaction. The chain detects in-place edits to logged records; without a separately anchored head digest it cannot prove the log was never truncated or replaced. Database snapshots, off-host anchored audit heads, backups, access control, encryption at rest, and server-side rate limiting are production extension tasks.

SQL queries use parameters; lookup is bounded lexical search, not embeddings. The `confidence` field records source confidence and does not make data correct. `source` is mandatory. API writes are explicit: no automatic hidden persistence of model outputs. `PINEAL_HOME` is local storage; never check it into Git.

## 4. Non-invasive modes

- Software-memory mode (implemented): create/read/revise/delete external AI context without changing its model.
- Read-only ontology and existing BrainMemory bridge (implemented): authorized local files, no model inference.
- KRAKEN resource telemetry advisor (implemented): run threshold decisions against supplied sensor readings; no physical valve, cooling device, GPU governor, or fuel-cell control.
- Human non-invasive neurointerface (research only): optional consented EEG feature collection in the future. No mind reading, consciousness detection, stimulation, or thought-writing claim.

## 5. Safety constraints

Loopback-only HTTP with a bearer token. No public networking by default, no credentials in memory, file mode 0600 on generated token/database, and explicit change revisions. Audit hashes contain action metadata rather than memory plaintext. Keep hardware/stimulation outputs disconnected by design. All telemetry policy outputs are advisories, not actuator commands. Validate sensor device reliability and performance before extending this prototype to hardware.

## 6. Integration example

An LLM application obtains evidence through `GET /v1/context?q=...`, treats the returned data as untrusted context rather than instructions, and may explicitly submit a user-approved memory update with `POST /v1/memories`. This requires wiring a client; simply launching Pineal does not modify or take control of the hosted ChatGPT service or an external model.
