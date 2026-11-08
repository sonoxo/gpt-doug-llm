"""CL1 skeletal mechanical ontology regressions: pure offline numeric simulation."""
from __future__ import annotations

import contextlib
import io
import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cl1_body_terminal as mech


class MechanicalOntologyTests(unittest.TestCase):
    def test_structured_graph_has_valid_tree_and_parent_edges(self):
        self.assertTrue(mech.validate_mechanical_graph())
        doc = mech.mech_ontology(70)
        self.assertEqual(doc['entity_count'], 19)
        self.assertEqual(len(doc['components']), 19)
        self.assertEqual(len(doc['relations']), 18)
        self.assertEqual(len([x for x in doc['components'] if x['parent_id'] is None]), 1)
        self.assertTrue(all(edge['source'].startswith('cl1:segment/') for edge in doc['relations']))
        self.assertTrue(doc['simulation_only'])
        self.assertFalse(doc['hardware_connected'])
        self.assertIn('@context', doc)
        self.assertEqual(len({x['id'] for x in doc['components']}), 19)
        self.assertEqual({x['class'] for x in doc['components']}, {'cl1:SkeletalRigidLink'})

    def test_mechanical_parameters_have_units_mass_conservation_and_dof(self):
        doc = mech.mech_ontology(body_mass_kg=80)
        actual = sum(x['estimated_bone_proxy_mass_kg'] for x in doc['components'])
        self.assertAlmostEqual(actual, 80 * 0.15, places=4)
        self.assertTrue(all(x['rod_axis_inertia_kg_m2'] >= 0 for x in doc['components']))
        self.assertTrue(all(x['nominal_length_m'] > 0 for x in doc['components']))
        self.assertTrue(all(x['degrees_of_freedom'] == len(x['axes_limits_deg']) for x in doc['components']))
        for x in doc['components']:
            for axis in x['axes_limits_deg']:
                self.assertLess(axis['min'], axis['max'])
        self.assertEqual(mech.mechanical_properties('pelvis')['joint_type'], 'fixed')
        self.assertEqual(mech.mechanical_properties('left_forearm')['degrees_of_freedom'], 1)
        self.assertEqual(mech.mechanical_properties('right_femur')['degrees_of_freedom'], 3)

    def test_mechanical_response_respects_joint_limits_and_virtual_torque(self):
        r = mech.evaluate_joint('left_forearm', 65, 15, 70)
        self.assertEqual(r['axis'], 'elbow_flexion')
        self.assertTrue(r['within_limits'])
        expected = -(5*math.radians(65) + .25*math.radians(15))
        self.assertAlmostEqual(r['virtual_restoring_torque_nm'], expected, places=5)
        self.assertFalse(r['hardware_command_sent'])
        over = mech.evaluate_joint('left_forearm', -20)
        self.assertFalse(over['within_limits'])
        self.assertIsNone(over['virtual_restoring_torque_nm'])
        with self.assertRaises(ValueError):
            mech.evaluate_joint('cranium', 10)

    def test_invalid_identifiers_or_unphysical_inputs_are_rejected(self):
        for bad in (0, 301, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                mech.mech_ontology(bad)
        with self.assertRaises(ValueError):
            mech.mechanical_properties('not_a_part')
        for a in (float('nan'), float('inf'), 500):
            with self.assertRaises(ValueError):
                mech.evaluate_joint('left_forearm', a)
        with self.assertRaises(ValueError):
            mech.evaluate_joint('left_forearm', 90, 900)

    def test_json_export_requires_no_network_or_geometry_generation(self):
        out = io.StringIO()
        with patch.object(mech, 'geometry', side_effect=AssertionError('mesh generator called')):
            with patch('urllib.request.urlopen', side_effect=AssertionError('network call')):
                with contextlib.redirect_stdout(out):
                    self.assertEqual(mech.run(['--ontology-json', '--body-mass', '75']), 0)
        j = json.loads(out.getvalue())
        self.assertEqual(j['reference_body_mass_kg'], 75.0)
        self.assertTrue(j['simulation_only'])
        self.assertEqual(j['entity_count'], 19)

    def test_cli_inspection_and_joint_simulation(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(mech.run(['--inspect', 'right_lower_leg', '--joint-angle', '40']), 0)
        p = json.loads(out.getvalue())
        self.assertEqual(p['joint_type'], 'hinge')
        self.assertTrue(p['joint_evaluation']['within_limits'])
        self.assertEqual(p['joint_evaluation']['hardware_command_sent'], False)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                mech.run(['--joint-angle', '30'])
            with self.assertRaises(SystemExit):
                mech.run(['--joint-speed', '5'])

    def test_3d_locators_and_selected_inspector_use_binary_skeleton(self):
        c = mech.BodyCanvas(mech.geometry('light'), width=100, height=45)
        self.assertEqual(c.mode, 'SKELETON')
        self.assertEqual(c.tint, 'BONE')
        self.assertEqual(c.ontology_selection, 0)
        out = c.dashboard(color=False)
        self.assertIn('ONTOLOGY 01/19', out)
        self.assertIn('MECH SIM  MASS', out)
        self.assertIn('BONE', out)
        self.assertIn('CL1 NEURAL/BIOCHIP LAYER IS SIMULATED', out)
        self.assertEqual(set(c.render(color=False)) - set(' 01\n'), set())
        c.ontology_selection = 9
        self.assertIn('LEFT FOREARM', c.dashboard(color=False))
        on = c.render(color=False)
        c.ontology_enabled = False
        self.assertIn('ONTOLOGY HIDDEN', c.dashboard(color=False))
        self.assertNotEqual(on, c.render(color=False))

    def test_noninteractive_once_has_no_terminal_escapes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = mech.run(['--once', '--no-color', '--width', '100', '--height', '40'])
        self.assertEqual(rc, 0)
        self.assertEqual(len(out.getvalue().splitlines()), 48)
        self.assertNotIn('\x1b', out.getvalue())
        self.assertIn('SKELETON | 01 | BONE', out.getvalue())


if __name__ == '__main__':
    unittest.main()