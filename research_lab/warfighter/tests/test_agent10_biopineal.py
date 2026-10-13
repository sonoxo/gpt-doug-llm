"""Pseudonymous local operator and research-only energy/quantum analogy."""
import contextlib
import io
import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from research_lab.warfighter.operator_profile import register_operator, read_operator
from research_lab.warfighter.biopineal import read_biochip_telemetry, simulate_biomito_quantum
from research_lab.warfighter.cli import main


class OperatorProfileTests(unittest.TestCase):
    def test_agent10_registers_only_local_unverified_alias(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'private'
            profile = register_operator(root, 'Agent10')
            self.assertEqual(profile['callsign'], 'Agent10')
            self.assertEqual(profile['identity_verified'], False)
            self.assertEqual(profile['military_affiliation_verified'], False)
            self.assertEqual(profile['authority'], 'RESEARCH_ONLY')
            self.assertEqual(profile['identity_source'], 'SELF_DECLARED')
            self.assertEqual(profile['source_system'], 'LOCAL_ONLY')
            self.assertTrue(profile['created_at'].endswith('+00:00'))
            path = root / 'operator-profile.json'
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(read_operator(root), profile)
            self.assertEqual(register_operator(root, 'Agent10'), profile)
            self.assertEqual(json.loads(path.read_text()), profile)
            with self.assertRaisesRegex(ValueError, 'different callsign'):
                register_operator(root, 'Agent11')

    def test_profile_cannot_claim_new_privileges_by_editing_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            register_operator(root, 'Agent10')
            path = root / 'operator-profile.json'
            data = json.loads(path.read_text())
            data['granted_permissions'] = ['ADMIN']
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'credentials or authority'):
                read_operator(root)

    def test_invalid_and_symlinked_operator_profile_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for callsign in ('../Agent10', 'A\nB', 'Agent 10', '', 'a' * 64):
                with self.subTest(callsign=callsign), self.assertRaises(ValueError):
                    register_operator(root / 'profiles', callsign)
            other = root / 'other.json'
            other.write_text('{}')
            folder = root / 'linked'
            folder.mkdir()
            (folder / 'operator-profile.json').symlink_to(other)
            with self.assertRaises(ValueError):
                register_operator(folder, 'Agent10')
            self.assertEqual(other.read_text(), '{}')


