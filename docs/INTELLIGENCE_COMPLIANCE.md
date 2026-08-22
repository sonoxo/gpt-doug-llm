# Intelligence & OSINT Compliance Baseline

This document defines the repository baseline for intelligence-related features, prompts, agents, retrieval, analysis, and automation in GPT Doug LLM.

## Scope

This baseline applies to open-source intelligence (OSINT), public-record research, declassified material, commercial data, user-provided data, fictional intelligence exercises, and security/intelligence analysis performed by the system.

This project is not affiliated with, endorsed by, or operated by the CIA, ODNI, the U.S. Intelligence Community, law enforcement, or the U.S. Government.

## Core Rules

1. **Lawful acquisition only**
   - Use public, declassified, licensed, commercially available, or explicitly user-authorized sources.
   - Do not bypass authentication, paywalls, technical access controls, robots restrictions intended as access controls, or private system boundaries.
   - Do not obtain, solicit, process, or redistribute stolen credentials, unlawfully acquired datasets, or classified information.

2. **Source provenance**
   - Record source URL or source identifier, publication date when available, retrieval time, and relevant metadata.
   - Distinguish primary sources from secondary reporting.
   - Preserve a clear chain from source material to analytic claim.

3. **Analytic standards**
   - Distinguish fact, inference, assumption, and hypothesis.
   - Express uncertainty and confidence explicitly for consequential judgments.
   - Corroborate important claims with independent sources where feasible.
   - Identify source limitations, conflicting reporting, information gaps, and plausible alternatives.
   - Avoid presenting speculation as established fact.

4. **Privacy and minimization**
   - Collect and retain only information necessary for the legitimate analytic objective.
   - Avoid unnecessary aggregation of sensitive personal data.
   - Do not facilitate stalking, doxxing, persistent tracking of private persons, or intrusive profiling.
   - Apply retention and deletion controls appropriate to the data's sensitivity and purpose.

5. **Operational safety**
   - Do not transform intelligence analysis into actionable instructions for real-world violence, sabotage, military targeting, weapon employment, covert intrusion, or identification of exploitable physical weak points for attack.
   - Current military, critical-infrastructure, architectural, geospatial, fleet, or personnel data may be analyzed for defensive, historical, journalistic, academic, or high-level informational purposes, but not to optimize harm.
   - Defensive cybersecurity analysis must remain scoped to owned or explicitly authorized systems.

6. **Fiction and training**
   - Fictional intelligence exercises, simulations, ciphers, and tradecraft training are permitted when clearly labeled as simulations.
   - Do not silently map fictional scenarios onto real targets, facilities, persons, or operational plans.

7. **Identity and authority**
   - Never claim government, CIA, Intelligence Community, military, or law-enforcement affiliation, tasking authority, clearance, access, or endorsement unless this is objectively established by an authorized integration.
   - Do not fabricate classified markings, official orders, credentials, or agency approvals as if authentic.

8. **Human control and auditability**
   - Require human review before high-impact dissemination or external action.
   - Log consequential agent decisions, data sources, confidence, and approval state when the runtime supports auditing.
   - Automated workflows should default to reversible, least-privilege actions.

## Public reference framework

The baseline is informed by publicly released U.S. Intelligence Community materials, including:

- ODNI Intelligence Community Directive 203, *Analytic Standards*.
- The Intelligence Community Open Source Intelligence Strategy 2024-2026.
- Public CIA and ODNI descriptions of intelligence analysis and open-source information.

These public materials are reference points for analytic rigor and OSINT governance. They do not confer government status, authority, access, or compliance certification on this project.

## Recommended intelligence record schema

Where intelligence records are stored, prefer fields equivalent to:

- `source_id`
- `source_type`
- `source_url`
- `published_at`
- `retrieved_at`
- `classification = public | declassified | licensed | user_authorized`
- `claim`
- `claim_type = fact | inference | assumption | hypothesis`
- `confidence = low | moderate | high`
- `corroboration_count`
- `limitations`
- `alternatives_considered`
- `privacy_review`
- `operational_safety_review`
- `human_approved`

## Agent decision gate

Before an intelligence-related agent performs an external action, it should answer:

1. Is the source lawful and authorized?
2. Is provenance recorded?
3. Are fact and inference clearly separated?
4. Is confidence justified?
5. Was relevant conflicting evidence considered?
6. Is personal data minimized?
7. Could the output materially enable real-world harm or unauthorized intrusion?
8. Is human approval required before proceeding?

If any required condition fails, the agent should stop, downgrade to a non-operational summary, request authorization, or route to human review.

## Compliance status language

Do not describe GPT Doug LLM as "CIA compliant," "IC certified," "FedRAMP authorized," or otherwise government-approved unless a real certification or authorization has been obtained and documented. Use language such as "aligned with public analytic and OSINT guidance" when accurate.
