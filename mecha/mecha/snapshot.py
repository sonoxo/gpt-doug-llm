"""Public-safe six-channel snapshot derived only from validated toy states."""
from __future__ import annotations
import json
import math
from typing import Any
from .contracts import validate_fixture,digest,canonical_json
from .robotics import simulate_rover

_SIM_STATUSES=frozenset({'SIMULATED_STEP_COMPLETE','SIMULATED_OBSTACLE_HALT',
                         'SIMULATED_POWER_EXHAUSTED','SIMULATED_BOUNDARY_HALT'})


def build_snapshot(fixture: dict[str, Any], model_state: dict[str, Any],
                   *, model_version: str = '1.0.0') -> dict[str, Any]:
    data=validate_fixture(fixture)
    if not isinstance(model_state,dict) or model_version!='1.0.0':
        raise ValueError('invalid simulation state or model version')
    if model_state.get('REAL_WORLD_ACTUATION') is not False:
        raise ValueError('a simulated state may never have real actuation')
    requested_steps=model_state.get('requested_steps')
    # Replay the bounded model; untrusted but numerically plausible state fields
    # cannot be relabeled as evidence from another fixture or changed post-run.
    replay=simulate_rover(data,steps=requested_steps)
    bound=('source_sha256','requested_steps','simulated_pose','simulated_steps',
           'simulated_power_remaining','sensor_health_pct','simulation_status',
           'source_kind','authority','REAL_WORLD_ACTUATION')
    if any(model_state.get(key)!=replay[key] for key in bound):
        raise ValueError('simulation and source fixture replay mismatch')
    status=model_state.get('simulation_status')
    if status not in _SIM_STATUSES:
        raise ValueError('invalid synthetic simulation status')
    pose=model_state.get('simulated_pose')
    if (not isinstance(pose,list) or len(pose)!=3 or
        any(type(n) not in (int,float) or not math.isfinite(n) or not -100<=n<=100 for n in pose)):
        raise ValueError('invalid simulated coordinates')
    step=model_state.get('simulated_steps')
    rem=model_state.get('simulated_power_remaining')
    health=model_state.get('sensor_health_pct')
    if (type(step) is not int or not 0<=step<=20 or
        type(rem) is not int or not 0<=rem<=1000000 or
        type(health) is not int or not 0<=health<=100):
        raise ValueError('invalid synthetic result metrics')
    if model_state.get('authority')!='RESEARCH_ONLY' or model_state.get('source_kind')!='SYNTHETIC':
        raise ValueError('simulation cannot assert operational authority')
    result={
        'schema_version':'1.0.0','type':'MechaSnapshot',
        'system':'GPT-DOUG-MECHA','model_version':model_version,
        'source_kind':'SYNTHETIC','authority':'RESEARCH_ONLY',
        'mode':'OFFLINE_ROBOTICS_DEMO','source_sha256':digest(data),
        'real_world_actuation':False,'quantum_hardware_used':False,
        'biological_hardware_connected':False,
        'channels':{
            'x':float(pose[0]),'y':float(pose[1]),'z':float(pose[2]),
            'time':{'simulated_step':step},
            'memory':'SOURCE_LABELS_ONLY',
            'compute':'ABSTRACT_SIMULATION_OPERATIONS',
        },
        'simulated_rover':{
            'status':status,'power_budget_units_remaining':rem,
            'synthetic_sensor_health_pct':health,
        },
        'external_calls':0,
    }
    if len(canonical_json(result))>1024*1024:
        raise ValueError('snapshot exceeds 1 MiB')
    return result
