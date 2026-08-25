from workers.engineering_fleet import plan_engineering_mission, select_roles


def _role_ids(prompt: str) -> list[str]:
    return [role.id for role in select_roles(prompt)]


def test_data_pipeline_mission_selects_data_fleet():
    roles = _role_ids("Build a streaming data pipeline with schema validation")
    assert roles == [
        "intake",
        "pipeline",
        "quality",
        "ontology",
        "security",
        "release",
        "observer",
    ]


def test_application_mission_selects_application_fleet():
    roles = _role_ids("Build a React application over ontology objects and actions")
    assert roles == [
        "intake",
        "ontology",
        "application",
        "security",
        "release",
        "observer",
    ]


def test_production_release_requires_approval():
    plan = plan_engineering_mission("Deploy the application to production")
    assert plan["approval_required"] is True
    assert "APPROVE" in plan["decision_loop"]
    assert "execution evidence recorded" in plan["completion_gates"]


def test_read_only_design_is_policy_dependent():
    plan = plan_engineering_mission("Design an ontology schema for a demo")
    assert plan["approval_required"] is False
