from agents.va3lm_geovision import VA3LM_COMMAND, VA3LM_PROFILE, build_va3lm_plan


def test_va3lm_batch_plan_is_bounded_and_geospatial():
    plan = build_va3lm_plan(camera_source="authorized-test-media", live=False)
    assert plan["command"] == VA3LM_COMMAND
    assert plan["profile"] == VA3LM_PROFILE
    assert plan["mode"] == "NON_IDENTIFYING_OBJECT_SCENE_RECOGNITION"
    assert "WGS84_GEOSPATIAL_ENRICHMENT" in plan["flow"]
    assert plan["deployment"] == "BATCH_MODEL_INFERENCE"
    assert len(plan["lanes"]) == 6


def test_va3lm_live_plan_uses_model_deployment():
    plan = build_va3lm_plan(live=True)
    assert plan["deployment"] == "LIVE_MODEL_DEPLOYMENT"
    assert "LIVE_MODEL_DEPLOYMENT" in plan["flow"]


def test_identity_surveillance_modes_are_not_part_of_capability():
    plan = build_va3lm_plan()
    prohibited = " ".join(plan["prohibitedIdentityModes"]).lower()
    assert "face recognition" in prohibited
    assert "persistent individual tracking" in prohibited
