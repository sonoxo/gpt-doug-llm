# SHADOW GLASS Glossary

Plain-language definitions for the Black House / SHADOW GLASS / GLASS ONION stack.

| Term | Plain-English meaning |
| --- | --- |
| **Action** | A controlled operation that may change data or system state. |
| **AgencyReference** | An ontology object representing a public organization/source reference; it does not imply affiliation. |
| **Audit trail** | A retained record of what was requested, allowed/denied, executed, validated, and produced. |
| **Black House** | The intelligence briefing layer that converts validated evidence into readable assessments. |
| **Confidence** | A stated estimate of how strongly available evidence supports an analytic judgment. |
| **Control decision** | A policy result such as allow, human-review, deny, or quarantine. |
| **Dataset** | A collection of structured or semi-structured data represented as an ontology object. |
| **EvidenceArtifact** | A source, file, log, result, test, or other item used to support a claim or validation. |
| **GLASS ONION** | The inner observability model: intent, identity, context, policy, tool, execution, evidence, outcome. |
| **Link** | A modeled relationship between two ontology objects. |
| **MissionDomain** | A category of mission or operational context such as space-domain awareness or defensive cyber. |
| **Object** | One specific real-world thing or event represented in the ontology. |
| **Object type** | The schema/category that defines a family of objects. |
| **Ontology** | A structured operational map of objects, properties, relationships, actions, and permissions. |
| **Policy gate** | Deterministic rules that decide whether an operation may proceed. |
| **Property** | A fact or characteristic stored on an ontology object. |
| **Provenance** | Where information came from, how it was acquired, and how it changed before use. |
| **Quarantine** | Isolation of untrusted or compromised information/actions so they cannot silently propagate. |
| **RVIA** | Project namespace used for the SONOXO / Virginia intelligence and control-plane architecture. |
| **SHADOW GLASS** | The outer defensive trust layer that shields GLASS ONION by evaluating identity, provenance, confidence, scope, risk, and policy. |
| **SoftwareArtifact** | A program, package, repository, release, model, script, or related software item represented in the ontology. |
| **TelemetryEvent** | A timestamped observation emitted by an authorized system or data source. |
| **ThreatIndicator** | Defensive information that may indicate malicious or suspicious activity; it should retain provenance and confidence. |
| **Zero trust** | Do not grant trust merely because something is inside a network or came from an agent; verify identity, scope, and context explicitly. |

## Four words to remember

```text
SOURCE → TRUST → EVIDENCE → BRIEF
```

If you understand those four stages, you understand the core of The Black House architecture.
