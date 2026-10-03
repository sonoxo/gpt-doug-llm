# THE BLACK HOUSE // PHASE 9 O/D SIMULATION PLANE

Phase 9 translates the uploaded layered battlespace reference into a **software-resilience architecture**, not a weapons-control system.

The architectural pattern retained is the useful systems idea: many observation layers feed transport, fusion, assessment, response, and verification. The weapon-engagement semantics are deliberately replaced with governed cyber/AI simulation semantics.

## Control loop

```text
SENSE
  ↓
TRANSPORT
  ↓
FUSE
  ↓
ASSESS
  ↓
EMULATE (authorized lab only)
  ↓
DEFEND
  ↓
VERIFY
  ↓
EVIDENCE / AUDIT
```

## Layer mapping

| Reference pattern | Black House implementation |
|---|---|
| distributed sensors | endpoint, network, identity, cloud, app, OSINT, synthetic telemetry |
| transport mesh | RVIA + telemetry/event routing |
| track fusion | evidence correlation + risk assessment |
| fire-control coordination | **replaced** by governed decision support and response planning |
| engagement loop | **replaced** by sense-assess-emulate-defend-verify |
| layered interceptors | defensive controls: detect, contain, recover, verify |
| shot assessment | post-response validation + mission evidence |

## Offense plane

`OFFENSE_EMULATION` means adversary simulation in `synthetic`, `isolated_lab`, or `owned_test` environments only. The runtime emits plans and synthetic signals; it does not exploit public systems, control weapons, disrupt critical infrastructure, or autonomously mutate external systems.

Safe emulation examples include synthetic authentication anomalies, synthetic suspicious movement edges, and synthetic data-access spikes.

## Defense plane

The defensive chain is:

```text
DETECT → CONTAIN → RECOVER → VERIFY
```

Production scopes may receive a read-only defensive plan. Any consequential mutation still requires explicit approval and must be carried out by a separate authorized executor with evidence and audit.

## Runtime

```text
GET  /api/black-house/od
POST /api/black-house/od/simulate
```

Example request:

```json
{
  "scenarioId": "lab-001",
  "requestedBy": "operator",
  "mode": "FULL_LOOP",
  "environment": "isolated_lab",
  "scope": ["lab-segment-a"],
  "telemetry": [
    {"signal": "auth-anomaly", "severity": "high"}
  ]
}
```

The response always reports whether any external execution occurred. Phase 9's runtime value is always `false` because this plane is intentionally plan/simulation only.

## Fail-closed rules

- explicit scope is mandatory;
- offense emulation cannot run against `production` or `public_internet` environments;
- public-Internet exploitation is disabled;
- critical-infrastructure disruption is disabled;
- weapons control is disabled;
- autonomous external mutation is disabled;
- mutation requests require `APPROVED` state;
- evidence and audit remain mandatory.

Canonical manifest: `the-black-house/od/od-plane.manifest.json`.
Runtime: `va3lm/src/va3lm/od_plane.py`.
Tests: `va3lm/tests/test_black_house_phase_9_od.py`.
