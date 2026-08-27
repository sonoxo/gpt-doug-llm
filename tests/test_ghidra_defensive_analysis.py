from agents.ghidra_defensive_analysis import build_ghidra_stack_config, normalize_ghidra_report


def test_stack_config_is_analysis_only_and_human_reviewed():
    config = build_ghidra_stack_config()
    assert config["engine"] == "Ghidra"
    assert config["operation"] == "STATIC_ANALYSIS_AND_EVIDENCE_INGEST"
    assert config["networkExecutionRequired"] is False
    assert config["humanReviewRequired"] is True
    assert config["guardrails"]["analysisOnly"] is True
    assert config["guardrails"]["exploitGeneration"] is False
    assert config["guardrails"]["payloadGeneration"] is False
    assert config["guardrails"]["thirdPartyExecution"] is False


def test_report_normalizes_into_ontology_ready_evidence():
    report = {
        "sha256": "a" * 64,
        "name": "authorized-sample.bin",
        "format": "PE",
        "architecture": "x86-64",
        "sessionId": "session-1",
        "analysisVersion": "test",
        "functions": [
            {
                "name": "parse_message",
                "address": "0x401000",
                "callingConvention": "__cdecl",
                "decompiled": True,
            }
        ],
        "findings": [
            {
                "findingType": "MEMORY_SAFETY_REVIEW",
                "summary": "Potential bounds-checking issue requiring analyst validation.",
                "confidence": 0.75,
                "functionName": "parse_message",
                "address": "0x401020",
                "techniqueId": "T1190",
            }
        ],
    }
    result = normalize_ghidra_report(report)
    assert result["artifact"]["artifactId"] == f"binary:{'a' * 64}"
    assert result["functions"][0]["decompiled"] is True
    assert result["findings"][0]["reviewState"] == "UNDER_REVIEW"
    assert result["ontologyBindings"]["finding"] == "ReverseEngineeringFinding"
    assert result["guardrails"]["exploitGeneration"] is False


def test_invalid_hash_is_rejected():
    try:
        normalize_ghidra_report({"sha256": "not-a-hash", "functions": [], "findings": []})
    except ValueError as exc:
        assert "SHA-256" in str(exc)
    else:
        raise AssertionError("invalid SHA-256 must be rejected")
