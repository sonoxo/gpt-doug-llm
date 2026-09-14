#include "blackhouse/cyber_tactile.hpp"

#include <chrono>
#include <iostream>

using namespace blackhouse::tactile;

int main() {
    MockHapticDevice device;
    CyberTactilePipeline pipeline{device};

    ThreatTelemetry telemetry{
        .event_id = "evt-demo-001",
        .kind = ThreatKind::PrivilegeEscalation,
        .source_asset = "identity-edge",
        .target_asset = "workload-17",
        .source_position = {-0.8, 0.2, 0.1},
        .target_position = {0.4, 0.7, 0.3},
        .cvss = 9.1,
        .anomaly_confidence = 0.96,
        .bytes_per_second = 0,
        .observed_at_unix_ms = 0,
    };

    const auto result = pipeline.process(telemetry, LinkHealth{.connected = true, .jitter_ms = 2.3});
    std::cout << "threat=" << to_string(result.threat.kind)
              << " severity=" << result.threat.severity
              << " actuation=" << (result.actuated ? "yes" : "no")
              << " latency_us="
              << std::chrono::duration_cast<std::chrono::microseconds>(result.processing_latency).count()
              << '\n';

    MockResponseExecutor response_executor;
    ResponseController controller{response_executor};
    const SecurityContext security{
        .mtls_verified = true,
        .hardware_token_verified = true,
        .pq_hybrid_channel_verified = true,
        .operator_authorized = true,
        .operator_id = "operator-demo",
        .pq_suite = "ML-KEM-768+X25519",
    };
    const GestureEvent gesture{
        .event_id = "gesture-demo-001",
        .kind = GestureKind::Squeeze,
        .threat_event_id = result.threat.event_id,
        .target_asset = result.threat.target_asset,
        .deliberate_confirmation = true,
    };
    const auto receipt = controller.handle(gesture, result.threat, security);
    std::cout << "response=" << (receipt.accepted ? "accepted" : "rejected")
              << " action=" << to_string(receipt.action)
              << " audit_sequence=" << receipt.audit_sequence
              << '\n';

    return receipt.accepted ? 0 : 1;
}
