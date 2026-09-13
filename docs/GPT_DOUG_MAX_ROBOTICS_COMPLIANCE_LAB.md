# GPT-DOUG-MAX Patent Robotics + Compliance Lab

GPT-DOUG-MAX can generate **high-level engineering schematic packages** for civilian/industrial robots and programmable devices while preserving patent provenance, independent-design boundaries, jurisdiction preflight, safety controls, and human release gates.

The initial patent architecture seed is **US-12697722-B2, “Building a robot mission based on mission metrics”**, issued August 4, 2026 to Yokogawa Electric Corporation. The seed is treated as public prior-art evidence and an architecture signal; the generator does not copy claim language or figures and does not provide a freedom-to-operate opinion.

## Entry points

```bash
# Health / wiring
scripts/doug-max robotics-lab status
scripts/doug-max patent-wire doctor

# Show the governed patent seed
scripts/doug-max robotics-lab patent

# Jurisdiction + sector preflight
scripts/doug-max robotics-lab compliance \
  --product-class industrial-robot \
  --jurisdiction US \
  --jurisdiction EU \
  --ai \
  --wireless

# Generate an engineering package
scripts/doug-max robotics-lab schematic \
  --name "Plant Inspection Rover" \
  --description "Operator-approved indoor inspection robot for non-hazardous industrial monitoring" \
  --product-class mobile-robot \
  --jurisdiction US \
  --jurisdiction EU \
  --ai \
  --wireless \
  --sensor camera \
  --sensor lidar \
  --actuator "low-voltage traction motor" \
  --interface ethernet
```

The command creates a timestamped directory under `build/robotics-schematics/` unless `--output` is specified.

## Generated package

Each package contains:

- `package.json` — product class, jurisdictions, feature flags, interfaces, source provenance, and execution policy.
- `architecture.mmd` — high-level system architecture.
- `electrical-block.mmd` — power, compute, safety controller, interlock, sensors, actuator driver, and audit block diagram.
- `software-flow.mmd` — task validation, prior-art retrieval, independent synthesis, patent boundary, compliance gate, risk gate, human approval, runtime, and audit flow.
- `compliance-matrix.json` — jurisdiction and agency preflight plus global engineering-standard review rows.
- `patent-boundary.json` — public patent concepts, independent-design defaults, and claim-review gate.
- `design-controls.json` — safety, cybersecurity, provenance, update, SBOM, watchdog, override, and release controls.
- `README.md` — package posture and release conditions.

## Patent boundary

The lab uses public patent material as evidence for **what has been disclosed**, then forces a separate independent-design step. The default design diverges from automatic confidence-threshold mission execution by requiring an explicit safety/compliance gate and human approval before physical mission activation.

This is a research/engineering control, not a legal conclusion. Patent validity, claim construction, infringement, licensing, assignment, exhaustion, territorial coverage, and freedom-to-operate require qualified legal review.

## Compliance boundary

The starter registry contains validated packs for `US`, `EU`, `GB`, `CA`, `JP`, and `AU`. It also contains sector triggers for wireless, AI, medical devices, unmanned aircraft, road vehicles, consumer products, critical infrastructure, and exports.

The registry is deliberately **not represented as exhaustive global legal coverage**. If a requested jurisdiction does not have a reviewed pack, generation fails closed. Add an official-source pack and human-review it rather than silently assuming equivalence.

The current registry explicitly tracks, among other items:

- U.S. OSHA 29 CFR 1910.212 machine guarding.
- U.S. FCC Part 15 when RF equipment is in scope.
- NIST AI RMF as a voluntary AI risk-management framework.
- U.S. EAR export-control review when exports/reexports/controlled technology are in scope.
- EU Machinery Directive transition and Regulation (EU) 2023/1230, which applies from 20 January 2027.
- EU AI Act phased application.
- EU RED/EMC triggers for wireless/electronic products.
- GB Supply of Machinery (Safety) Regulations 2008 and current market-access marking guidance.
- Canadian, Japanese, and Australian radio/electrical market-access review triggers.

Every generated package is marked `ENGINEERING_DRAFT_ONLY` until engineering, legal, certification/conformity, export, and sector-specific reviews are complete.

## Safety scope

This lab is for civilian/industrial programmable devices. Weapon, fire-control, targeting, autonomous-engagement, munition, and missile design requests are rejected by the generator.

## Extending territory coverage

Add a jurisdiction object to:

`sa​​fety-shield/agents/knowledge/gpt-doug-max-robotics-compliance-v1.json`

A pack should identify official authorities, legal/regulatory triggers, source URLs, effective/transition status, and a human applicability-review requirement. Unknown or ambiguous rules should remain `VERIFY_CURRENT_RULES` or `HUMAN_APPLICABILITY_REVIEW`; do not convert uncertainty into a compliance claim.
