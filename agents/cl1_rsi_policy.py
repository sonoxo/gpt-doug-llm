"""CL1-inspired synthetic electrophysiology decoding target for bounded RSI.

This is a deterministic software exercise over synthetic spike-count/rate bins.
It does not open cl-sdk, use physical CL1 hardware, or establish biological learning.
Only this file may be edited in the dedicated CL1 RSI improvement profile.
"""
from __future__ import annotations

import math


def decode_activity(rates: list[float], baseline: float) -> list[int]:
    """Decode high/low activity from nonnegative synthetic sample rates.

    Parameters are sample rates per fixed synthetic bin and a known per-session
    baseline. The intentionally simple initial decoder is a benchmark baseline:
    the held-out evaluator verifies whether this simple temporal denoiser helps.
    """
    if isinstance(baseline, bool) or not isinstance(baseline, (float, int)):
        raise ValueError("baseline must be finite and positive")
    if not math.isfinite(baseline) or baseline <= 0:
        raise ValueError("baseline must be finite and positive")
    if not isinstance(rates, list) or len(rates) > 1024:
        raise ValueError("rates must be a bounded list")
    if any(
        isinstance(value, bool) or not isinstance(value, (float, int))
        or not math.isfinite(value) or value < 0
        for value in rates
    ):
        raise ValueError("rates must be nonnegative finite numbers")
    raw = [1 if value >= 1.27 * baseline else 0 for value in rates]
    if len(raw) < 3:
        return raw
    # A 3-bin median filter suppresses one-bin readout glitches while retaining
    # all sustained activity transitions. It never invents a biological state.
    denoised = raw.copy()
    for index in range(1, len(raw) - 1):
        if raw[index - 1] == raw[index + 1]:
            denoised[index] = raw[index - 1]
    return denoised
