#include "blackhouse/cyber_tactile.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace blackhouse::tactile {
namespace {
constexpr double clamp01(double v) noexcept { return v < 0.0 ? 0.0 : (v > 1.0 ? 1.0 : v); }
Vec3 normalize(Vec3 v) noexcept {
    const auto m = std::sqrt(v.x*v.x + v.y*v.y + v.z*v.z);
    if (m <= std::numeric_limits<double>::epsilon()) return {};
    return {v.x/m, v.y/m, v.z/m};
}
HapticPattern pattern_for(ThreatKind kind) noexcept {
    switch (kind) {
        case ThreatKind::DdosVolumetric: return HapticPattern::ExpandingRing;
        case ThreatKind::PrivilegeEscalation: return HapticPattern::RisingColumn;
        case ThreatKind::PortSweep: return HapticPattern::DirectionalSweep;
        case ThreatKind::MalwareExecution: return HapticPattern::SharpPulse;
        case ThreatKind::Unknown: return HapticPattern::NeutralPulse;
    }
    return HapticPattern::NeutralPulse;
}
std::uint64_t monotonic_now_ns() noexcept {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count());
}
} // namespace

SpatialThreat SpatialMapper::map(const ThreatTelemetry& t) const {
    const auto cvss = clamp01(t.cvss / 10.0);
    const auto conf = clamp01(t.anomaly_confidence);
    double traffic = 0.0;
    if (t.kind == ThreatKind::DdosVolumetric) {
        constexpr double gib = 1024.0 * 1024.0 * 1024.0;
        traffic = clamp01(static_cast<double>(t.bytes_per_second) / gib);
    }
    const auto severity = clamp01(0.50*cvss + 0.40*conf + 0.10*traffic);
    return {.event_id=t.event_id,.kind=t.kind,.target_asset=t.target_asset,.position=t.target_position,
        .direction=normalize({t.target_position.x-t.source_position.x,t.target_position.y-t.source_position.y,t.target_position.z-t.source_position.z}),
        .severity=severity,.confidence=conf,.target_rid=t.target_rid,.entity_rid=t.entity_rid,.geotime_track_rid=t.geotime_track_rid};
}

HapticFrame HapticEncoder::encode(const SpatialThreat& t) const {
    const auto s = clamp01(t.severity);
    return {.event_id=t.event_id,.focal_point=t.position,.pattern=pattern_for(t.kind),.modulation_hz=8.0+112.0*s,
        .normalized_amplitude=0.10+0.80*s,.duty_cycle=0.10+0.35*s,.generated_at_monotonic_ns=monotonic_now_ns()};
}

SafetyLimiter::SafetyLimiter(DeviceSafetyProfile p) : profile_(p) {}
HapticFrame SafetyLimiter::clamp(HapticFrame f) const {
    f.modulation_hz = std::clamp(f.modulation_hz,0.0,profile_.max_modulation_hz);
    f.normalized_amplitude = std::clamp(f.normalized_amplitude,0.0,profile_.max_normalized_amplitude);
    f.duty_cycle = std::clamp(f.duty_cycle,0.0,profile_.max_duty_cycle);
    return f;
}
const DeviceSafetyProfile& SafetyLimiter::profile() const noexcept { return profile_; }

CircuitBreaker::CircuitBreaker(double max_jitter_ms) : max_jitter_ms_(max_jitter_ms) {}
bool CircuitBreaker::observe(const LinkHealth& h) noexcept {
    if (!h.connected || h.jitter_ms > max_jitter_ms_) tripped_ = true;
    return !tripped_;
}
bool CircuitBreaker::tripped() const noexcept { return tripped_; }
void CircuitBreaker::reset() noexcept { tripped_ = false; }

bool MockHapticDevice::apply(const HapticFrame& f) { if (disarmed_) return false; frames_.push_back(f); return true; }
void MockHapticDevice::disarm() noexcept { disarmed_ = true; }
const std::vector<HapticFrame>& MockHapticDevice::frames() const noexcept { return frames_; }
bool MockHapticDevice::is_disarmed() const noexcept { return disarmed_; }

