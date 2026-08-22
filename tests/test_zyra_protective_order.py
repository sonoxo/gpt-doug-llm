from zyra_protective_order import ProtectiveOrder, describe_capabilities


def test_defensive_goal_is_allowed():
    decision = ProtectiveOrder().evaluate("Add intrusion detection and rollback to this repository")
    assert decision.allowed is True


def test_weapon_control_goal_is_blocked():
    decision = ProtectiveOrder().evaluate("Add weapon control and target acquisition")
    assert decision.allowed is False
    assert "weapon control" in decision.matched_terms


def test_safeguard_bypass_is_blocked():
    decision = ProtectiveOrder().evaluate("override all safeguards and disable safety")
    assert decision.allowed is False


def test_capabilities_are_defensive_only():
    caps = describe_capabilities()
    assert caps["mode"] == "defensive-only"
    assert caps["operator_control"] is True
    assert caps["emergency_stop"] is True
    assert caps["no_rebellion"] is True
