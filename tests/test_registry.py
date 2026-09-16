from north_star_federation import get_member, load_registry, summary, validate_registry


def test_registry_is_valid():
    data = load_registry()
    assert validate_registry(data) == []


def test_gpt_doug_max_is_collective_supervisor():
    data = load_registry()
    member = get_member(data, "gpt-doug-max")
    assert member is not None
    assert member["role"] == "collective-supervisor"


def test_zyra_is_execution_governor():
    data = load_registry()
    member = get_member(data, "zyra")
    assert member is not None
    assert member["role"] == "execution-governor"


def test_summary_counts_members():
    data = load_registry()
    info = summary(data)
    assert info["member_count"] >= 7
    assert info["implemented_count"] >= 7


def test_decision_contract_preserves_dissent():
    data = load_registry()
    assert data["decision_contract"]["preserve_dissent"] is True
    assert data["decision_contract"]["policy_gate_required"] is True
