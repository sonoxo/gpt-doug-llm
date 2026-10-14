"""Sequential spike-confluence and quantum-inspired projection engine.

This is classical research software. It does not claim quantum computation,
biological causality, consciousness, individual-neuron access, or physical
biochip control. It consumes already-authorized spike-count sequences and emits
transparent descriptive features plus an uncalibrated heuristic forecast.
"""
from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from statistics import fmean
from typing import Iterable, Sequence

OUTCOME_STATES = (
    "QUIESCENT",
    "DISTRIBUTED_ACTIVITY",
    "CONFLUENT_ACTIVITY",
    "BURST_CONFLUENT",
)

MAX_FRAMES = 10_000
MAX_CHANNELS = 256
MAX_COUNT_PER_CHANNEL = 1_000_000

FEATURE_DIMENSIONS = (
    "time",
    "channel_occupancy",
    "population_rate",
    "channel_entropy",
    "temporal_persistence",
    "vector_similarity",
    "rate_acceleration",
    "burst_index",
    "spectral_proxy",
    "geometry_proxy",
    "phase_proxy",
    "confluence",
    "forecast_uncertainty",
    "provenance",
    "causal_status",
    "verification",
)


@dataclass(frozen=True)
class SpikeFrame:
    t_ms: float
    counts: tuple[int, ...]

    def __post_init__(self) -> None:
        if isinstance(self.t_ms, bool) or not isinstance(self.t_ms, (int, float)):
            raise ValueError("t_ms must be numeric")
        if not math.isfinite(float(self.t_ms)):
            raise ValueError("t_ms must be finite")
        if not self.counts:
            raise ValueError("counts cannot be empty")
        if len(self.counts) > MAX_CHANNELS:
            raise ValueError(f"at most {MAX_CHANNELS} channels are supported")
        if any(type(v) is not int or v < 0 or v > MAX_COUNT_PER_CHANNEL for v in self.counts):
            raise ValueError(
                f"counts must be non-negative integers <= {MAX_COUNT_PER_CHANNEL}"
            )


