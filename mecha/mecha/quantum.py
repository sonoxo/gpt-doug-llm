"""Bounded classical statevector mathematics, not quantum hardware."""
from __future__ import annotations
import math
import random
from typing import Any, Mapping

MAX_QUBITS=6
MAX_GATES=128
MAX_SHOTS=1024
MAX_BUDGET=1000000


def _bounded_int(value: Any, name: str, lo: int, hi: int) -> int:
    if type(value) is not int or not lo<=value<=hi:
        raise ValueError(name+' outside allowed classical simulation limits')
    return value


def simulate_quantum(problem: Mapping[str,Any], *, budget_units: int = 200) -> dict[str,Any]:
    _bounded_int(budget_units,'abstract compute budget',1,MAX_BUDGET)
    if (not isinstance(problem,dict) or
        set(problem)!={'qubits','initial_basis','gates','shots','seed'}):
        raise ValueError('quantum problem must use exact approved fields')
    n=_bounded_int(problem['qubits'],'qubits',1,MAX_QUBITS)
    dimension=1<<n
    basis=_bounded_int(problem['initial_basis'],'initial basis',0,dimension-1)
    shots=_bounded_int(problem['shots'],'shots',0,MAX_SHOTS)
    seed=_bounded_int(problem['seed'],'seed',0,2**32-1)
    gates=problem['gates']
    if not isinstance(gates,list) or len(gates)>MAX_GATES:
        raise ValueError('gate count exceeds classical simulation cap')
    for gate in gates:
        if not isinstance(gate,dict):
            raise ValueError('malformed gate')
        kind=gate.get('gate')
        if kind in ('H','X','Z') and set(gate)=={'gate','target'}:
            _bounded_int(gate['target'],'gate target',0,n-1)
        elif kind=='CNOT' and set(gate)=={'gate','control','target'}:
            ctrl=_bounded_int(gate['control'],'control',0,n-1)
            target=_bounded_int(gate['target'],'target',0,n-1)
            if ctrl==target:
                raise ValueError('CNOT requires distinct indices')
        else:
            raise ValueError('unrecognized or malformed unitary gate')
    units=dimension*(1+len(gates))+shots
    if units>budget_units:
        raise ValueError('mitochondrial abstract compute budget exceeded')
    amplitudes=[0j]*dimension
    amplitudes[basis]=complex(1,0)
    root2=math.sqrt(2.0)
    for gate in gates:
        kind=gate['gate']
        mask=1<<gate['target']
        if kind=='Z':
            for i in range(dimension):
                if i&mask:
                    amplitudes[i]*=-1
        elif kind=='CNOT':
            control=1<<gate['control']
            for i in range(dimension):
                if (i&control) and not (i&mask):
                    j=i|mask
                    amplitudes[i],amplitudes[j]=amplitudes[j],amplitudes[i]
        else:
            for i in range(dimension):
                if i&mask:
                    continue
                j=i|mask
                a,b=amplitudes[i],amplitudes[j]
                if kind=='H':
                    amplitudes[i]=(a+b)/root2
                    amplitudes[j]=(a-b)/root2
                else:
                    amplitudes[i],amplitudes[j]=b,a
    raw=[abs(a)**2 for a in amplitudes]
    if not math.isfinite(sum(raw)) or abs(sum(raw)-1.0)>1e-10:
        raise ValueError('invalid statevector normalization')
    keys=[format(i,'0{}b'.format(n)) for i in range(dimension)]
    probabilities=dict(zip(keys,[round(x,12) for x in raw]))
    sampled=None
    if shots:
        rng=random.Random(seed)
        drawn=rng.choices(keys,weights=raw,k=shots)
        sampled={k:drawn.count(k) for k in keys}
    return {
        'type':'ClassicalStatevectorStudy','source_kind':'SYNTHETIC',
        'authority':'RESEARCH_ONLY','qubits':n,'gates_applied':len(gates),
        'seed':seed,'shots':shots,'probabilities':probabilities,
        'sampled_counts':sampled,'normalization_tolerance':1e-10,
        'classical_simulation':True,'quantum_hardware_used':False,
        'mitochondrial_energy_measured':False,'compute_units_used':units,
        'compute_units_remaining':budget_units-units,
    }
