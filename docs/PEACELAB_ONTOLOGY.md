# GPT-Doug PeaceLab — ontology-first safety and evidence graph

**Version:** 1.0.0 (JSON-LD 1.1)  
**Authority:** Engineering design and consistency model only. **Not a completed humanitarian pilot, government authorization, independent safety certification, verified peace outcome, or Nobel nomination.**

## What was created

The authoritative version-controlled semantic model lives at [peace_impact/peacelab.ontology.jsonld](../peace_impact/peacelab.ontology.jsonld). It has 54 linked nodes and uses compact RDF identifiers for concepts and directed relations. The linked node categories are:

| Ontology layer | Nodes | Meaning |
|---|---:|---|
| Classes | 11 | PeaceProgram, PilotPlan, SafetyGate, HumanRole, PilotPhase, Risk, EvidenceRecord, EvaluationMeasurement, ReviewDecision, SoftwareComponent, GovernancePolicy |
| Object relationships | 7 | hasPilot, hasGate, hasPhase, hasRisk, requiresHumanRole, nextPhase, hasTrustState |
| Human role placeholders | 7 | Roles required for oversight; **no reviewer is claimed to be identified** |
| Safety gates | 8 | Same immutable IDs and sequence as peace_impact/pilot.py; all PENDING |
| Pilot phases | 4 | 90-day proposed process with external field approval required |
| Risk nodes | 5 | Retaliation, coercion, privacy, escalation, evaluation overclaim |
| Trust states | 4 | Synthetic, self-reported, unchecked links, external review required |
| Deny policies | 5 | No self-authorized field actions, autonomous mediation, identity tracking, efficacy fabrication or Nobel self-nomination |
| Program, pilot and software nodes | 3 | Anchors of the project graph, all nonoperational by default |

### Graph overview

~~~mermaid
flowchart LR
  Program[PeaceLab program] -->|hasPilot| Plan[Pilot plan / not running]
  Plan -->|hasGate| Gates[8 pending safeguards]
  Gates -->|requiresHumanRole| Roles[7 unassigned human roles]
  Plan -->|hasPhase| Phases[4 conditional stages]
  Plan -->|hasRisk| Risks[5 stop risks]
  Plan -->|hasTrustState| Trust[Synthetic / not independently verified]
  Program --> Policy[5 deny-first policies]
~~~

The graph is an **ontology** (classes, properties, individual resources and explicit relationships); the prior [ontology.json](../peace_impact/ontology.json) remains a compatible legacy policy manifest. The validator refuses semantic drift between both manifests and the existing Python source definitions in pilot.py.

## Free Terminal visualization

Run from the GPT-Doug repository root, with Python 3.9+:

~~~bash
bash scripts/doug-max peace-lab ontology
bash scripts/doug-max peace-lab ontology-check
~~~

Print the actual JSON-LD graph:

~~~bash
bash scripts/doug-max peace-lab ontology-json
~~~

Open a self-contained HTML graph overview on a Mac (no JavaScript, network or external assets):

~~~bash
bash scripts/doug-max peace-lab ontology-html > /tmp/gpt-doug-peacelab-ontology.html && open /tmp/gpt-doug-peacelab-ontology.html
~~~

If Graphviz is already installed, export the connected ontology for a full arrow-based SVG:

~~~bash
bash scripts/doug-max peace-lab ontology-dot > /tmp/gpt-doug-peace.dot
dot -Tsvg /tmp/gpt-doug-peace.dot -o /tmp/gpt-doug-peace.svg
open /tmp/gpt-doug-peace.svg
~~~

Graphviz is **optional**, and the read-only terminal or HTML commands have no external dependencies.

To inspect a saved graph stored at another path:

~~~bash
bash scripts/doug-max peace-lab ontology-check ./graph.jsonld
~~~

The CLI **fails closed** if the document is missing, oversized, symlinked, contains duplicate JSON keys, changes the local contexts, declares an unrecognized node, points to an unresolved local relation, fabricates a reviewer/approval, falsely claims an independent outcome, or drifts from the eight gates, four phases and five risks defined in the actual pilot. A green check means **local structural and policy consistency only**.

## Machine semantics and provenance

- **W3C JSON-LD 1.1:** classes use owl:Class; properties use owl:ObjectProperty with explicit domain/range; individuals use @id and @type.
- **W3C PROV-O:** HumanRole subclass prov:Role, EvidenceRecord subclass prov:Entity, PilotPhase subclass prov:Activity, PilotPlan subclass prov:Plan, SoftwareComponent subclass prov:SoftwareAgent. These are model terms, not claims of actual human involvement.
- **SKOS:** trust states are skos:Concept instances with fixed identifiers. Importing a link or hashing a report never promotes SYNTHETIC to independently verified real-world outcome.
- **Constrained policy:** five explicit effect=DENY nodes with overrideBySoftware=false, and hard-coded zero verified outcomes/no Nobel nomination/no autonomous permission.
- **Audit digest:** SHA-256 over deterministically serialized JSON data detects local data differences and allows repeatable checks; it does not authenticate a publisher or a third-party reviewer.

The standard-library validator is not a full JSON-LD expander, OWL inference engine or SHACL processor. It explicitly says so in its report. RDF/SHACL semantic conformance can be assessed independently using dedicated tools after engineering review.

## Human safety and workflow boundary

Nothing in this ontology grants access to a global network, runs remote agents, launches a humanitarian field program, or decides political/medical outcomes. Human ethics, community, privacy and conflict-sensitivity review are real-world processes—not variables that a model can set to true. Independent evaluation must verify any real peace effect; the current tool records **zero**.

The graph is designed for integration with the current [90-day protocol](PEACELAB_90_DAY_PILOT.md), [review request](PEACELAB_ENGINEERING_REVIEW_REQUEST.md), and earlier GitHub PeaceLab implementation.

### Public standards (references, not endorsements)

- W3C JSON-LD 1.1: https://www.w3.org/TR/json-ld11/
- W3C PROV Ontology: https://www.w3.org/TR/prov-o/
- W3C SHACL Recommendation: https://www.w3.org/TR/shacl/
- UNESCO ethics recommendation: https://www.unesco.org/en/artificial-intelligence/recommendation-ethics
