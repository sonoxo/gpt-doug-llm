import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIRING = ROOT / "safety-shield/agents/knowledge/gpt-doug-max-patent-wiring-v1.json"
DOUG_MAX = ROOT / "scripts/doug-max"
ZYRA = ROOT / "scripts/zyrapalantir"
MSS = ROOT / "scripts/zyra_mss.py"
BRIDGE = ROOT / "scripts/gpt_doug_max_patent_bridge.py"
READER = ROOT / "scripts/zyra-mss-uspto-reader"


def test_patent_fabric_has_all_required_components_and_controls():
    data = json.loads(WIRING.read_text(encoding="utf-8"))
    required = {
        "GPT_DOUG",
        "GPT_DOUG_MAX",
        "ZYRAPALANTIR",
        "ZYRA_MSS",
        "USPTO_PATENT_INTEL",
        "USPTO_CORPUS_READER",
        "GLASS_ONION",
        "PALANTIR_MAVEN",
        "GPT_REDPANDA",
        "HUMAN_REVIEW",
    }
    assert required.issubset(data["components"])
    controls = data["required_controls"]
    assert controls["automatic_external_action"] is False
    assert controls["human_review_for_claim_level_analysis"] is True
    assert controls["provenance_required"] is True
    assert controls["sha256_for_local_pdf_corpus"] is True


def test_gpt_doug_max_and_zyrapalantir_route_to_patent_bridge():
    doug = DOUG_MAX.read_text(encoding="utf-8")
    zyra = ZYRA.read_text(encoding="utf-8")
    assert "patent-wire" in doug
    assert "gpt_doug_max_patent_bridge.py" in doug
    assert "patent-corpus" in doug
    assert "patent-search" in doug
    assert "patent-wire" in zyra
    assert "gpt_doug_max_patent_bridge.py" in zyra


def test_mss_and_exhaustive_reader_are_wired():
    mss = MSS.read_text(encoding="utf-8")
    bridge = BRIDGE.read_text(encoding="utf-8")
    reader = READER.read_text(encoding="utf-8")
    assert "patent-wiring" in mss
    assert "GPT_DOUG_MAX" in mss
    assert "USPTO_CORPUS_READER" in mss
    assert "corpus.sqlite3" in bridge
    assert "documents_fts" in bridge
    assert "resume" in reader
