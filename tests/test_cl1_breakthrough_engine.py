from research_lab import cl1_breakthrough_engine as be


def test_exhaustive_count_all_domains():
    rows = be.enumerate_hypotheses()
    assert len(rows) == len(be.DOMAINS) * len(be.MODALITIES) * len(be.QUESTIONS) * len(be.ENDPOINTS) * len(be.VALIDATION)


def test_oncology_prioritizes_pdo_or_gmro():
    out = be.breakthroughs("oncology", top=10)
    assert out["enumerated"] > 0
    assert any(row["modality"] in {"patient_derived_tumor_organoid_response", "molecular_profile_gmro"} for row in out["top"])


def test_neurocomputing_prioritizes_direct_electrophysiology():
    out = be.breakthroughs("neurocomputing", top=10)
    assert any(row["modality"] in {"cl1_simulator_electrophysiology", "cl1_bnn_electrophysiology_reference"} for row in out["top"])


def test_mitochondrial_inference_from_cl1_is_penalized():
    rows = be.enumerate_hypotheses("neurocomputing")
    unsafe = [
        row for row in rows
        if row["modality"].startswith("cl1_")
        and row["endpoint"] == "mitochondrial_state"
        and row["question"] == "link_electrical_and_metabolic_state"
    ]
    assert unsafe
    assert max(row["score"] for row in unsafe) < 5
