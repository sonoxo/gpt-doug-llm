# TheBlackHouse Cyber Defense Tactile Projection Remote System

A deterministic C++20 reference implementation that turns authorized cyber-defense telemetry into bounded spatial haptic events and converts deliberate tactile gestures into audited incident-response requests.

## Architecture

```text
SIEM / EDR / packet telemetry
        |
        v
[gRPC / QUIC adapter]
        |
        v
SPSC ingest queue
        |
        v
SpatialMapper ---> SpatialThreat(x,y,z,direction,severity)
        |
        v
HapticEncoder ---> SafetyLimiter ---> CircuitBreaker ---> IHapticDevice
                                                        |-- ultrasonic-array adapter
                                                        |-- glove adapter
                                                        `-- vibrotactile-surface adapter

Operator gesture
        |
        v
ZeroTrustGate (mTLS + hardware token + hybrid PQ channel + operator authorization)
        |
        v
ResponseController ---> IResponseExecutor ---> scoped EDR/SIEM/firewall adapter
        |
        `-- append-only action receipt / audit sequence
```

## Low-latency path

The core hot path avoids network calls and uses a single-producer/single-consumer ring buffer for ingestion. The mapping, haptic encoding, limiting, and HAL dispatch path is measured against a 5 ms deadline. If the deadline is missed, the driver is disarmed.

`gRPC` and `QUIC` are transport adapters outside the deterministic core. The Protocol Buffer contract in `proto/cyber_tactile.proto` is transport-neutral and supports bidirectional telemetry/haptic streams.

## Safety and fail-passive behavior

The reference HAL uses normalized amplitude rather than vendor-specific transducer power. Hardware adapters MUST translate normalized output through a device-specific safety profile, calibration table, vendor limits, and independent hardware emergency stop.

Default software guards:

- tactile modulation cap: 250 Hz
- normalized amplitude cap: 0.65
- duty-cycle cap: 0.40
- connection required for actuation
- jitter above 15 ms trips a latched circuit breaker
- processing past the 5 ms actuation deadline disarms the device
- reconnect does not automatically re-arm; the application must explicitly reset the circuit breaker

The core intentionally does not expose raw ultrasonic transducer phase/power commands. Those belong in certified/vendor adapters with their own safety interlocks.

## Remote defense control

A gesture is treated as a human command event, not ambient authority. It is accepted only when:

1. the gesture is bound to the currently displayed threat and target;
2. the operator deliberately confirms the gesture;
3. mTLS identity is verified;
4. a hardware-token assertion is verified;
5. the session reports a hybrid post-quantum channel (`ML-KEM-768+X25519`);
6. the operator is authorized for the requested capability.

`IResponseExecutor` is intentionally capability-scoped. The included mock proves the control path without shipping host-isolation, firewall, or process-kill shell commands. Production adapters should call authenticated EDR/SIEM/firewall APIs under least-privilege service identities and emit the resulting external audit ID alongside `ActionReceipt`.

## Threat-to-haptic mapping

| Threat | Spatial pattern |
| --- | --- |
| Volumetric DDoS | expanding ring |
| Privilege escalation | rising column |
| Port sweep | directional sweep |
| Malware execution | sharp pulse |
| Unknown | neutral pulse |

Severity is computed from CVSS, anomaly confidence, and a bounded DDoS traffic component. Severity then controls tactile modulation frequency, amplitude, and duty cycle before the safety limiter clamps the frame.

## Build and test

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
./build/blackhouse_cyber_tactile_demo
```

## Production adapters

Implement these two interfaces without changing the core policy model:

- `IHapticDevice`: vendor ultrasonic array, haptic glove, thermal/vibrotactile surface
- `IResponseExecutor`: EDR host isolation, firewall policy API, SOAR incident action, process termination through an authorized endpoint agent

For production crypto, the `SecurityContext` booleans MUST come from a verified transport/authentication provider; never set them from untrusted client payloads. Bind the operator, session, gesture, threat event, action scope, nonce, and expiry into the server-verified authorization decision.
