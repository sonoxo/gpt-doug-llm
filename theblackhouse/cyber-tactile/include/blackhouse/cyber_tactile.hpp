#pragma once

#include <array>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace blackhouse::tactile {

struct Vec3 { double x{}; double y{}; double z{}; };

enum class ThreatKind : std::uint8_t { DdosVolumetric, PrivilegeEscalation, PortSweep, MalwareExecution, Unknown };
enum class HapticPattern : std::uint8_t { ExpandingRing, RisingColumn, DirectionalSweep, SharpPulse, NeutralPulse };
enum class GestureKind : std::uint8_t { Pinch, Squeeze, Press };
enum class DefenseAction : std::uint8_t { OpenIncident, BlockIndicator, IsolateHost, TerminateProcess };

struct ThreatTelemetry {
    std::string event_id;
    ThreatKind kind{ThreatKind::Unknown};
    std::string source_asset;
    std::string target_asset;
    Vec3 source_position{};
    Vec3 target_position{};
    double cvss{};
    double anomaly_confidence{};
    std::uint64_t bytes_per_second{};
    std::uint64_t observed_at_unix_ms{};
};

struct SpatialThreat {
    std::string event_id;
    ThreatKind kind{ThreatKind::Unknown};
    std::string target_asset;
    Vec3 position{};
    Vec3 direction{};
    double severity{};
    double confidence{};
};

struct HapticFrame {
    std::string event_id;
    Vec3 focal_point{};
    HapticPattern pattern{HapticPattern::NeutralPulse};
    double modulation_hz{};
    double normalized_amplitude{};
    double duty_cycle{};
    std::uint64_t generated_at_monotonic_ns{};
};

struct LinkHealth { bool connected{true}; double jitter_ms{}; };
struct DeviceSafetyProfile {
    double max_modulation_hz{250.0};
    double max_normalized_amplitude{0.65};
    double max_duty_cycle{0.40};
    double max_network_jitter_ms{15.0};
};

struct SecurityContext {
    bool mtls_verified{false};
    bool hardware_token_verified{false};
    bool pq_hybrid_channel_verified{false};
    bool operator_authorized{false};
    std::string operator_id;
    std::string pq_suite;
};

struct GestureEvent {
    std::string event_id;
    GestureKind kind{GestureKind::Press};
    std::string threat_event_id;
    std::string target_asset;
    bool deliberate_confirmation{false};
};

struct ActionReceipt {
    bool accepted{false};
    DefenseAction action{DefenseAction::OpenIncident};
    std::string threat_event_id;
    std::string target_asset;
    std::string operator_id;
    std::string reason;
    std::uint64_t audit_sequence{};
};

struct PipelineResult {
    bool actuated{false};
    bool circuit_breaker_tripped{false};
    bool deadline_missed{false};
    SpatialThreat threat{};
    HapticFrame frame{};
    std::chrono::nanoseconds processing_latency{};
};

template <typename T, std::size_t Capacity>
class SpscRingBuffer {
    static_assert(Capacity >= 2, "Capacity must be at least 2");
public:
    bool try_push(T value) noexcept {
        const auto head = head_.load(std::memory_order_relaxed);
        const auto next = increment(head);
        if (next == tail_.load(std::memory_order_acquire)) return false;
        storage_[head] = std::move(value);
        head_.store(next, std::memory_order_release);
        return true;
    }
    std::optional<T> try_pop() noexcept {
        const auto tail = tail_.load(std::memory_order_relaxed);
        if (tail == head_.load(std::memory_order_acquire)) return std::nullopt;
        auto value = std::move(storage_[tail]);
        tail_.store(increment(tail), std::memory_order_release);
        return value;
    }
private:
    static constexpr std::size_t increment(std::size_t value) noexcept { return (value + 1U) % Capacity; }
    std::array<T, Capacity> storage_{};
    alignas(64) std::atomic<std::size_t> head_{0};
    alignas(64) std::atomic<std::size_t> tail_{0};
};

class SpatialMapper { public: [[nodiscard]] SpatialThreat map(const ThreatTelemetry& telemetry) const; };
class HapticEncoder { public: [[nodiscard]] HapticFrame encode(const SpatialThreat& threat) const; };

class SafetyLimiter {
public:
    explicit SafetyLimiter(DeviceSafetyProfile profile = {});
    [[nodiscard]] HapticFrame clamp(HapticFrame frame) const;
    [[nodiscard]] const DeviceSafetyProfile& profile() const noexcept;
private:
    DeviceSafetyProfile profile_;
};

class CircuitBreaker {
public:
    explicit CircuitBreaker(double max_jitter_ms = 15.0);
    [[nodiscard]] bool observe(const LinkHealth& health) noexcept;
    [[nodiscard]] bool tripped() const noexcept;
    void reset() noexcept;
private:
    double max_jitter_ms_;
    bool tripped_{false};
};

class IHapticDevice {
public:
    virtual ~IHapticDevice() = default;
    virtual bool apply(const HapticFrame& frame) = 0;
    virtual void disarm() noexcept = 0;
};

class MockHapticDevice final : public IHapticDevice {
public:
    bool apply(const HapticFrame& frame) override;
    void disarm() noexcept override;
    [[nodiscard]] const std::vector<HapticFrame>& frames() const noexcept;
    [[nodiscard]] bool is_disarmed() const noexcept;
private:
    std::vector<HapticFrame> frames_;
    bool disarmed_{false};
};

class ZeroTrustGate { public: [[nodiscard]] bool authorize(const SecurityContext& context) const noexcept; };

class IResponseExecutor {
public:
    virtual ~IResponseExecutor() = default;
    virtual bool execute(DefenseAction action, std::string_view target_asset) = 0;
};

class MockResponseExecutor final : public IResponseExecutor {
public:
    bool execute(DefenseAction action, std::string_view target_asset) override;
    [[nodiscard]] const std::vector<std::pair<DefenseAction, std::string>>& actions() const noexcept;
private:
    std::vector<std::pair<DefenseAction, std::string>> actions_;
};

class ResponseController {
public:
    explicit ResponseController(IResponseExecutor& executor);
    [[nodiscard]] ActionReceipt handle(const GestureEvent& gesture, const SpatialThreat& threat, const SecurityContext& security);
private:
    [[nodiscard]] static DefenseAction action_for(GestureKind gesture, const SpatialThreat& threat) noexcept;
    IResponseExecutor& executor_;
    ZeroTrustGate security_gate_{};
    std::uint64_t audit_sequence_{0};
};

class CyberTactilePipeline {
public:
    CyberTactilePipeline(IHapticDevice& device, DeviceSafetyProfile safety_profile = {}, std::chrono::microseconds deadline = std::chrono::microseconds{5000});
    [[nodiscard]] PipelineResult process(const ThreatTelemetry& telemetry, const LinkHealth& link_health);
    void reset_circuit_breaker() noexcept;
private:
    SpatialMapper mapper_{};
    HapticEncoder encoder_{};
    SafetyLimiter limiter_;
    CircuitBreaker breaker_;
    IHapticDevice& device_;
    std::chrono::microseconds deadline_;
};

[[nodiscard]] const char* to_string(ThreatKind value) noexcept;
[[nodiscard]] const char* to_string(DefenseAction value) noexcept;

}  // namespace blackhouse::tactile