class BioPinealTests(unittest.TestCase):
    def _heartbeat(self, root, age_seconds=1):
        hb=root/'working'/'heartbeat.json'
        hb.parent.mkdir(parents=True, exist_ok=True)
        payload={
            'heart':'BEATING',
            'timestamp':datetime.fromtimestamp(time.time()-age_seconds,timezone.utc).isoformat(),
            'ram':{'used_gb':6.0,'total_gb':8.0},
            'load':[1.3,2.0,2.0],
            'machine':'arm64',
        }
        hb.write_text(json.dumps(payload))
        return hb

    def test_heartbeat_is_read_only_and_stale_is_not_online(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            f=self._heartbeat(root,250)
            before=f.read_bytes()
            out=read_biochip_telemetry(root)
            self.assertEqual(out['heart'], 'STALE')
            self.assertGreaterEqual(out['heartbeat_age_seconds'],245)
            self.assertEqual(out['ram_gb']['total'],8.0)
            self.assertEqual(out['cpu_load_1m'],1.3)
            self.assertEqual(out['gpu_usage'],'UNMEASURED')
            self.assertEqual(f.read_bytes(),before)
            self._heartbeat(root,1)
            self.assertEqual(read_biochip_telemetry(root)['heart'], 'LIVE')
            f.unlink()
            self.assertEqual(read_biochip_telemetry(root)['heart'], 'MISSING')

    def test_bell_state_is_classical_and_budgeted(self):
        request={
            'qubits':2,'initial_basis':0,
            'gates':[{'gate':'H','target':0}, {'gate':'CNOT','control':0,'target':1}],
            'shots':0,'seed':0,
        }
        output=simulate_biomito_quantum(request,budget_units=200)
        self.assertEqual(output['quantum_hardware_used'],False)
        self.assertEqual(output['model'],'CLASSICAL_STATEVECTOR')
        self.assertEqual(output['energy_unit_kind'],'ABSTRACT_COMPUTE_OPERATIONS_NOT_ATP')
        self.assertEqual(output['authority'],'RESEARCH_ONLY')
        self.assertEqual(output['basis_probabilities']['00'],0.5)
        self.assertEqual(output['basis_probabilities']['11'],0.5)
        self.assertEqual(output['basis_probabilities']['01'],0.0)
        self.assertEqual(output['basis_probabilities']['10'],0.0)
        self.assertGreater(output['compute_units_consumed'],0)
        self.assertLessEqual(output['compute_units_consumed'],200)
        self.assertEqual(simulate_biomito_quantum(request,budget_units=200),output)
        with self.assertRaisesRegex(ValueError,'budget'):
            simulate_biomito_quantum(request,budget_units=1)

    def test_invalid_quantum_input_bounded_and_no_extra_dimensions_claim(self):
        base={'qubits':1,'initial_basis':0,'gates':[{'gate':'H','target':0}], 'shots':0, 'seed':1}
        for overrides in ({'qubits':7}, {'gates':[{'gate':'H','target':0}]*129},
                          {'shots':1025}, {'qubits':True}, {'initial_basis':2},
                          {'gates':[{'gate':'CNOT','control':0,'target':0}]},
                          {'gates':[{'gate':'DANGEROUS','target':0}]},
                          {'seed':-1}, {'secret':'NO'}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                simulate_biomito_quantum({**base,**overrides}, budget_units=1000000)
        value=simulate_biomito_quantum(base,budget_units=100)
        self.assertFalse(value['physical_extra_dimensions_accessed'])
        self.assertEqual(value['model_scope'],'TOY_MATHEMATICAL_RESEARCH')

    def test_cli_register_operator_and_biopineal_status(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            hb=root/'memory'
            self._heartbeat(hb, 250)
            buf=io.StringIO()
            with contextlib.redirect_stdout(buf):
                exitcode=main(['operator','register','--callsign','Agent10','--workspace',str(root/'w')])
            self.assertEqual(exitcode,0)
            registration=json.loads(buf.getvalue())
            self.assertFalse(registration['military_affiliation_verified'])
            buf=io.StringIO()
            with contextlib.redirect_stdout(buf):
                exitcode=main(['biopineal','status','--memory-root',str(hb),'--workspace',str(root/'w')])
            self.assertEqual(exitcode,0)
            result=json.loads(buf.getvalue())
            self.assertEqual(result['operator']['callsign'],'Agent10')
            self.assertEqual(result['heart'],'STALE')
            self.assertEqual(result['authority'],'RESEARCH_ONLY')

    def test_biopineal_simulation_cli_is_no_network_and_no_database(self):
        with tempfile.TemporaryDirectory() as td:
            workspace=Path(td)
            inp=workspace/'bell.json'
            inp.write_text(json.dumps({'qubits':2,'initial_basis':0,'gates':[
                {'gate':'H','target':0},{'gate':'CNOT','control':0,'target':1}],
                'shots':0,'seed':0}))
            buf=io.StringIO()
            with contextlib.redirect_stdout(buf):
                exitcode=main(['biopineal','simulate',str(inp),'--input-root',str(workspace),'--budget-units','200'])
            self.assertEqual(exitcode,0)
            result=json.loads(buf.getvalue())
            self.assertEqual(result['basis_probabilities']['00'],0.5)
            self.assertFalse((workspace/'research.sqlite3').exists())
            self.assertFalse((workspace/'operator-profile.json').exists())


if __name__=='__main__':
    unittest.main()
