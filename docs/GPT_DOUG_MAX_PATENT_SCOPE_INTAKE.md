# GPT-DOUG-MAX Patent Scope Intake

GPT-DOUG-MAX treats each accepted patent as a provenance-preserving **technical-scope seed**, not as text to copy.

## Intake contract

For every patent, capture:

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

Patent seeds live in `safety-shield/agents/knowledge/patents/` and every JSON seed using `xunia.patent-robotics.seed.v1` is discovered automatically.

## Commands

```bash
scripts/doug-max patent-scope status
scripts/doug-max patent-scope list
scripts/doug-max patent-scope show US-20260201971-A9
scripts/doug-max patent-scope match "pressure sensor normally closed valve pneumatic actuator"
scripts/doug-max patent-scope doctor
```

`match` ranks technical relevance from declared scope signals. It does not decide infringement, validity, ownership, licensing, patentability, or freedom to operate.

## Current learned scopes

### US-12697722-B2
Robot mission generation and selection: robot-independent tasks, mission repositories, context, metrics, ranking/confidence, heterogeneous robot adapters, and fleet abstraction.

### US-20260201971-A9
Fluid-control and actuator feedback: normally closed supply/exhaust valves, pressure-sensor feedback, fill/vent paths, pressure-band control, fluid cylinders/airbags, force regulation, dual-circuit actuation, and agricultural implement control.

The A9 seed is linked to the `WO2020056395A1 / US20220030757A1` family for research context. Official A9 claims must be re-fetched and compared before claim-element analysis because an A9 publication can reflect a correction or republication.

## Patent-family rule

A patent family is not one worldwide right. GPT-DOUG-MAX stores family signals for research, but legal scope remains territorial. National/regional claim sets, prosecution histories, grants, expirations, lapses, oppositions, and other status events must be checked in the relevant official register before commercial or legal decisions.

## Safety boundary

Patent-derived scope data may inform civilian/industrial robotics and programmable-device engineering. It does not authorize weapon, targeting, fire-control, autonomous-engagement, munition, or missile design. Patent presence also does not override product safety, export controls, certification, privacy, cybersecurity, or sector regulation.
