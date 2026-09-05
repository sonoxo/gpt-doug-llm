# ZYRA Product Portfolio

ZYRA is the product layer built on top of GPT-DOUG-LLM / NXYZ runtime components. This document is the market-facing catalog for what exists today, what is integration-ready, and what is still experimental.

## Portfolio

| Product | Buyer / user | Value | Current state |
| --- | --- | --- | --- |
| **ZYRA Core** | Developers, technical teams, AI builders | Bounded agentic coding with checkpoints, validation, rollback, policy gates, and local-first model support | **Implemented repository runtime** |
| **Black House Studio / Orbit** | Developers building in a browser | Browser IDE, project collaboration, browser AI, and an Ollama-compatible Black House model bridge | **Owner-private Studio deployed; bridge and project memory available in source** |
| **NXYZ Mouse Mic** | Foundry users, accessibility workflows, operators navigating dense web UIs | Voice/keyboard guidance that identifies, highlights, and activates visible controls with confirmation on high-impact actions | **v1.0.2 shipping candidate** |
| **GPT-DOUG ↔ Palantir Foundry Bridge** | Teams with an authorized Foundry tenant | Reads Ontology context, grounds GPT-DOUG analysis in authorized objects, and gates Ontology Actions behind explicit write enablement + confirmation | **Integration-ready; tenant authorization required** |
| **Watch Dog** | Local smart-camera experimentation | Local dog detection plus temporal scoring for suspected bathroom events and local alerting | **Experimental prototype** |

## ZYRA Core

**Problem:** agentic coding systems can be difficult to inspect or constrain once they move from suggestions to execution.

**Product response:** ZYRA separates model reasoning from deterministic execution controls. Repository mutations are bounded by explicit mission budgets, checkpointing, validation, and rollback behavior.

Core capabilities include:

- repository-scoped planning and edits;
- checkpoint-before-write behavior;
- validation gates and reviewer passes;
- automatic rollback on failed final validation;
- runtime self-heal for supported local provider configuration;
- native LASER defensive circuit-breaker behavior;
- worker/fleet patterns for background execution;
- GitHub security and test workflows.

Technical detail: [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`AGENTIC_RUNTIME.md`](AGENTIC_RUNTIME.md).

## Black House Studio / Orbit

**Problem:** the Black House runtime needs a discoverable browser workspace and durable project context for people and coding agents.

**Product response:** Orbit is the browser development surface for the Black House ecosystem. Its cloud workspace includes file editing, collaborative project state, a console, browser execution, web previews, and static deployment snapshots. Browser AI uses the user's device; the repository's Black House bridge connects an authorized client to an installed Ollama model.

The integration includes:

- an explicit ecosystem manifest and resource-hub entry;
- an Ollama-compatible bridge with configured model/origin allowlists, health checks, and bounded project-scoped response caching;
- opt-in SQLite project memory for Wakeup3LM, with data, logic, action, decision, and preference notes;
- provenance-aware memory import/export and recall that does not grant action approval.

The currently deployed Studio is owner-private. Listing it here does not grant other users access. No shared hosted model or container fleet is provisioned by this integration. Open-source and browser inference avoid a required paid model API; hardware, hosting, model licenses, and provider quotas still apply.

Launch, API contract, memory examples, and capability status: [`BLACK_HOUSE_STUDIO.md`](BLACK_HOUSE_STUDIO.md).

## NXYZ Mouse Mic

**Problem:** complex enterprise web applications can require dense navigation and precise targeting of controls.

**Product response:** NXYZ Mouse Mic scans visible interactive DOM elements on supported Palantir Foundry pages and lets the user navigate through typed or spoken instructions.

Shipping features:

- `show targets` numbered overlay;
- fuzzy target matching;
- `where is <label>` guidance;
- `click <label>` and `click number <n>`;
- browser speech synthesis;
- optional browser Web Speech recognition;
- typed-command fallback;
- confirmation gate on higher-impact controls;
- Manifest V3;
- no paid API key required by the extension;
- no generic `<all_urls>` permission.

Product source: [`tools/nxyz-mouse-mic`](../tools/nxyz-mouse-mic/README.md).

## GPT-DOUG ↔ Palantir Foundry Bridge

**Problem:** LLM workflows need governed operational context rather than unverified free-form context when working inside an enterprise data platform.

**Product response:** the Foundry bridge connects GPT-DOUG to an authorized Palantir Foundry deployment through the permissions assigned to the configured application/service identity.

Implemented capabilities include:

- OAuth client-credential or explicitly issued bearer-token configuration;
- list Ontologies;
- list object types;
- read/search Ontology objects;
- ground GPT-DOUG prompts with authorized Foundry objects;
- call Ontology Actions only when writes are enabled and the user confirms.

The bridge does not create Palantir permissions or credentials. Exact access is controlled by the connected Foundry tenant.

Integration guide: [`PALANTIR_FOUNDRY.md`](PALANTIR_FOUNDRY.md).

## Watch Dog

Watch Dog is an experimental local smart-camera workflow for dog detection and suspected bathroom-event scoring. It is intentionally presented as a prototype rather than a finished commercial detection product because generic object detection does not directly identify defecation behavior.

Product source: [`watch-dog`](../watch-dog/README.md).

## Product principles

Across the portfolio, ZYRA favors:

1. **Explicit capability boundaries** over claims of unlimited autonomy.
2. **Local-first or tenant-authorized execution** where practical.
3. **Human confirmation for material actions** rather than silent production mutation.
4. **Evidence and validation** before declaring an operation successful.
5. **Clear product-status labels** so prototypes are not presented as production systems.

## Commercial positioning

The portfolio is aimed at teams that need AI-assisted execution but still require visible control over what the system can read, modify, approve, or deploy.

Primary positioning areas:

- agentic software engineering;
- governed enterprise AI workflows;
- Palantir Foundry / Ontology integration;
- browser navigation and accessibility assistance;
- local automation and edge experimentation.

## Independence statement

ZYRA, GPT-DOUG-LLM, NXYZ, and repository-issued RVIA materials are independent software/project artifacts. References to Palantir, government systems, security disciplines, or external organizations describe integrations, research, or design context and do **not** imply endorsement, agency status, government authority, security clearance, certification, or affiliation.
