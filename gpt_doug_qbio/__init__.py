"""GPT-Doug quantum-inspired spike-confluence research layer."""

from .core import (
    FEATURE_DIMENSIONS,
    OUTCOME_STATES,
    SequentialSpikeModel,
    SpikeFrame,
    analyze_sequence,
    quantum_inspired_projection,
)

__all__ = [
    "FEATURE_DIMENSIONS",
    "OUTCOME_STATES",
    "SequentialSpikeModel",
    "SpikeFrame",
    "analyze_sequence",
    "quantum_inspired_projection",
]