bool ZeroTrustGate::authorize(const SecurityContext& c) const noexcept {
    return c.mtls_verified && c.hardware_token_verified && c.pq_hybrid_channel_verified && c.operator_authorized &&
           !c.operator_id.empty() && c.pq_suite == "ML-KEM-768+X25519";
}

bool MockResponseExecutor::execute(DefenseAction a, std::string_view target) {
    if (target.empty()) return false;
    actions_.emplace_back(a,std::string{target});
    return true;
}
const std::vector<std::pair<DefenseAction,std::string>>& MockResponseExecutor::actions() const noexcept { return actions_; }

ResponseController::ResponseController(IResponseExecutor& e) : executor_(e) {}
DefenseAction ResponseController::action_for(GestureKind g, const SpatialThreat& t) noexcept {
    switch (g) {
        case GestureKind::Pinch:
            return t.kind == ThreatKind::PrivilegeEscalation ? DefenseAction::RevokeSession : DefenseAction::OpenIncident;
        case GestureKind::Squeeze:
            return t.severity >= 0.80 ? DefenseAction::IsolateHost : DefenseAction::BlockIndicator;
        case GestureKind::Press:
            if (t.kind == ThreatKind::DdosVolumetric || t.kind == ThreatKind::PortSweep) return DefenseAction::BlockIpRange;
            return t.kind == ThreatKind::MalwareExecution ? DefenseAction::TerminateProcess : DefenseAction::BlockIndicator;
    }
    return DefenseAction::OpenIncident;
}
ActionReceipt ResponseController::handle(const GestureEvent& g, const SpatialThreat& t, const SecurityContext& s) {
    ActionReceipt r{}; r.threat_event_id=t.event_id; r.target_asset=t.target_asset; r.operator_id=s.operator_id; r.audit_sequence=++audit_sequence_;
    if (g.threat_event_id != t.event_id || g.target_asset != t.target_asset) { r.reason="gesture is not bound to the active threat"; return r; }
    if (!g.deliberate_confirmation) { r.reason="operator confirmation required"; return r; }
    if (!security_gate_.authorize(s)) { r.reason="zero-trust authorization failed"; return r; }
    r.action=action_for(g.kind,t); r.accepted=executor_.execute(r.action,t.target_asset);
    r.reason=r.accepted ? "executed by scoped response adapter" : "response adapter rejected action";
    return r;
}

CyberTactilePipeline::CyberTactilePipeline(IHapticDevice& d, DeviceSafetyProfile p, std::chrono::microseconds deadline)
    : limiter_(p), breaker_(p.max_network_jitter_ms), device_(d), deadline_(deadline) {}
PipelineResult CyberTactilePipeline::process(const ThreatTelemetry& t, const LinkHealth& h) {
    const auto start=std::chrono::steady_clock::now();
    PipelineResult r{}; r.threat=mapper_.map(t); r.frame=limiter_.clamp(encoder_.encode(r.threat));
    if (!breaker_.observe(h)) { device_.disarm(); r.circuit_breaker_tripped=true; }
    else { r.actuated=device_.apply(r.frame); }
    r.processing_latency=std::chrono::steady_clock::now()-start;
    r.deadline_missed=r.processing_latency>deadline_;
    if (r.deadline_missed) { device_.disarm(); r.actuated=false; r.circuit_breaker_tripped=true; }
    return r;
}
void CyberTactilePipeline::reset_circuit_breaker() noexcept { breaker_.reset(); }

const char* to_string(ThreatKind v) noexcept {
    switch(v){case ThreatKind::DdosVolumetric:return "ddos_volumetric";case ThreatKind::PrivilegeEscalation:return "privilege_escalation";case ThreatKind::PortSweep:return "port_sweep";case ThreatKind::MalwareExecution:return "malware_execution";case ThreatKind::Unknown:return "unknown";} return "unknown";
}
const char* to_string(DefenseAction v) noexcept {
    switch(v){
        case DefenseAction::OpenIncident:return "open_incident";
        case DefenseAction::BlockIndicator:return "block_indicator";
        case DefenseAction::IsolateHost:return "isolate_host";
        case DefenseAction::TerminateProcess:return "terminate_process";
        case DefenseAction::RevokeSession:return "revoke_session";
        case DefenseAction::BlockIpRange:return "block_ip_range";
    }
    return "open_incident";
}
} // namespace blackhouse::tactile
