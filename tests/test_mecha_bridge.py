import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from integrations.mecha_bridge.adapters import host_status,host_quantum_comparison
from mecha.quantum import simulate_quantum

BELL={'qubits':2,'initial_basis':0,
      'gates':[{'gate':'H','target':0},{'gate':'CNOT','control':0,'target':1}],
      'shots':0,'seed':0}


class TestMechaBridge(unittest.TestCase):
    def test_empty_host_reports_unavailable_without_db_or_network(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with patch('socket.socket',side_effect=AssertionError('network forbidden')):
                s=host_status(memory_root=root,operator_workspace=root/'no-workspace')
            self.assertEqual(s['authority'],'RESEARCH_ONLY')
            self.assertEqual(s['external_calls'],0)
            self.assertIsNone(s['operator'])
            self.assertEqual(s['heartbeat']['heart'],'MISSING')
            self.assertFalse(s['robotics']['command_write'])
            self.assertFalse((root/'no-workspace').exists())
            self.assertFalse(any(root.rglob('*.sqlite*')))

    def test_self_declared_agent10_is_private_and_unverified(self):
        from research_lab.warfighter.operator_profile import register_operator
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);register_operator(root/'profile','Agent10')
            out=host_status(operator_workspace=root/'profile',memory_root=root/'memory')
            self.assertEqual(out['operator']['callsign'],'Agent10')
            self.assertEqual(out['operator']['identity_state'],'SELF_DECLARED')
            self.assertFalse(out['operator']['government_credential_verified'])
            self.assertFalse(out['operator']['military_affiliation_verified'])
            self.assertFalse(out['robotics']['command_write'])

    def test_stale_heartbeat_never_called_live(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);h=root/'working'/'heartbeat.json';h.parent.mkdir()
            h.write_text(json.dumps({'heart':'BEATING','timestamp':datetime.fromtimestamp(time.time()-250,timezone.utc).isoformat()}))
            before=h.read_bytes()
            out=host_status(memory_root=root)
            self.assertEqual(out['heartbeat']['heart'],'STALE')
            self.assertEqual(before,h.read_bytes())

    def test_missing_optional_dependency_reports_unavailable(self):
        with patch('importlib.import_module',side_effect=ModuleNotFoundError('not installed')):
            status=host_status()
            check=host_quantum_comparison(BELL)
        self.assertEqual(status['heartbeat']['heart'],'ADAPTER_UNAVAILABLE')
        self.assertEqual(check['status'],'ADAPTER_UNAVAILABLE')
        self.assertEqual(check['external_calls'],0)

    def test_host_quantum_compares_actual_classical_probabilities(self):
        comparison=host_quantum_comparison(BELL)
        self.assertEqual(comparison['status'],'MATCH')
        self.assertEqual(comparison['proof_scope'],'CLASSICAL_MODEL_ONLY')
        self.assertFalse(comparison['quantum_hardware_used'])
        self.assertEqual(comparison['external_calls'],0)

    def test_rover_contract_cannot_grant_hardware_control(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'rover.json'
            p.write_text(json.dumps({'schema':'xunia.maven.rover-connector.v1','defaults':{'command_write':True}}))
            with patch('integrations.mecha_bridge.adapters._ROVER_CONTRACT',p):
                status=host_status()
            self.assertFalse(status['robotics']['command_write'])
            self.assertEqual(status['robotics']['status'],'UNSAFE_CONTRACT_REJECTED')


if __name__=='__main__':unittest.main()
