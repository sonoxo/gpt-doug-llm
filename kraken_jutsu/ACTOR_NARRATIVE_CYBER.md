# Actor–Narrative–Cyber Intelligence Layer

Kraken Jutsu now separates public cyber claims from verified incidents and keeps attribution hypotheses distinct from technical incident verification.

## Core invariant

> CLAIM != COMPROMISE

An actor post, social-media claim, screenshot, or single news report is evidence of a **claim**. It is not sufficient evidence that infrastructure was compromised.

## Ontology chain

```text
EVENT
  -> NARRATIVE
  -> ACTOR
  -> MOTIVATION
  -> TARGET
  -> TTP
  -> OBSERVABLE
  -> IMPACT
  -> DEFENSE
  -> CONFIDENCE
```

The verification result also carries a `claim_status`:

- `CLAIMED` — insufficient independent corroboration
- `CORROBORATED` — multiple independent sources support the claim
- `VERIFIED_INCIDENT` — confidence threshold plus independent, authoritative, and technical corroboration
- `DISPUTED` — strong authoritative contradiction prevents verification
- `RETRACTED` — claim explicitly withdrawn

## Evidence model

Supported evidence classes are:

- actor claim
- social post
- news report
- third-party report
- government advisory
- victim/affected-party statement
- owned or authorized telemetry
- IOC match

Evidence is scored deterministically by evidence type and operator-supplied reliability. Duplicate source/type observations are collapsed to the highest-reliability observation. Independent-source bonuses are capped so a pile of weak social posts cannot manufacture a verified incident.

`VERIFIED_INCIDENT` requires all of the following:

1. confidence at or above the verification threshold;
2. at least two independent supporting sources;
3. at least one authoritative supporting source; and
4. at least one technical supporting source.

Actor self-claims never satisfy the independent-source requirement by themselves.

## Defensive output

`build_defensive_brief()` produces a SOC/IR-oriented object with:

- verification state and confidence;
- the Actor–Narrative–Cyber ontology;
- evidence provenance;
- explainable reasons;
- a defensive posture; and
- non-operational recommendations for telemetry correlation, ATT&CK detection mapping, provenance preservation, containment validation, and attribution discipline.

The module does not execute intrusion, exploitation, retaliation, or targeting actions.

## Example

```python
from kraken_jutsu import (
    ClaimVerifier,
    Evidence,
    EvidenceKind,
    ThreatClaim,
    build_defensive_brief,
)

claim = ThreatClaim(
    claim_id="incident-001",
    event="reported service disruption",
    narrative="an actor claims responsibility for an outage",
    actor="unverified-actor",
    targets=["owned-service"],
    ttps=["T1498"],
    observables=["availability anomaly"],
    defenses=["rate limiting", "telemetry correlation"],
    evidence=[
        Evidence("affected-party", EvidenceKind.VICTIM_STATEMENT, 0.95),
        Evidence("owned-sensor", EvidenceKind.TELEMETRY, 0.95),
    ],
)

result = ClaimVerifier().verify(claim)
brief = build_defensive_brief(claim, result)
```

## Acceptance properties

The test suite enforces these invariants:

- actor self-claim alone remains `CLAIMED`;
- independent reporting can corroborate without proving compromise;
- verified incidents require authoritative and technical support;
- strong authoritative contradiction can produce `DISPUTED`; and
- ontology output preserves the full reasoning chain.
