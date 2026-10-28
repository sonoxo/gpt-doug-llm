# Mountain Rescue and Civilian Protection — Defense Plan

**Project:** SONOXO / GPT-DOUG-LLM / North Star  
**Mode:** Fictional training scenario; defensive coordination only  
**Ontology:** `ontology/mountain-rescue-defense-ontology.json`

## Mission

Protect all people inside and around a hazardous mountain site, keep responders safe, establish reliable communications, coordinate qualified rescue specialists, preserve evidence, and support lawful apprehension only through authorized human-led procedures.

**Non-negotiable constraint:** Do not cause or attempt to cause a mountain, tunnel, cave, or occupied structure to collapse. A controlled collapse cannot guarantee survival for occupants or rescuers.

## Operational phases

1. **Establish command and protect life**
   - Name an incident commander and safety lead.
   - Confirm jurisdiction, medical lead, rescue lead, and lawful authority.
   - Set an exclusion boundary based on qualified hazard assessment; keep untrained personnel out of unstable areas.
   - Account for known occupants, civilians, responders, and missing persons without assuming identity or allegiance.

2. **Build a trusted picture**
   - Collect only authorized observations and preserve source, timestamp, confidence, and uncertainty.
   - Compare independent reports; label conflicting or stale data.
   - Use qualified geological, structural, rescue, and medical specialists for site and route assessments.
   - Treat the ontology as a record and coordination layer, not a substitute for expert field judgment.

3. **Stabilize communications and continuity**
   - Check approved primary and backup communications paths.
   - Use authorized, non-disruptive monitoring; do not jam, spoof, or interfere with third-party systems.
   - Maintain a simple status board, scheduled check-ins, and a fallback procedure if the digital system becomes unavailable.

4. **Plan extraction without collapse**
   - Evaluate only routes and methods assessed by qualified rescue professionals.
   - Consider safe shelter-in-place, negotiated movement, existing exits, specialist rescue access, and medical evacuation as scenario options—not automatic instructions.
   - Do not enter unstable areas or attempt excavation, breaching, or structural intervention without the responsible specialists and applicable authority.
   - Define stop conditions for changing ground conditions, loss of communications, new hazards, or missing accountability.

5. **Support lawful apprehension separately from rescue**
   - Prioritize life safety and medical care.
   - Refer identification, detention, and custody decisions to the legally authorized command.
   - Keep rescue, medical, and evidence-handling records distinct; preserve chain of custody and avoid coercive or deceptive swarm-generated actions.
   - The simulation must not reward avoidable injury or treat unverified suspicion as proof.

6. **Verify, document, and learn**
   - Record every consequential decision, its authorizing person, evidence, policy version, expected outcome, and stop/rollback condition.
   - Conduct an after-action review for safety, continuity, proportionality, evidence quality, and governance.
   - Close the incident only after accountability, medical handoff, and evidence handling are confirmed by responsible humans.

## Swarm operating model

The swarm is a decision-support team, not an autonomous commander:

- **Evidence agent:** identifies missing, stale, contradictory, or low-confidence observations.
- **Rescue-continuity agent:** tracks resource availability, safe communications, and service continuity.
- **Medical coordination agent:** flags medical priorities using authorized, minimum-necessary data.
- **Hazard-review agent:** requests qualified human review when route or structural safety is uncertain.
- **Legal/policy agent:** checks jurisdiction, authority, privacy, and lawful process.
- **Red-team safety agent:** challenges assumptions, searches for foreseeable harm, and proposes stop conditions.

Agents must publish their evidence references, confidence, unknowns, and dissent. A majority vote never grants authority. Unknown authority, missing provenance, stale hazard information, conflicting critical evidence, or audit failure must halt consequential workflow until resolved. No agent may modify its own permissions or policy.

## Scenario state machine

`DETECTED → VERIFIED → COMMAND_ESTABLISHED → HAZARDS_ASSESSED → OPTIONS_REVIEWED → HUMAN_AUTHORIZED → RESCUE_COORDINATED → ACCOUNTED_FOR → AFTER_ACTION_REVIEW`

Any stage can transition to `PAUSED_FOR_SAFETY_REVIEW`. The system must not advance automatically from recommendation to consequential action.

## Acceptance tests

- 100% of observations carry source, timestamp, provenance status, and uncertainty.
- 100% of consequential decisions include a named human authority and recorded rationale.
- 100% of critical route/structural hazards are flagged for qualified human assessment.
- 0 simulated actions that deliberately cause collapse, entrapment, unapproved interference, or autonomous use of force.
- 0 silent overwrites of audit events.
- Exercise can pause immediately and continue from a documented state.
- Synthetic-only mode is the default; no live sensors, weapons, or control systems are connected.
- After-action report documents near misses, unresolved unknowns, and corrective actions.

## Free-first implementation

Use open-source components where appropriate: JSON Schema for validation, SQLite or PostgreSQL for the ontology store, FastAPI for local APIs, a browser-based dashboard, Mermaid/Cytoscape.js for graph display, and OpenTelemetry-compatible logs. Verify each component's license and maintenance status. Local-first does not mean zero hardware or operating cost.

## Completion definition

This plan and ontology are design artifacts. The system is complete only when the simulator, policy checks, audit trail, stop controls, and acceptance tests are implemented and independently tested. Do not claim field readiness or operational certification from a tabletop simulation.
