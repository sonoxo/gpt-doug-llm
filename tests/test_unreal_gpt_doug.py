import json
from pathlib import Path

from unreal_gpt_doug import UnrealGPTDoug

ROOT = Path(__file__).resolve().parent.parent

def test_unreal_knowledge_jsonl_is_valid_and_unique():
    path = ROOT / "workers" / "knowledge" / "unreal-engine-5-8.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) >= 30
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    for row in rows:
        assert row["id"].startswith("unreal-")
        assert row["topic"]
        assert row["attribution"]
        assert row["summary"]
        assert row["keywords"]
        assert row["source_url"].startswith("https://")
        assert row["source_status"]

def test_unreal_search_retrieves_networked_physics():
    unreal = UnrealGPTDoug(ROOT)
    rows = unreal.search("networked physics resimulation")
    assert rows
    assert rows[0]["id"] in {"unreal-networked-physics", "unreal-network-physics-component"}

def test_unreal_grounding_is_scoped():
    unreal = UnrealGPTDoug(ROOT)
    assert unreal.context_for("write a country song") == ""
    ctx = unreal.context_for("how should I architect Unreal networked physics?")
    assert "UNREAL-GPT-DOUG SOURCE-GROUNDED CONTEXT" in ctx
    assert "SOURCE=https://" in ctx

def test_mcp_guide_is_local_and_bounded():
    unreal = UnrealGPTDoug(ROOT)
    guide = unreal.mcp_guide()
    assert guide["endpoint"].startswith("http://127.0.0.1:")
    assert any("source control" in x.lower() for x in guide["boundary"])
    assert any("local" in x.lower() for x in guide["boundary"])
