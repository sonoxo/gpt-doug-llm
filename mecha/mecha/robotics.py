"""Finite invented rover exercise; never a controller or command generator."""
from __future__ import annotations
import math
from typing import Any
from .contracts import validate_fixture,digest


def simulate_rover(fixture: dict[str, Any], *, steps: int = 3) -> dict[str, Any]:
    if type(steps) is not int or not 1 <= steps <= 20:
        raise ValueError('simulated step count must be integer 1..20')
    data=validate_fixture(fixture)
    pose=[float(x) for x in data['robot']['pose']]
    obstacles=data['environment']['obstacles']
    energy=data['robot']['power_budget_units']
    executed=0
    status='SIMULATED_STEP_COMPLETE'
    for _ in range(steps):
        if energy==0:
            status='SIMULATED_POWER_EXHAUSTED'
            break
        candidate=[round(pose[0]+0.25,6), pose[1], pose[2]]
        if candidate[0]>100:
            status='SIMULATED_BOUNDARY_HALT'
            break
        if any(math.dist(candidate, obstacle)<0.5 for obstacle in obstacles):
            status='SIMULATED_OBSTACLE_HALT'
            break
        pose=candidate
        energy-=1
        executed+=1
    if executed==steps and energy==0:
        status='SIMULATED_POWER_EXHAUSTED'
    return {'simulated_pose':pose,'simulated_steps':executed,
            'simulated_power_remaining':energy,
            'sensor_health_pct':data['robot']['health_pct'],
            'simulation_status':status,'source_kind':'SYNTHETIC',
            'authority':'RESEARCH_ONLY','REAL_WORLD_ACTUATION':False,
            'requested_steps':steps,'source_sha256':digest(data)}
