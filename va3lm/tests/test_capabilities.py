from va3lm.capabilities import capability_manifest, capability_status


def test_pack_capability_manifest_is_explicitly_alpha_reference():
    manifest = capability_manifest()
    assert manifest["name"] == "BIG VIRGINIA // VA3LM Capability Plane"
    assert manifest["source"] == "sonoxo/pack"
    assert manifest["sourceState"] == "ALPHA_REFERENCE"
    assert len(manifest["capabilities"]) == 10


def test_big_virginia_capability_ids_are_unique():
    ids = [item["id"] for item in capability_manifest()["capabilities"]]
    assert len(ids) == len(set(ids))
    assert {"core", "auth", "schema", "state", "codegen", "sdkgen", "app"}.issubset(ids)


def test_capability_status_counts_manifest():
    status = capability_status()
    assert status["total"] == 10
    assert status["adapted"] == 9
    assert status["blueprint"] == 1