@dataclass(frozen=True)
class SequenceFeatures:
    t_ms: float
    total_spikes: int
    population_rate_hz: float
    active_ratio: float
    normalized_entropy: float
    temporal_persistence: float
    vector_similarity: float
    acceleration: float
    burst_index: float
    spectral_proxy: float
    geometry_proxy: float
    phase_proxy: float
    confluence: float


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _cosine(a: Sequence[int], b: Sequence[int]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return _clamp(dot / (na * nb))


def _entropy(counts: Sequence[int]) -> float:
    total = sum(counts)
    n = len(counts)
    if total <= 0 or n <= 1:
        return 0.0
    entropy = 0.0
    for value in counts:
        if value:
            p = value / total
            entropy -= p * math.log(p)
    return _clamp(entropy / math.log(n))


def _active_jaccard(a: Sequence[int], b: Sequence[int]) -> float:
    aa = {i for i, value in enumerate(a) if value > 0}
    bb = {i for i, value in enumerate(b) if value > 0}
    if not aa and not bb:
        return 1.0
    union = aa | bb
    return len(aa & bb) / len(union) if union else 0.0


def _spectral_proxy(history: Sequence[int]) -> float:
    """Low-cost alternating-energy proxy, not a frequency-domain spectrum."""
    if len(history) < 3:
        return 0.0
    mean = fmean(history)
    centered = [value - mean for value in history]
    total_energy = sum(value * value for value in centered)
    if total_energy == 0:
        return 0.0
    alternating = abs(sum((1 if i % 2 == 0 else -1) * value for i, value in enumerate(centered)))
    return _clamp(alternating / math.sqrt(total_energy * len(centered)))


def _geometry_proxy(counts: Sequence[int]) -> float:
    """Measures whether activity is spread across the array rather than isolated."""
    active = [i for i, value in enumerate(counts) if value > 0]
    if len(active) <= 1:
        return 0.0
    span = (max(active) - min(active)) / max(1, len(counts) - 1)
    occupancy = len(active) / len(counts)
    return _clamp(math.sqrt(span * occupancy))


def _phase_proxy(current: Sequence[int], previous: Sequence[int] | None) -> float:
    if previous is None:
        return 0.0
    cosine = _cosine(current, previous)
    overlap = _active_jaccard(current, previous)
    return _clamp(0.5 * cosine + 0.5 * overlap)


def extract_features(frames: Sequence[SpikeFrame], index: int, window: int = 8) -> SequenceFeatures:
    if not 0 <= index < len(frames):
        raise IndexError(index)
    if window < 2:
        raise ValueError("window must be >= 2")

    frame = frames[index]
    previous = frames[index - 1] if index else None
    totals = [sum(item.counts) for item in frames[max(0, index - window + 1): index + 1]]
    total = totals[-1]
    dt_ms = frame.t_ms - previous.t_ms if previous else 0.0
    population_rate_hz = total * 1000.0 / dt_ms if dt_ms > 0 else 0.0
    active_ratio = sum(1 for value in frame.counts if value > 0) / len(frame.counts)
    entropy = _entropy(frame.counts)
    persistence = _active_jaccard(frame.counts, previous.counts) if previous else 0.0
    similarity = _cosine(frame.counts, previous.counts) if previous else 0.0

    if previous is None or index < 2:
        acceleration = 0.5
    else:
        previous_previous = frames[index - 2]
        previous_dt_ms = previous.t_ms - previous_previous.t_ms
        previous_rate_hz = (
            sum(previous.counts) * 1000.0 / previous_dt_ms if previous_dt_ms > 0 else 0.0
        )
        rate_scale = max(1.0, abs(population_rate_hz) + abs(previous_rate_hz))
        acceleration = _clamp(
            0.5 + (population_rate_hz - previous_rate_hz) / (2.0 * rate_scale)
        )

    baseline = fmean(totals[:-1]) if len(totals) > 1 else float(total)
    burst_index = _clamp(total / max(1.0, 3.0 * baseline))
    spectral = _spectral_proxy(totals)
    geometry = _geometry_proxy(frame.counts)
    phase = _phase_proxy(frame.counts, previous.counts if previous else None)

    # "Confluence" is a declared descriptive index. It intentionally rewards
    # simultaneous occupancy, temporal continuity, vector similarity and
    # distributed geometry; it is not a biological learning metric.
    confluence = _clamp(
        0.24 * active_ratio
        + 0.18 * entropy
        + 0.18 * persistence
        + 0.18 * similarity
        + 0.12 * geometry
        + 0.10 * phase
    )

    return SequenceFeatures(
        t_ms=frame.t_ms,
        total_spikes=total,
        population_rate_hz=round(population_rate_hz, 6),
        active_ratio=round(active_ratio, 6),
        normalized_entropy=round(entropy, 6),
        temporal_persistence=round(persistence, 6),
        vector_similarity=round(similarity, 6),
        acceleration=round(acceleration, 6),
        burst_index=round(burst_index, 6),
        spectral_proxy=round(spectral, 6),
        geometry_proxy=round(geometry, 6),
        phase_proxy=round(phase, 6),
        confluence=round(confluence, 6),
    )


def classify(features: SequenceFeatures) -> str:
    if features.total_spikes == 0 or features.active_ratio < 0.05:
        return "QUIESCENT"
    if features.burst_index >= 0.75 and features.confluence >= 0.55:
        return "BURST_CONFLUENT"
    if features.confluence >= 0.58:
        return "CONFLUENT_ACTIVITY"
    return "DISTRIBUTED_ACTIVITY"


def _softmax(logits: dict[str, float]) -> dict[str, float]:
    maximum = max(logits.values())
    exps = {key: math.exp(value - maximum) for key, value in logits.items()}
    total = sum(exps.values())
    return {key: value / total for key, value in exps.items()}


def heuristic_outcome_probabilities(features: SequenceFeatures) -> dict[str, float]:
    """Return transparent, uncalibrated next-state probabilities."""
    activity = _clamp(features.active_ratio * 1.5)
    conf = features.confluence
    burst = features.burst_index
    quiet = 1.0 - activity
    logits = {
        "QUIESCENT": 2.2 * quiet - 0.8 * conf - 0.5 * burst,
        "DISTRIBUTED_ACTIVITY": 1.4 * activity + 0.8 * features.normalized_entropy - 0.5 * conf,
        "CONFLUENT_ACTIVITY": 1.8 * conf + 0.7 * features.temporal_persistence + 0.4 * activity,
        "BURST_CONFLUENT": 1.8 * burst + 1.2 * conf + 0.5 * features.acceleration,
    }
    probs = _softmax(logits)
    return {key: round(probs[key], 6) for key in OUTCOME_STATES}


def _transition_matrix(states: Sequence[str]) -> dict[str, dict[str, float]]:
    """Laplace-smoothed first-order transition matrix from the observed sequence."""
    counts = {
        left: {right: 1.0 for right in OUTCOME_STATES}
        for left in OUTCOME_STATES
    }
    for left, right in zip(states, states[1:]):
        counts[left][right] += 1.0

    matrix: dict[str, dict[str, float]] = {}
    for left in OUTCOME_STATES:
        total = sum(counts[left].values())
        matrix[left] = {
            right: counts[left][right] / total
            for right in OUTCOME_STATES
        }
    return matrix


def _propagate(
    distribution: dict[str, float],
    matrix: dict[str, dict[str, float]],
) -> dict[str, float]:
    result = {
        target: sum(
            distribution[source] * matrix[source][target]
            for source in OUTCOME_STATES
        )
        for target in OUTCOME_STATES
    }
    total = sum(result.values()) or 1.0
    return {key: result[key] / total for key in OUTCOME_STATES}


def _blend_probabilities(a: dict[str, float], b: dict[str, float], weight_a: float = 0.65) -> dict[str, float]:
    weight_a = _clamp(weight_a)
    values = {key: weight_a * a[key] + (1.0 - weight_a) * b[key] for key in OUTCOME_STATES}
    total = sum(values.values())
    return {key: round(values[key] / total, 6) for key in OUTCOME_STATES}


def _uncertainty(probabilities: dict[str, float]) -> float:
    entropy = -sum(p * math.log(p) for p in probabilities.values() if p > 0)
    return _clamp(entropy / math.log(len(probabilities)))


def quantum_inspired_projection(features: SequenceFeatures) -> dict:
    """Classical complex-vector transform inspired by amplitude/phase notation.

    This runs on ordinary CPU arithmetic. It is not a quantum circuit and makes
    no quantum advantage claim.
    """
    vector = [
        features.active_ratio,
        features.normalized_entropy,
        features.temporal_persistence,
        features.vector_similarity,
        features.acceleration,
        features.burst_index,
        features.geometry_proxy,
        features.confluence,
    ]
    weights = [max(1e-12, value) for value in vector]
    total = sum(weights)
    amplitudes = [
        math.sqrt(weight / total) * cmath.exp(2j * math.pi * _clamp(value))
        for weight, value in zip(weights, vector)
    ]

    n = len(amplitudes)
    transformed: list[complex] = []
    for k in range(n):
        value = 0j
        for j, amplitude in enumerate(amplitudes):
            value += amplitude * cmath.exp(-2j * math.pi * j * k / n)
        transformed.append(value / math.sqrt(n))

    probabilities = [abs(value) ** 2 for value in transformed]
    norm = sum(probabilities) or 1.0
    probabilities = [value / norm for value in probabilities]
    dominant = max(range(n), key=lambda i: probabilities[i])
    return {
        "mode": "CLASSICAL_QUANTUM_INSPIRED",
        "hardware_quantum": False,
        "state_dimension": n,
        "measurement_probabilities": [round(value, 6) for value in probabilities],
        "dominant_latent_axis": dominant,
        "dominant_probability": round(probabilities[dominant], 6),
    }


class SequentialSpikeModel:
    def __init__(self, window: int = 8) -> None:
        if not 2 <= window <= 128:
            raise ValueError("window must be 2..128")
        self.window = window

    def analyze(self, frames: Sequence[SpikeFrame], source_class: str = "SIMULATED") -> dict:
        if len(frames) < 2:
            raise ValueError("at least two frames are required")
        channel_count = len(frames[0].counts)
        if any(len(frame.counts) != channel_count for frame in frames):
            raise ValueError("all frames must have the same channel count")
        if any(right.t_ms <= left.t_ms for left, right in zip(frames, frames[1:])):
            raise ValueError("timestamps must be strictly increasing")

        features = [extract_features(frames, i, self.window) for i in range(len(frames))]
        states = [classify(item) for item in features]
        last = features[-1]
        heuristic = heuristic_outcome_probabilities(last)
        transition_matrix = _transition_matrix(states)
        empirical = transition_matrix[states[-1]]
        probabilities = _blend_probabilities(heuristic, empirical)
        horizons: dict[str, dict[str, float]] = {"1": probabilities}
        propagated = probabilities
        for step in range(2, 6):
            propagated = _propagate(propagated, transition_matrix)
            horizons[str(step)] = {
                key: round(value, 6)
                for key, value in propagated.items()
            }
        quantum = quantum_inspired_projection(last)
        uncertainty = round(_uncertainty(probabilities), 6)
        verification = (
            "SIMULATED_DETERMINISTIC"
            if source_class == "SIMULATED"
            else "OPERATOR_DECLARED_NOT_INDEPENDENTLY_VERIFIED"
        )
        dimension_state = {
            "time": {"value": last.t_ms, "unit": "ms"},
            "channel_occupancy": {"value": last.active_ratio, "unit": "ratio"},
            "population_rate": {"value": last.population_rate_hz, "unit": "spikes_per_second"},
            "channel_entropy": {"value": last.normalized_entropy, "unit": "normalized"},
            "temporal_persistence": {"value": last.temporal_persistence, "unit": "ratio"},
            "vector_similarity": {"value": last.vector_similarity, "unit": "cosine"},
            "rate_acceleration": {"value": last.acceleration, "unit": "bounded_score"},
            "burst_index": {"value": last.burst_index, "unit": "bounded_score"},
            "spectral_proxy": {"value": last.spectral_proxy, "unit": "bounded_proxy"},
            "geometry_proxy": {"value": last.geometry_proxy, "unit": "bounded_proxy"},
            "phase_proxy": {"value": last.phase_proxy, "unit": "bounded_proxy"},
            "confluence": {"value": last.confluence, "unit": "bounded_index"},
            "forecast_uncertainty": {"value": uncertainty, "unit": "normalized_entropy"},
            "provenance": {"value": source_class, "unit": "label"},
            "causal_status": {"value": "DESCRIPTIVE_ONLY", "unit": "label"},
            "verification": {"value": verification, "unit": "label"},
        }

        return {
            "schema": "gpt-doug-qbio-spike-confluence/v1",
            "mode": "THEORETICAL_QUANTUM_BIOCHIP_SIMULATION",
            "source_class": source_class,
            "biological_causality_claim": False,
            "quantum_hardware_claim": False,
            "physical_control": False,
            "channel_count": channel_count,
            "frame_count": len(frames),
            "window": self.window,
            "sequence": [
                {
                    **item.__dict__,
                    "state": state,
                }
                for item, state in zip(features, states)
            ],
            "forecast": {
                "next_state_probabilities": probabilities,
                "most_probable_next_state": max(probabilities, key=probabilities.get),
                "uncertainty": uncertainty,
                "confidence_proxy": round(1.0 - uncertainty, 6),
                "calibrated": False,
                "transition_matrix": {
                    left: {
                        right: round(value, 6)
                        for right, value in row.items()
                    }
                    for left, row in transition_matrix.items()
                },
                "horizon_steps_1_to_5": horizons,
                "note": "Probabilities are heuristic/sequence-derived research scores, not clinical or biological predictions.",
            },
            "quantum_inspired": quantum,
            "dimensions": {
                "count": len(FEATURE_DIMENSIONS),
                "axes": list(FEATURE_DIMENSIONS),
                "state": dimension_state,
                "interpretation": "classical feature projections; no extra physical dimensions are claimed",
            },
        }


def analyze_sequence(
    frames: Iterable[SpikeFrame],
    *,
    window: int = 8,
    source_class: str = "SIMULATED",
) -> dict:
    bounded: list[SpikeFrame] = []
    for frame in frames:
        if len(bounded) >= MAX_FRAMES:
            raise ValueError(f"at most {MAX_FRAMES} frames are supported per analysis")
        bounded.append(frame)
    return SequentialSpikeModel(window=window).analyze(bounded, source_class=source_class)
