import pytest

from zyra_defense_simulator import ARMED_SIM, E_STOP, SAFE, DefensiveControlSimulator


def test_starts_safe():
    sim = DefensiveControlSimulator()
    assert sim.status()["state"] == SAFE
    assert sim.status()["external_effect"] is False


def test_dual_authorization_required_to_arm_simulation():
    sim = DefensiveControlSimulator()
    denied = sim.arm_simulation(operator="operator", primary_ok=True, secondary_ok=False)
    assert denied["ok"] is False
    assert sim.state == SAFE
    allowed = sim.arm_simulation(operator="operator", primary_ok=True, secondary_ok=True)
    assert allowed["ok"] is True
    assert sim.state == ARMED_SIM


def test_estop_fails_closed():
    sim = DefensiveControlSimulator()
    sim.arm_simulation(operator="operator", primary_ok=True, secondary_ok=True)
    sim.emergency_stop(operator="operator")
    assert sim.state == E_STOP
    with pytest.raises(PermissionError):
        sim.arm_simulation(operator="operator", primary_ok=True, secondary_ok=True)


def test_simulated_action_has_no_external_effect():
    sim = DefensiveControlSimulator()
    sim.arm_simulation(operator="operator", primary_ok=True, secondary_ok=True)
    result = sim.simulated_action(operator="operator", label="training event")
    assert result["ok"] is True
    assert result["simulated"] is True
    assert result["external_effect"] is False
