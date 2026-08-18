# GPT-Doug-Max Submission Packet — 2026-08-17

## One-line pitch
GPT-Doug-Max is a local-first, ontology-governed agentic AI system where Zyra memory can propose new knowledge, trusted ontology state controls acceptance, and autonomous tools operate behind explicit verification and human control.

## Verified proof
- Python 3.9.6
- pytest 8.4.2
- pytest-asyncio 1.0.0
- asyncio mode: auto
- ontology proposal test suite: 5 passed in 0.16s
- public MIT-licensed repository

## Primary hackathon target
CockroachDB x AWS — Build with Agentic Memory

### Project title
GPT-Doug-Max: Ontology-Governed Agentic Memory

### Tagline
Agents that remember without letting memory silently rewrite truth.

### Problem
Agentic systems need memory, but naive long-term memory can silently turn guesses, stale outputs, or malicious inputs into future truth. GPT-Doug-Max separates proposed memory from trusted ontology state.

### Solution
Zyra captures candidate memories and routes them into a proposal subsystem. Proposed entities are tested, reviewed, and only promoted into trusted ontology state when approval invariants pass. The system is local-first, provider-neutral, and designed so agents can build tools while humans remain in command.

### Current verified engineering baseline
The async ontology proposal test suite is operational on Python 3.9 with pytest-asyncio in auto mode. The current proof-of-work run completed with 5 passing proposal tests.

### Architecture
USER / AGENT INPUT
  -> ZYRA MEMORY
  -> PROPOSAL STORE
  -> VALIDATION / APPROVAL
  -> TRUSTED ONTOLOGY
  -> RETRIEVAL / REASONING
  -> TOOL ACTION
  -> VERIFICATION

### Important submission gap
The current repository does not yet contain a verified CockroachDB persistent-memory integration or verified AWS deployment for this specific ontology proposal path. Do not represent those requirements as complete until implemented and tested.

## YC application draft

### Company / project
GPT-Doug-Max

### What are you building?
An open-source, local-first agentic AI operating layer that can build and use tools, maintain persistent memory, and reason over a governed ontology without allowing autonomous memory writes to silently become trusted truth.

### What is different?
Most agent systems treat memory as a convenience layer. GPT-Doug-Max treats memory as a governed state transition: Zyra proposes, ontology validates, and only approved knowledge becomes trusted context for future reasoning and actions.

### Current traction / proof
Public MIT-licensed repository, multi-agent and voice/tooling prototypes, automated workflows, and a verified async ontology proposal test baseline with 5 passing proposal tests on Python 3.9.

### Next milestone
Finish the proposal-to-ontology compatibility boundary, connect the trusted graph to runtime retrieval, then deploy a reproducible hosted demo showing memory proposal, approval/rejection, retrieval, and verified tool execution.

## Recommended open-source hackathon targets
- CockroachDB x AWS: strong thematic fit after CockroachDB + AWS requirements are actually implemented.
- AI Builders Hackathon 2026: broad multi-agent/open-source fit.
- Africa Deep Tech Challenge 2026: strong fit for local/on-device LLM positioning if eligibility and hardware requirements match.
- CALL-E: fit for GPT-Doug voice/phone-agent work if telephony requirements are completed.

## Submission policy
Never claim integrations, deployments, affiliations, test results, security properties, or endorsements that have not been verified. Government, military, and corporate names used in experiments or labels do not imply endorsement, affiliation, authorization, or access to non-public systems.
