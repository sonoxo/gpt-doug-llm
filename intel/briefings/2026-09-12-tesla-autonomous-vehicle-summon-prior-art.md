# GPT-DOUG INTEL BRIEF // TESLA AUTONOMOUS VEHICLE SUMMON FAMILY

**Date:** 2026-09-12  
**Authority:** United States Patent and Trademark Office front pages supplied by the user  
**Company printed on front pages:** Tesla, Inc.  
**Family title:** `AUTONOMOUS AND USER CONTROLLED VEHICLE SUMMON TO A TARGET`  
**Disposition:** `ADJACENT_PUBLIC_PRIOR_ART_AND_CIVILIAN_AUTONOMY_ARCHITECTURE_WATCH`

## Exact document family captured

| Document | Date | Front-page attribution | Family role |
| --- | --- | --- | --- |
| `US-20230176593-A1` | 2023-06-08 | Applicant: Tesla, Inc. | continuation publication from application 18/166,565 |
| `US-11567514-B2` | 2023-01-31 | Applicant + Assignee: Tesla, Inc. | issued patent from application 16/272,273 |
| `US-20200257317-A1` | 2020-08-13 | Applicant: Tesla, Inc. | prior publication of application 16/272,273 |

The front pages support document-level Applicant/Assignee attribution only. They do not establish current assignment status, validity, enforceability, infringement, or freedom to operate.

## Visible architecture flow

The supplied diagrams visibly show the following high-level sequence:

1. Receive Destination
2. Receive Vision Data
3. Determine Drivable Space
4. Generate Occupancy Grid
5. Determine Path Goal
6. Navigate To Path Goal
7. Check Arrival At Destination
8. Complete Summon

GPT-DOUG stores this as an **adjacent civilian autonomy architecture watch**, not an implementation specification.

## Independent-design mapping

The safe research mapping is:

- authorized destination request;
- sensor/vision evidence ingestion;
- environment-state estimation;
- simulated occupancy representation;
- route/path-goal planning;
- bounded navigation state machine;
- arrival/termination verification;
- human authorization and safe-stop controls.

## Safety boundary

Because the source title uses the word `target`, GPT-DOUG must not reinterpret that term as a military or hostile target. In this source family it is modeled only as a civilian navigation destination/path goal.

Blocked mappings include:

- weapon target selection;
- hostile pursuit or engagement;
- weapons release;
- drone-swarm attack control;
- unattended real-world vehicle command.

Any real-world mobility control remains separately authorized, human-supervised, and outside this research watch unless an explicitly safe, lawful control path is established.

## Engineering value

This family is useful for comparing high-level perception → planning → execution → termination patterns against independently designed GPT-DOUG/ZYRAPALANTIR simulation and autonomy research. It is especially relevant to state-machine design, occupancy representations, sensor-driven navigation, safe-stop logic, and auditability.

## Implementation

- source: `intel/sources/uspto-adjacent-tesla-autonomous-vehicle-summon-family.json`
- ontology: `safety-shield/agents/knowledge/gpt-doug-adjacent-autonomy-prior-art-v1.json`
- CLI: `scripts/gpt_doug_autonomy_prior_art.py`
- tests: `tests/test_gpt_doug_autonomy_prior_art.py`

## Use

```bash
python3 scripts/gpt_doug_autonomy_prior_art.py summary
python3 scripts/gpt_doug_autonomy_prior_art.py family
python3 scripts/gpt_doug_autonomy_prior_art.py flow
python3 scripts/gpt_doug_autonomy_prior_art.py doctor
```
