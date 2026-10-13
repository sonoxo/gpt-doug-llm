"""BioPINEAL: local-heartbeat status plus a bounded classical quantum analogy.

'Mitochondrial' compute units are a synthetic operation-count budget, NOT
biological ATP, measured electrical energy, or a real quantum coprocessor.
"""
from __future__ import annotations

import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_QUBITS = 6
MAX_GATES = 128
MAX_SHOTS = 1024
MAX_BUDGET = 1000000


def read_biochip_telemetry(memory_root: Path, *, stale_after: float = 20.0) -> dict[str, Any]:
    root = Path(memory_root).expanduser()
    path = root / 'working' / 'heartbeat.json'
    result: dict[str, Any] = {
        'system': 'GPT-Doug BioPINEAL',
        'heart': 'MISSING',
        'authority': 'RESEARCH_ONLY',
        'quantum_hardware_used': False,
        'gpu_usage': 'UNMEASURED',
        'ram_gb': {'used': None, 'total': None},
        'cpu_load_1m': None,
        'heartbeat_age_seconds': None,
    }
    if not path.is_file() or path.is_symlink():
        return result
    try:
        if path.stat().st_size > 65536:
            raise ValueError('oversized heartbeat')
        state = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(state, dict):
            raise ValueError('heartbeat is not JSON object')
        timestamp = state['timestamp']
        if type(timestamp) in (int, float):
            stamp = float(timestamp)
        elif isinstance(timestamp, str):
            when = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if when.tzinfo is None:
                raise ValueError('heartbeat missing timezone')
            stamp = when.timestamp()
        else:
            raise ValueError('bad heartbeat timestamp')
        if not math.isfinite(stamp):
            raise ValueError('nonfinite timestamp')
        age = time.time() - stamp
        if age < -5:
            result['heart'] = 'FUTURE_TIMESTAMP'
        elif age > stale_after:
            result['heart'] = 'STALE'
        else:
            result['heart'] = 'LIVE' if state.get('heart') == 'BEATING' else 'UNCONFIRMED'
        result['heartbeat_age_seconds'] = round(max(0.0, age), 1)
        ram = state.get('ram', {})
        if isinstance(ram, dict):
            used, total = ram.get('used_gb'), ram.get('total_gb')
            if all(type(v) in (float, int) and math.isfinite(v) and v >= 0 for v in (used, total)) and used <= total:
                result['ram_gb'] = {'used': round(used, 2), 'total': round(total, 2)}
        load = state.get('load')
        if isinstance(load, list) and load and type(load[0]) in (int, float) and math.isfinite(load[0]) and load[0] >= 0:
            result['cpu_load_1m'] = round(float(load[0]), 3)
    except (ValueError, OSError, KeyError, TypeError, OverflowError):
        result['heart'] = 'INVALID'
    return result


def _int(value: Any, name: str, smallest: int, largest: int) -> int:
    if type(value) is not int or not smallest <= value <= largest:
        raise ValueError(name + ' out of bounds')
    return value


def _validate(problem: Any, budget_units: int) -> dict[str, Any]:
    _int(budget_units, 'mitochondrial abstract compute budget', 1, MAX_BUDGET)
    if not isinstance(problem, dict) or set(problem) != {'qubits', 'initial_basis', 'gates', 'shots', 'seed'}:
        raise ValueError('invalid quantum research problem schema')
    n = _int(problem['qubits'], 'qubits', 1, MAX_QUBITS)
    _int(problem['initial_basis'], 'initial_basis', 0, (1 << n) - 1)
    _int(problem['shots'], 'shots', 0, MAX_SHOTS)
    _int(problem['seed'], 'seed', 0, 2 ** 32 - 1)
    gates = problem['gates']
    if not isinstance(gates, list) or len(gates) > MAX_GATES:
        raise ValueError('gates out of bounds')
    for gate in gates:
        if not isinstance(gate, dict):
            raise ValueError('gate must be object')
        kind = gate.get('gate')
        if kind in {'H', 'X', 'Z'} and set(gate) == {'gate', 'target'}:
            _int(gate['target'], 'target', 0, n - 1)
        elif kind == 'CNOT' and set(gate) == {'gate', 'control', 'target'}:
            control = _int(gate['control'], 'control', 0, n - 1)
            target = _int(gate['target'], 'target', 0, n - 1)
            if control == target:
                raise ValueError('CNOT requires distinct control and target')
        else:
            raise ValueError('unrecognized or malformed unitary gate')
    units = (1 << n) * (1 + len(gates)) + problem['shots']
    if units > budget_units:
        raise ValueError('mitochondrial abstract compute budget exceeded')
    return problem


def simulate_biomito_quantum(problem: dict[str, Any], *, budget_units: int = 1000) -> dict[str, Any]:
    _validate(problem, budget_units)
    n = problem['qubits']
    dim = 1 << n
    amplitudes = [0j for _ in range(dim)]
    amplitudes[problem['initial_basis']] = 1 + 0j
    root2 = math.sqrt(2.0)
    for gate in problem['gates']:
        kind = gate['gate']
        bit = 1 << gate['target']
        if kind == 'Z':
            for i in range(dim):
                if i & bit:
                    amplitudes[i] *= -1
        elif kind == 'CNOT':
            ctrl = 1 << gate['control']
            for i in range(dim):
                if (i & ctrl) and not (i & bit):
                    j = i | bit
                    amplitudes[i], amplitudes[j] = amplitudes[j], amplitudes[i]
        else:
            for i in range(dim):
                if i & bit:
                    continue
                j = i | bit
                a, b = amplitudes[i], amplitudes[j]
                if kind == 'H':
                    amplitudes[i], amplitudes[j] = (a + b) / root2, (a - b) / root2
                elif kind == 'X':
                    amplitudes[i], amplitudes[j] = b, a
    raw_probs = [abs(a) ** 2 for a in amplitudes]
    if abs(sum(raw_probs) - 1.0) > 1e-10:
        raise ValueError('quantum toy state failed normalization')
    probs = [round(x, 12) for x in raw_probs]
    keys = [format(i, f'0{n}b') for i in range(dim)]
    units = dim * (1 + len(problem['gates'])) + problem['shots']
    sampled = None
    if problem['shots']:
        # A local pseudorandom sample, not measurements on quantum hardware.
        rng = random.Random(problem['seed'])
        counts = dict.fromkeys(keys, 0)
        for _ in range(problem['shots']):
            t = rng.random()
            cumulative = 0.0
            selected = keys[-1]
            for k, p in zip(keys, raw_probs):
                cumulative += p
                if t <= cumulative:
                    selected = k
                    break
            counts[selected] += 1
        sampled = counts
    return {
        'system': 'GPT-Doug BioPINEAL Mitochondrial Quantum Research',
        'model': 'CLASSICAL_STATEVECTOR',
        'model_scope': 'TOY_MATHEMATICAL_RESEARCH',
        'authority': 'RESEARCH_ONLY',
        'classical_simulation': True,
        'quantum_hardware_used': False,
        'physical_extra_dimensions_accessed': False,
        'energy_unit_kind': 'ABSTRACT_COMPUTE_OPERATIONS_NOT_ATP',
        'compute_units_consumed': units,
        'budget_units': budget_units,
        'budget_units_remaining': budget_units - units,
        'basis_probabilities': dict(zip(keys, probs)),
        'shots': problem['shots'],
        'sampled_counts': sampled,
        'seed': problem['seed'],
        'qubits': n,
        'gates': len(problem['gates']),
        'external_calls': 0,
    }
