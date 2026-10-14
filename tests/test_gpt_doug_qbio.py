import math

import pytest

from gpt_doug_qbio.core import (
    FEATURE_DIMENSIONS,
    OUTCOME_STATES,
    SequentialSpikeModel,
    SpikeFrame,
    analyze_sequence,
    quantum_inspired_projection,
)


def frames():
    return [
        SpikeFrame(0.0, (0, 0, 0, 0)),
        SpikeFrame(20.0, (1, 0, 1, 0)),
        SpikeFrame(40.0, (1, 1, 1, 0)),
        SpikeFrame(60.0, (2, 1, 2, 1)),
        SpikeFrame(80.0, (3, 2, 3, 2)),
    ]


def test_sequence_report_has_probabilities_and_dimensions():
    report = analyze_sequence(frames(), window=3)
    probs = report["forecast"]["next_state_probabilities"]
    assert set(probs) == set(OUTCOME_STATES)
    assert math.isclose(sum(probs.values()), 1.0, abs_tol=1e-5)
    assert report["dimensions"]["count"] == 16
    assert tuple(report["dimensions"]["axes"]) == FEATURE_DIMENSIONS


def test_quantum_layer_is_explicitly_classical():
    report = analyze_sequence(frames(), window=3)
    q = report["quantum_inspired"]
    assert q["mode"] == "CLASSICAL_QUANTUM_INSPIRED"
    assert q["hardware_quantum"] is False
    assert math.isclose(sum(q["measurement_probabilities"]), 1.0, abs_tol=1e-5)


def test_no_physical_or_causal_claims():
    report = SequentialSpikeModel(window=3).analyze(frames(), source_class="MEASURED_READ_ONLY")
    assert report["physical_control"] is False
    assert report["biological_causality_claim"] is False
    assert report["quantum_hardware_claim"] is False


def test_timestamps_must_be_increasing():
    bad = [SpikeFrame(0.0, (1, 0)), SpikeFrame(0.0, (0, 1))]
    with pytest.raises(ValueError):
        analyze_sequence(bad)


def test_channel_count_must_match():
    bad = [SpikeFrame(0.0, (1, 0)), SpikeFrame(1.0, (0, 1, 0))]
    with pytest.raises(ValueError):
        analyze_sequence(bad)


def test_negative_counts_rejected():
    with pytest.raises(ValueError):
        SpikeFrame(0.0, (1, -1))
