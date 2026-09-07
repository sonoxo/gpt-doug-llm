# ZYRAPALANTIR

**Division:** GPT-ZYRA-PALANTIR  
**Codename:** ZYRAPALANTIR  
**Parent ecosystem:** GPT-DOUG-LLM / XUNIA / krakenXYZ

ZYRAPALANTIR is the Palantir-centered operational intelligence, digital-twin, resilience, and governed-AI division of the shared ecosystem.

## Mission

Build ontology-first operational software that can:

- model complex infrastructure dependencies as digital twins;
- ingest synthetic or approved telemetry into a governed operational graph;
- reason over incidents with AIP-style agents and deterministic policies;
- simulate cascading failures, containment, failover, restoration, and after-action review;
- preserve life-safety dependencies in every exercise;
- expose only explicitly authorized, auditable actions;
- connect to Foundry/AIP/OSDK/MCP-compatible interfaces when credentials and approved deployments are available.

## Safety boundary

ZYRAPALANTIR is **simulation-only for critical-infrastructure exercises**. It must not provide direct actuation or control over real utilities, SCADA/PLC systems, traffic controllers, aviation systems, 911/988, EMS/EMT dispatch, hospitals, or other life-safety infrastructure.

Hard invariants:

```text
REAL_INFRASTRUCTURE_WRITE_ACCESS = FALSE
REAL_SCADA_CONTROL               = FALSE
REAL_PLC_CONTROL                 = FALSE
REAL_EMERGENCY_SERVICE_CONTROL   = FALSE
REAL_TRAFFIC_CONTROL             = FALSE
OUTBOUND_NETWORK_IN_SIM          = FALSE

SYNTHETIC_TELEMETRY              = TRUE
DIGITAL_TWIN                     = TRUE
CASCADE_SIMULATION               = TRUE
FAILOVER_SIMULATION              = TRUE
HUMAN_APPROVAL_FOR_ACTIONS       = TRUE
AUDIT_LOGGING                    = TRUE
```

## Architecture

```text
GPT-DOUG / ZYRA agents
        |
        v
ZYRAPALANTIR policy gateway
        |
        v
Ontology / digital-twin graph
        |
        +--> POWER_SIM
        +--> WATER_SIM
        +--> TRAFFIC_SIM
        +--> EMS_SIM
        +--> 911_SIM
        +--> 988_SIM
        +--> AIR_SIM
        |
        v
KRAKEN_GUARD simulation actions
        |
        v
Audit + recovery verification
```

## Core object types

- `Division`
- `InfrastructureDomain`
- `DigitalTwinAsset`
- `Dependency`
- `SyntheticSensor`
- `SyntheticAlert`
- `Incident`
- `SafetyEnvelope`
- `FailoverResource`
- `RecoveryStep`
- `AuditEvent`

## Allowed action types

- `DECLARE_EXERCISE`
- `ACKNOWLEDGE_INCIDENT`
- `ISOLATE_SIMULATED_NODE`
- `ENTER_SIMULATED_SAFE_STATE`
- `PRESERVE_LIFE_SAFETY_SERVICE`
- `ACTIVATE_SIMULATED_FAILOVER`
- `REROUTE_SIMULATED_EMS`
- `ROLLBACK_SIMULATION_ACTION`
- `RESTORE_SIMULATED_SERVICE`
- `VERIFY_RECOVERY`
- `CLOSE_EXERCISE`

## Division command

```text
ZYRAPALANTIR STATUS
```

Returns division identity, safety mode, registered digital-twin domains, active synthetic incidents, and audit state.
