# GPT-DOUG-MAX Patent Scope Intake

GPT-DOUG-MAX treats patent feeds as provenance-preserving engineering evidence, not as text to copy. Intake is deliberately two-stage so the system never invents technical scope when a source document cannot be verified.

## Stage 1 - pending intake

A newly supplied publication is first registered under `safety-shield/agents/knowledge/patent-intake/` using `xunia.patent-intake.v1` when the official text/PDF cannot yet be retrieved or verified.

A pending record stores only verified identifiers, stable source provenance, extraction status, and the promotion gates needed before the patent can influence design retrieval. Temporary USPTO request tokens are never persisted.

Pending patents are visible through:

```bash
scripts/doug-max patent-scope pending
scripts/doug-max patent-scope show US-20260271508-A1
```

Pending records are **excluded from technical scope ranking**. Unknown scope is fail-closed rather than guessed.

## Stage 2 - validated scope seed

After source review, capture:

1. exact publication or grant identifier and kind code;
2. title, application/priority dates, inventors, and verified document-level applicant/assignee metadata;
3. official-source provenance without persisting temporary request tokens;
4. patent-family references and territorial caveats;
5. normalized `scope_tags` and technical domain;
6. publicly described functional concepts in paraphrased engineering language;
7. a `scope_model` describing architecture, control loops, interfaces, and reusable engineering patterns;
8. family-level claim-scope signals for retrieval only, explicitly marked **not claim construction**;
9. independent-design defaults and human legal-review gates;
10. schematic seeds and safety boundaries relevant to civilian/industrial programmable devices.

Validated patent seeds live in `safety-shield/agents/knowledge/patents/` and every JSON seed using `xunia.patent-robotics.seed.v1` is discovered automatically.

## Commands

```bash
scripts/doug-max patent-scope status
scripts/doug-max patent-scope list
scripts/doug-max patent-scope pending
scripts/doug-max patent-scope show US-20250363154-A1
scripts/doug-max patent-scope match "natural language ontology graph database query generation"
scripts/doug-max patent-scope doctor
```

`match` ranks technical relevance only from validated scope signals. It does not decide infringement, validity, ownership, licensing, patentability, or freedom to operate.

## Current validated scopes

### US-12697722-B2
Robot mission generation and selection: robot-independent tasks, mission repositories, context, metrics, ranking/confidence, heterogeneous robot adapters, and fleet abstraction.

### US-20260201971-A9
Fluid-control and actuator feedback: normally closed supply/exhaust valves, pressure-sensor feedback, fill/vent paths, pressure-band control, fluid cylinders/airbags, force regulation, dual-circuit actuation, and agricultural implement control.

The A9 seed is linked to the `WO2020056395A1 / US20220030757A1` family for research context. Official A9 claims must be re-fetched and compared before claim-element analysis because an A9 publication can reflect a correction or republication.

### US-20250363154-A1
Ontology-backed database interaction using machine learning: natural-language query intake, LLM generation of graph/relational queries, ontology-aware API function calling, multi-database access, candidate-query selection, ontology updates, and preservation of provenance/access-control semantics.

GPT-DOUG-MAX stores the reusable build profile as `ONTOLOGY_FIRST_GOVERNED_LLM_QUERY_COMPILER`. The independent reference architecture keeps authoritative ontology data outside model memory and inserts deterministic schema validation, query-policy linting, least-privilege execution, read/write separation, provenance, dry-run/explain support, and human approval for high-impact mutations between LLM generation and execution.

## Current pending intake

### US-20260271508-A1
Registered from a user-supplied USPTO US-PGPUB link. The ephemeral request token is not stored. In the current execution environment the official document text/PDF could not be retrieved, so title, abstract, claims, CPC/IPC, inventors, assignee, and technical scope remain intentionally unverified. This record will not influence design matching until it is promoted to a validated scope seed after source review.

## Building-memory rule

A learned patent may contribute high-level architecture patterns to GPT-DOUG-MAX only when they are stored as independent-design abstractions. Build memory should favor reusable interfaces, validation gates, provenance, safety/security controls, and implementation-neutral patterns. It must not copy patent claim language, patent figures, or represent that a generated design has freedom to operate.

## Patent-family rule

A patent family is not one worldwide right. GPT-DOUG-MAX stores family signals for research, but legal scope remains territorial. National/regional claim sets, prosecution histories, grants, expirations, lapses, oppositions, and other status events must be checked in the relevant official register before commercial or legal decisions.

## Safety boundary

Patent-derived scope data may inform civilian/industrial robotics and programmable-device engineering. It does not authorize weapon, targeting, fire-control, autonomous-engagement, munition, or missile design. Patent presence also does not override product safety, export controls, certification, privacy, cybersecurity, or sector regulation.
