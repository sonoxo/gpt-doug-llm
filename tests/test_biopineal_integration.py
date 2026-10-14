from gpt_doug_mlm.biopineal import BioPineal, REFERENCES
from gpt_doug_mlm.biochip_research import ResearchRouter


def test_cited_metadata_and_attribution():
    core = BioPineal()
    records = core.search("mitochondria")
    assert len(records) == 1
    assert records[0]["patent_id"] == "US12760292B2"
    assert "Broad Institute" in records[0]["assignee"]
    assert "independent verification pending" in records[0]["status"]


def test_llm_mlm_biopineal_bridge_is_review_only():
    core = BioPineal()
    router = ResearchRouter({"local_stub": lambda q: "unverified summary"})
    result = core.review("biosensor", router)
    assert result["approval"] == "human_review_required"
    assert result["model_candidates"][0]["confidence"] == 0.0
    assert result["references"][0]["source"].startswith("user-provided")
