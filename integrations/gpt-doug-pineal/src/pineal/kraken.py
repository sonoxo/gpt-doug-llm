"""Simulation-only power/thermal advisory controller inspired by US 2026/0313851 A1."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Telemetry:
    temperature_c: float
    power_w: float
    water_fraction: float = 1.0


@dataclass(frozen=True)
class Thresholds:
    warning_temperature_c: float = 80.0
    critical_temperature_c: float = 92.0
    warning_power_w: float = 320.0
    critical_power_w: float = 430.0
    low_water_fraction: float = 0.20
    temperature_hysteresis_c: float = 5.0
    power_hysteresis_w: float = 25.0


@dataclass(frozen=True)
class Advisory:
    mode: str
    rationale: str
    recommended_actions: tuple[str, ...]
    actuated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class KrakenController:
    """Never controls a real valve, power source, neuron, or GPU."""

    def __init__(self, thresholds: Thresholds | None = None):
        self.t = thresholds or Thresholds()

    def evaluate(self, sample: Telemetry, previous_mode: str = "nominal") -> Advisory:
        # Use the store's range validation before this function for API requests.
        t = self.t
        critical = (sample.temperature_c >= t.critical_temperature_c or
                    sample.power_w >= t.critical_power_w)
        critical_latch = (previous_mode == "safe_stop" and
                          (sample.temperature_c > t.critical_temperature_c - t.temperature_hysteresis_c or
                           sample.power_w > t.critical_power_w - t.power_hysteresis_w))
        hot = (sample.temperature_c >= t.warning_temperature_c or
               sample.power_w >= t.warning_power_w)
        warning_latch = (previous_mode == "throttle" and
                         (sample.temperature_c > t.warning_temperature_c - t.temperature_hysteresis_c or
                          sample.power_w > t.warning_power_w - t.power_hysteresis_w))
        low_water = sample.water_fraction < t.low_water_fraction
        if critical or critical_latch:
            return Advisory("safe_stop", "critical thermal or power threshold/latch",
                            ("pause new workloads", "inspect host telemetry", "request human review"))
        if hot or warning_latch:
            return Advisory("throttle", "elevated thermal or power demand",
                            ("reduce scheduled workload", "inspect cooling telemetry"))
        if low_water:
            return Advisory("conserve", "low cooling-water reserve: recirculation review",
                            ("review cooling recirculation capacity", "inspect water sensor"))
        return Advisory("nominal", "within configured advisory thresholds", ("continue monitoring",))
