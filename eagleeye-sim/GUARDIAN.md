# THE GUARDIAN

The Guardian is the predictive defensive-intelligence layer for GPT-DOUG EAGLEEYE / GPT-EYERISFLOCK.

## Concept
Run up to 100 independent "technical eyes" over public, synthetic, local, and explicitly authorized data. Each eye observes one bounded signal family, produces evidence-backed assessments, and never issues direct physical-force commands.

## Eye families
1. Environment: weather, wildfire, flood, earthquake, air quality
2. Mobility: traffic, transit, aviation, maritime
3. Robotics: ROS2 health, localization drift, battery, thermal, comms, actuator anomalies
4. Infrastructure: power/service continuity, outages, network reachability, facility telemetry
5. Cyber defense: service health, auth anomalies, certificate expiry, endpoint status, suspicious-but-non-attributed behavior
6. Data integrity: stale feeds, missing data, conflicting sources, schema drift, impossible values
7. Operations: SLA misses, queue growth, resource saturation, dependency failure
8. Safety: geofence violations, collision risk, unsafe temperature/voltage/state
9. Provenance: source trust, age, chain of custody, authorization scope
10. Simulation: scenario injects and synthetic training conditions

## Decision loop
OBSERVE -> NORMALIZE -> CORRELATE -> SCORE -> PREDICT -> EXPLAIN -> RECOMMEND -> HUMAN GATE -> LOG

## Threat score
Every finding includes:
- severity: 0-100
- confidence: 0-1
- time horizon
- evidence count
- provenance quality
- freshness penalty
- reversible recommended action
- escalation path

## Instruction policy
Guardian instructions are constrained to:
- warn
- isolate
- pause
- fail over
- inspect
- patch
- retry
- evacuate a synthetic/authorized zone
- reduce load
- disconnect a compromised integration
- switch to backup systems
- request human review

Guardian never instructs:
- weapon use
- target engagement
- stalking or covert tracking
- access-control bypass
- credential theft
- destructive cyber activity

## Human-first requirement
The Guardian may predict and recommend, but safety-critical actions require explicit operator approval unless they are low-risk automatic protections such as circuit-breaker style software isolation, rate limiting, or simulator-only failover.
