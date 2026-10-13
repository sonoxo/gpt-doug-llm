"""Host-only optional, read-only BioPINEAL and synthetic rover references.

Operator callsigns in host_status() are session-private. Never persist or send
this result to a public MECHA snapshot or research publication.
"""
from __future__ import annotations
import importlib
import json
from pathlib import Path
from typing import Any, Mapping

_ROOT=Path(__file__).resolve().parents[2]
_ROVER_CONTRACT=_ROOT/'robotics-intel-site'/'rover-connector-contract.json'
_ZYRA_SCHEMA=_ROOT/'safety-shield'/'ontology'/'zyra-mss-v1.json'


def _rover_contract() -> dict[str,Any]:
    result={'status':'ADAPTER_UNAVAILABLE','command_write':False,
            'real_robot_connected':False}
    path=_ROVER_CONTRACT
    if not path.is_file():
        return result
    if path.is_symlink() or path.stat().st_size>16384:
        return dict(result,status='UNSAFE_CONTRACT_REJECTED')
    try:
        contract=json.loads(path.read_text(encoding='utf-8'))
        defaults=contract['defaults']
        if (contract.get('schema')!='xunia.maven.rover-connector.v1' or
            not isinstance(defaults,dict) or defaults.get('command_write') is not False):
            return dict(result,status='UNSAFE_CONTRACT_REJECTED')
    except (OSError, UnicodeError, ValueError,KeyError,TypeError):
        return dict(result,status='UNSAFE_CONTRACT_REJECTED')
    return dict(result,status='READ_ONLY_TEMPLATE')


def host_status(*,memory_root: Path | None=None,
                operator_workspace: Path | None=None) -> dict[str,Any]:
    """Present only user-selected host metadata; never elevate authority."""
    data={'system':'GPT-DOUG-MECHA-HOST','authority':'RESEARCH_ONLY',
          'source_kind':'SYNTHETIC','operator':None,
          'heartbeat':{'heart':'ADAPTER_UNAVAILABLE'},
          'robotics':_rover_contract(),
          'zyra_schema':{'status':'ADAPTER_UNAVAILABLE'},
          'external_calls':0,'real_world_actuation':False}
    if _ZYRA_SCHEMA.is_file() and not _ZYRA_SCHEMA.is_symlink():
        data['zyra_schema']={'status':'REFERENCE_AVAILABLE_READ_ONLY'}
    if memory_root is not None:
        try:
            module=importlib.import_module('research_lab.warfighter.biopineal')
        except (ImportError,ModuleNotFoundError):
            pass
        else:
            reading=module.read_biochip_telemetry(memory_root)
            data['heartbeat']={k:reading[k] for k in
                               ('heart','heartbeat_age_seconds','gpu_usage','ram_gb','cpu_load_1m')
                               if k in reading}
    if operator_workspace is not None:
        try:
            module=importlib.import_module('research_lab.warfighter.operator_profile')
        except (ImportError,ModuleNotFoundError):
            pass
        else:
            profile=module.read_operator(operator_workspace)
            if profile is not None:
                if (profile.get('identity_verified') is not False or
                    profile.get('military_affiliation_verified') is not False or
                    profile.get('granted_permissions')!=[]):
                    raise ValueError('private profile cannot grant host privileges')
                data['operator']={'callsign':profile['callsign'],
                                  'identity_state':'SELF_DECLARED',
                                  'government_credential_verified':False,
                                  'military_affiliation_verified':False}
    return data


def host_quantum_comparison(problem: Mapping[str,Any]) -> dict[str,Any]:
    """Compare two toy model outputs, not physical or independent validation."""
    from mecha.quantum import simulate_quantum
    local=simulate_quantum(dict(problem),budget_units=1000)
    result={'authority':'RESEARCH_ONLY','status':'ADAPTER_UNAVAILABLE',
            'proof_scope':'CLASSICAL_MODEL_ONLY','quantum_hardware_used':False,
            'external_calls':0,'compared_seed':local['seed']}
    try:
        module=importlib.import_module('research_lab.warfighter.biopineal')
    except (ImportError,ModuleNotFoundError):
        return result
    reference=module.simulate_biomito_quantum(dict(problem),budget_units=1000)
    actual=reference.get('basis_probabilities')
    expected=local['probabilities']
    matches=(isinstance(actual,dict) and set(expected)==set(actual) and
             all(type(actual[k]) in (int,float) and
                 abs(expected[k]-actual[k])<=1e-11 for k in expected))
    result['status']='MATCH' if matches else 'MISMATCH'
    result['sample_counts_compared']=False
    result['comparison']='Numerical probabilities only; not independent scientific proof'
    return result
