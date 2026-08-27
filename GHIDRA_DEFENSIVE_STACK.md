# GPT-DOUG-LLM × Ghidra Defensive Analysis Stack

Source repository: https://github.com/sonoxo/ghidraGPTDougLLMXYRA

## Mission

Stack Ghidra's software reverse-engineering capability into the GPT-DOUG-LLM / VA3LM defensive intelligence system without turning reverse engineering into autonomous offensive execution.

Ghidra remains the analysis engine for binaries the operator is authorized to inspect. GPT-DOUG-LLM ingests normalized analysis metadata, binds it into the ontology, correlates findings with assets, ATT&CK techniques, incidents, and evidence, and routes analyst-reviewed defensive work.

## Flow

`AUTHORIZED BINARY → GHIDRA STATIC ANALYSIS → NORMALIZED REPORT → ONTOLOGY → ANALYST REVIEW → INCIDENT / EVIDENCE / RECOVERY`

The bridge does not require raw binary bytes to leave the owner's environment.

## Ontology

The stack adds these object types:

- `BinaryArtifact`
- `ReverseEngineeringSession`
- `FunctionObservation`
- `ReverseEngineeringFinding`
- `VulnerabilityHypothesis`

They connect to the existing defensive ontology through:

- `AttackTechnique`
- `Asset`
- `Incident`
- `Evidence`

This lets a reverse-engineering observation become operationally useful without losing provenance or review state.

## Guardrails

The integration is intentionally defensive and analysis-only:

- authorized binaries only
- no exploit generation
- no payload generation
- no credential theft
- no persistence deployment
- no destructive action
- no third-party execution
- no autonomous offensive action
- human approval for incident actions
- raw binaries remain with their owner by default

## Implementation

- `agents/ghidra_defensive_analysis.py` — normalization and bounded integration contract
- `foundry/ontology/ghidra-defense-ontology.json` — ontology extension
- `tests/test_ghidra_defensive_analysis.py` — focused guardrail and normalization tests
- `.github/workflows/ghidra-defensive-stack.yml` — focused CI

## Why Ghidra

The connected Ghidra repository describes the framework as an NSA-created software reverse-engineering platform supporting disassembly, decompilation, graphing, scripting, interactive and automated analysis, and malicious-code research. The source repository carries the Apache License 2.0.

## Federal defensive use

In an authorized environment, this stack can support malware triage, firmware review, suspicious binary analysis, software supply-chain investigation, vulnerability hypothesis generation, and incident evidence development. Findings remain hypotheses or observations until an analyst validates them.
