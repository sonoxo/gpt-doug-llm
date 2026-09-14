#include "blackhouse/cyber_tactile.hpp"

#include <cstdlib>
#include <iostream>
#include <string_view>

using namespace blackhouse::tactile;

namespace {
void require(bool condition, std::string_view message) {
    if (!condition) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
}
ThreatTelemetry high_severity_threat() {
    return {.event_id="evt-001",.kind=ThreatKind::PrivilegeEscalation,.source_asset="identity-proxy",.target_asset="db-prod-7",
        .source_position={-1.0,0.0,0.0},.target_position={1.0,0.0,0.0},.cvss=10.0,.anomaly_confidence=1.0,.bytes_per_second=0,.observed_at_unix_ms=0};
}
void test_pipeline_actuation_and_deadline() {
    MockHapticDevice device; CyberTactilePipeline pipeline{device};
    const auto r=pipeline.process(high_severity_threat(),{.connected=true,.jitter_ms=1.2});
    require(r.actuated,"healthy link should actuate mock device");
    require(!r.circuit_breaker_tripped,"healthy link should not trip circuit breaker");
    require(!r.deadline_missed,"core path should complete inside 5 ms deadline");
    require(device.frames().size()==1,"device should receive one haptic frame");
    require(r.frame.normalized_amplitude<=0.65,"amplitude limiter must clamp frame");
    require(r.frame.duty_cycle<=0.40,"duty-cycle limiter must clamp frame");
}
void test_fail_passive_on_jitter() {
    MockHapticDevice device; CyberTactilePipeline pipeline{device};
    const auto r=pipeline.process(high_severity_threat(),{.connected=true,.jitter_ms=15.1});
    require(!r.actuated,"jitter violation must prevent actuation");
    require(r.circuit_breaker_tripped,"jitter violation must trip circuit breaker");
    require(device.is_disarmed(),"driver must enter fail-passive state");
}
void test_zero_trust_gate() {
    MockResponseExecutor executor; ResponseController controller{executor}; SpatialMapper mapper; const auto threat=mapper.map(high_severity_threat());
    const GestureEvent gesture{.event_id="gesture-001",.kind=GestureKind::Squeeze,.threat_event_id=threat.event_id,.target_asset=threat.target_asset,.deliberate_confirmation=true};
    const SecurityContext insecure{.mtls_verified=true,.hardware_token_verified=false,.pq_hybrid_channel_verified=true,.operator_authorized=true,.operator_id="operator-7",.pq_suite="ML-KEM-768+X25519"};
    const auto receipt=controller.handle(gesture,threat,insecure);
    require(!receipt.accepted,"missing hardware-token proof must reject action");
    require(executor.actions().empty(),"rejected action must not reach response executor");
}
void test_gesture_to_defense_trigger() {
    MockResponseExecutor executor; ResponseController controller{executor}; SpatialMapper mapper; const auto threat=mapper.map(high_severity_threat());
    const GestureEvent gesture{.event_id="gesture-002",.kind=GestureKind::Squeeze,.threat_event_id=threat.event_id,.target_asset=threat.target_asset,.deliberate_confirmation=true};
    const SecurityContext secure{.mtls_verified=true,.hardware_token_verified=true,.pq_hybrid_channel_verified=true,.operator_authorized=true,.operator_id="operator-7",.pq_suite="ML-KEM-768+X25519"};
    const auto receipt=controller.handle(gesture,threat,secure);
    require(receipt.accepted,"authorized tactile gesture should trigger response adapter");
    require(receipt.action==DefenseAction::IsolateHost,"high-severity squeeze should request host isolation");
    require(executor.actions().size()==1,"exactly one action should execute");
    require(executor.actions().front().second=="db-prod-7","action must stay bound to active threat target");
}
void test_spsc_ingest_queue() {
    SpscRingBuffer<ThreatTelemetry,4> queue;
    require(queue.try_push(high_severity_threat()),"queue should accept telemetry");
    const auto event=queue.try_pop();
    require(event.has_value(),"queue should return telemetry");
    require(event->event_id=="evt-001","queue should preserve event identity");
}
} // namespace

int main() {
    test_pipeline_actuation_and_deadline();
    test_fail_passive_on_jitter();
    test_zero_trust_gate();
    test_gesture_to_defense_trigger();
    test_spsc_ingest_queue();
    std::cout << "PASS: blackhouse cyber tactile tests\n";
    return 0;
}
