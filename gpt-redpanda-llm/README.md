# GPT-REDPANDA-LLM

GPT-REDPANDA is the portable local-first operator node for the Sonoxo / XUNIA ecosystem. It packages a USB-resident runtime, local assistant, Cyber CPR health/recovery, terminal metadata monitoring, and ZYRA File Intelligence into one operator surface.

## Current use cases

- Portable USB-backed AI operator node on macOS.
- Local portal for GPT-REDPANDA status, local LLM access, Cyber CPR, and terminal-health events.
- Defensive DevSecOps heartbeat and bounded recovery for GitHub repositories.
- ZYRA File Intelligence intake for local file classification, SHA-256 fingerprinting, sidecar manifests, and controlled release routing.
- Local-first runtime that can continue operating without paid hosted inference when a compatible local model is available.

## Network intelligence pack

GPT-REDPANDA now has a provenance-aware networking knowledge pack for defensive diagnosis, observability, traffic analysis, and explicitly authorized lab learning.

- Source record: `../intel/sources/youtube-OqmJb826mY4.json`
- Briefing: `../intel/briefings/2026-09-07-redpanda-networking-ethical-hackers.md`
- Ontology: `../safety-shield/agents/knowledge/redpanda-network-intel-v1.json`
- Validator: `../scripts/validate_redpanda_network_intel.py`

Core competencies include OSI/TCP-IP reasoning, IPv4/IPv6 and subnet literacy, TCP/UDP session reasoning, DNS/DHCP/ARP/ICMP concepts, ports/services, routing/switching/segmentation, firewall/ACL reasoning, packet/log analysis, network baselining, and evidence/scope discipline.

The pack does **not** grant autonomous authority for third-party targeting, credential interception, unauthorized MITM, disruption, persistence, stealth, or evasion. Active discovery and shared/production packet capture remain explicit-review actions tied to declared authorization.

## Current implementation

The production implementation currently lives in `../redpanda-desktop/` inside `sonoxo/gpt-doug-llm` while this directory is the extraction-ready standalone product package.

Core components:

- `redpanda_agent.py` — local operator portal and background agent.
- `redpanda-node` — launcher, recovery, mobile/desktop mode, and service control.
- `install.sh` — USB-aware macOS installer.
- `gpt_redpanda_llm.py` — local model orchestration plane when present.
- `agentic_cpr_runtime.py` — agentic CPR runtime when present.
- `zfi_agent.py` — ZYRA File Intelligence portal.

## How to run today

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/redpanda-desktop/install.sh) auto
redpanda-node open
```

Open ZYRA File Intelligence with:

```bash
redpanda-node files
```

## Product boundary

GPT-REDPANDA is an operator edge node. It should not silently turn every local file, credential, government artifact, customer record, or restricted item into public GitHub content.

The intended handling boundary is:

- `PUBLIC_RELEASE` — explicitly approved for publication.
- `UNCLASSIFIED_INTERNAL` — normal private working material.
- `RESTRICTED_REVIEW` — security-sensitive, NDA, customer, government-nonpublic, CUI-candidate, export-review, or otherwise uncertain material.
- `CLASSIFIED_MARKED` — never stored in ordinary GitHub, Gmail, Lovable, consumer Drive, or this local publication pipeline; use only an appropriately authorized environment.

## Expansion roadmap

### Phase 1 — Portable operator node

Current state: implemented.

- USB discovery and runtime persistence.
- Desktop background service and fallback process.
- Local authenticated portal.
- Cyber CPR integration.
- Terminal exit-status + cwd observation only.
- Optional local LLM.

### Phase 2 — File intelligence

Current state: implemented locally, cloud sync not yet claimed connected.

- Drag/drop intake.
- SHA-256 fingerprints.
- Sidecar metadata manifests.
- Project routing: ZYRA, Black House, RVIA, VA3LM, Wakeup3lm, XUNIA, NXYZ, AIP/Palantir.
- Controlled public/internal/review handling.
- Google Drive adapter as an explicit authenticated integration.

### Phase 3 — Agentic workspace

Planned.

- Job queue with durable task state.
- Per-task permission scopes.
- Tool adapters for GitHub, Drive, Gmail, Calendar, and approved cloud runtimes.
- Human approval checkpoints for consequential actions.
- Evidence trail for every agent action.
- Task replay and recovery.

### Phase 4 — Multi-node Red Panda mesh

Planned.

- Multiple USB/desktop nodes.
- Signed node identity.
- Local peer discovery.
- Delegated workloads.
- Heartbeats and failover.
- Shared policy packs without shared secrets.

### Phase 5 — XUNIA edge plane

Planned.

- Red Panda becomes the local edge/operator plane for XUNIA.
- Ontology-aware routing into RVIA, VA3LM, Zyra, NXYZ, Black House, and AIP quality planes.
- Public-source and internal-source provenance preserved separately.
- Offline-first sync with explicit conflict resolution.

## How developers should extend it

1. Add capabilities as isolated adapters rather than embedding credentials into the core runtime.
2. Give every adapter explicit read/write permissions.
3. Default external writes to disabled until configured.
4. Emit structured audit events for every consequential action.
5. Keep local fallback behavior when an external service is unavailable.
6. Add health checks before promoting a capability to GREEN.
7. Keep implementation, deployment, connection, and authorization states separate.

## Suggested standalone repository layout

```text
gpt-redpanda-llm/
├── README.md
├── LICENSE
├── redpanda/
│   ├── redpanda_agent.py
│   ├── redpanda-node
│   ├── gpt_redpanda_llm.py
│   ├── agentic_cpr_runtime.py
│   └── zfi_agent.py
├── installer/
│   └── install.sh
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── SECURITY.md
│   └── index.html
└── .github/workflows/
    ├── test.yml
    ├── security.yml
    └── pages.yml
```

## Status vocabulary

- **APPLIED** — code/config exists.
- **GREEN** — relevant verification passed.
- **DEPLOYED** — deployment actually succeeded.
- **CONNECTED** — a live external integration probe succeeded.
- **AUTHORIZED** — required authorization was explicitly established.

Never infer one state from another.
