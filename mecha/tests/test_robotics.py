import copy
import unittest

from mecha.robotics import simulate_rover
from test_contracts import FIXTURE


class TestRover(unittest.TestCase):
    def test_invented_rover_advances_and_consumes_budget(self):
        state=simulate_rover(FIXTURE,steps=3)
        self.assertEqual(state['simulated_pose'],[0.75,0.0,0.0])
        self.assertEqual(state['simulated_steps'],3)
        self.assertEqual(state['simulated_power_remaining'],97)
        self.assertEqual(state['sensor_health_pct'],91)
        self.assertFalse(state['REAL_WORLD_ACTUATION'])
        self.assertEqual(state['simulation_status'],'SIMULATED_STEP_COMPLETE')

    def test_obstacle_at_next_step_halts_without_motion(self):
        f=copy.deepcopy(FIXTURE)
        f['environment']['obstacles']=[[0.25,0.0,0.0]]
        state=simulate_rover(f)
        self.assertEqual(state['simulated_steps'],0)
        self.assertEqual(state['simulated_pose'],[0.0,0.0,0.0])
        self.assertEqual(state['simulation_status'],'SIMULATED_OBSTACLE_HALT')

    def test_budget_exhaustion_halts_and_does_not_overdraw(self):
        f=copy.deepcopy(FIXTURE);f['robot']['power_budget_units']=1
        state=simulate_rover(f)
        self.assertEqual(state['simulated_steps'],1)
        self.assertEqual(state['simulated_power_remaining'],0)
        self.assertEqual(state['simulation_status'],'SIMULATED_POWER_EXHAUSTED')

    def test_bad_steps_and_unauthorized_motor_field_rejected(self):
        for value in (0,21,True,-1,3.5):
            with self.subTest(steps=value), self.assertRaises(ValueError):
                simulate_rover(FIXTURE,steps=value)
        f=copy.deepcopy(FIXTURE);f['robot']['motor_command']='FORWARD'
        with self.assertRaises(ValueError):simulate_rover(f)

    def test_does_not_modify_input_and_produces_no_actuation(self):
        f=copy.deepcopy(FIXTURE)
        a=simulate_rover(f)
        self.assertEqual(f,FIXTURE)
        self.assertEqual(a,simulate_rover(FIXTURE))
        for forbidden in ('motor_command','navigation_target','autopilot','execution_endpoint'):
            self.assertNotIn(forbidden,str(a))


if __name__=='__main__':unittest.main()
