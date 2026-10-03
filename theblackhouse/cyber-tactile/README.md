# TheBlackHouse Cyber Defense Tactile Projection Remote System

A deterministic C++20 edge runtime plus Palantir integration layer that turns authorized cyber-defense telemetry into bounded spatial haptic events and converts deliberate tactile gestures into governed incident-response Actions.

## Architecture

```text
SIEM / EDR / packet telemetry
        |
        v
[gRPC / QUIC / gateway stream]
        |
        v
SPSC ingest queue / edge stream
        |
        v
SpatialMapper ---> SpatialThreat(x,y,z,direction,severity)
        |
        v
HapticEncoder ---> SafetyLimiter ---> CircuitBreaker ---> IHapticDevice
                                                        |-- ultrasonic-array adapter
                                                        |-- glove adapter
                                                        `-- vibrotactile-surface adapter
        |
        | async mirror; never blocks hot path
        v
Defense OSDK / RevDB -----> CyberThreatVector
        |                    SpatialHapticNode
        |                    DefenseOperatorAction
        |
        +---- Gotham Target Workbench target validation (read/context)
        +---- Gotham Gaia object layer projection
        `---- governed Ontology Actions
             |-- IsolateHost
             |-- RevokeSession
             |-- BlockIPRange
             |-- TerminateProcess
             `-- OpenIncident

Operator gesture
        |
        v
ZeroTrustGate / RBAC / deliberate confirmation
        |
        v
DefenseController ---> generated Defense OSDK Action ---> audit receipt
```

## Latency boundary

The `<5 ms` target applies to **edge ingress -> mapping -> safety clamp -> HAL dispatch**. Palantir/Gotham/RevDB calls are network/control-plane operations and therefore run asynchronously off the actuation path. A WAN/API round trip is never treated as part of the tactile safety deadline.

The C++ hot path avoids network calls and uses a single-producer/single-consumer ring buffer. The Python `CyberTactileEdge` follows the same rule and the `PalantirMirror` submits ontology/Gaia updates in a separate asynchronous task.

## Palantir Defense OSDK

`palantir/defense_ontology.yaml` defines the canonical API contract for:

- `CyberThreatVector`
- `SpatialHapticNode`
- `DefenseOperatorAction`
- `ThreatProjectedAtNode`
- `ActionRespondsToThreat`
- `upsertCyberThreatVector`
- `recordDefenseOperatorAction`
- `isolateHost`
- `revokeSession`
- `blockIPRange`
- `terminateProcess`
- `openIncident`

Generate the enrollment-specific Python Defense OSDK in Palantir Developer Console using these API names. The generated package name is supplied with `DEFENSE_OSDK_PACKAGE`; the repository does not invent enrollment-specific object classes.

The `GeneratedDefenseOsdkAdapter` uses confidential-client OAuth2 and the generated `FoundryClient`, then invokes the allowlisted generated Action functions. Production service-user permissions should be restricted to the exact object/action resources required by this service.

Required environment values:

```text
FOUNDRY_URL=<enrollment hostname>
CLIENT_ID=<confidential client id>
CLIENT_SECRET=<secret from protected runtime secret store>
DEFENSE_OSDK_PACKAGE=<generated python package>
GOTHAM_GAIA_MAP_RID=<optional Gaia map RID>
GOTHAM_PREVIEW=false
GOTHAM_OAUTH_SCOPES="<endpoint scopes required by your enrollment>"
```

Do not commit tokens or secrets.

## Gotham / RevDB / Gaia integration

`GothamPlatformAdapter` uses the official `gotham-platform-python` client surface:

- `client.target_workbench.Targets.get(...)` validates a supplied Target Workbench RID before it is associated with a cyber threat projection.
- `client.gaia.Map.add_objects(...)` adds the resulting ontology object RID to a configured Gaia map layer.

Target Workbench and geotime identifiers are retained as contextual provenance only. This subsystem is intentionally scoped to **cyber defense** and does not implement kinetic aimpoints, weapon release, fire-control, or autonomous engagement.

## Maven Smart System compatibility

The integration boundary is the Defense OSDK / Defense Ontology contract rather than a fabricated private Maven API. Enrollment-specific Maven Smart System workflows can consume the same governed ontology objects, links, properties, and Actions when those interfaces are available in the target environment.

## Safety and fail-passive behavior

Default software guards:

- tactile modulation cap: 250 Hz
- normalized amplitude cap: 0.65
- duty-cycle cap: 0.40
- connection required for actuation
- invalid/expired edge authorization token disarms the driver
- jitter above 15 ms trips a latched circuit breaker
- processing past the 5 ms edge deadline disarms the device
- reconnect does not automatically re-arm
- physical driver adapters must also enforce vendor calibration limits and an independent emergency stop

The core intentionally does not expose raw ultrasonic transducer phase/power commands. Those belong in certified/vendor HAL adapters with their own safety interlocks.

## C2 governance

A gesture is treated as a human command event, not ambient authority. It is accepted only when the gesture is bound to the active cyber threat and the operator has deliberate confirmation plus verified mTLS/session state, hardware-token proof, protected channel state, and RBAC permission.

The reference gesture policy maps:

| Gesture | Cyber context | Governed Action |
| --- | --- | --- |
| Squeeze | high-severity threat | `IsolateHost` |
| Pinch | privilege escalation | `RevokeSession` |
| Press | DDoS / port sweep | `BlockIPRange` |
| Press | malware execution | `TerminateProcess` |
| Other / low impact | any | `OpenIncident` |

Every decision is persisted as a `DefenseOperatorAction`, including rejected authorization attempts. Successful external action/audit identifiers are carried into the receipt for COA/post-incident playback.

## IL5 / IL6 note

The code implements controls that support deployment in high-assurance environments: confidential-client OAuth2, least privilege, explicit RBAC gates, mTLS at the edge control boundary, append-only action evidence, fail-passive behavior, and no secrets in source. It does **not** by itself establish IL5 or IL6 compliance/accreditation. That depends on the accredited Palantir enrollment, hosting boundary, network path, endpoint/device configuration, identity and key management, logging, vulnerability management, and the organization's authorization package.

## Build and test

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
PYTHONPATH=. python3 -m unittest -v tests.test_palantir_bridge
./build/blackhouse_cyber_tactile_demo
```

The Python tests use mocks and do not require Palantir credentials. Live integration additionally requires the enrollment-generated Defense OSDK and `gotham-platform-python`.

## Production adapters

Implement or configure these boundaries without changing the core safety model:

- `IHapticDevice`: vendor ultrasonic array, haptic glove, thermal/vibrotactile surface
- `GeneratedDefenseOsdkAdapter`: generated Defense OSDK package and governed Actions
- `GothamPlatformAdapter`: official Gotham SDK for Target Workbench and Gaia
- `AuditPort`: append-only enterprise audit/SIEM sink

The Palantir/Maven control plane must remain outside the `<5 ms` HAL hot path.
