# JCSA-20260826-01 — QTFY Defensive Profile

Source: https://www.ic3.gov/CSA/2026/260826.pdf

This profile adapts the FBI/NSA/CNMF **TLP:CLEAR** advisory into the GPT-DOUG-LLM / VA3LM defensive intelligence architecture. It does not confer government status or authorization and it does not implement offensive action against third-party systems.

## What the intelligence brain learns

- QTFY targets U.S. and foreign organizations, including critical infrastructure.
- The advisory prioritizes software/firmware updates, protection of operational information exposed through internet-facing applications, zero-trust isolation of critical systems from edge devices, and IOC hunting.
- Mapped MITRE ATT&CK techniques: `T1595.002`, `T1190`, `T1505.003`, `T1583.003`, and `T1587`.
- Incident response should identify and isolate compromised hosts, threat hunt and collect evidence, report compromises to appropriate agencies, evict the threat actor, and harden the environment.
- IOC matches are **investigation leads**, not automatic blocking authority. The advisory recommends investigating or vetting listed IP indicators before actions such as blocking.
- Security controls should be repeatedly exercised and measured against the mapped ATT&CK behaviors.

## VA3LM mapping

| Advisory need | VA3LM lane | Evidence |
| --- | --- | --- |
| Patch and lifecycle review | `agent-inventory` | patch-and-lifecycle-evidence |
| Secret exposure review | `agent-identity` | secret-exposure-review |
| Zero-trust segmentation | `agent-segmentation` | segmentation-policy-evidence |
| IOC + ATT&CK hunting | `agent-detection` | hunt-query-and-result-evidence |
| Isolation and access revocation | `agent-containment` | containment-evidence |
| Hardened restoration | `agent-recovery` | recovery-validation-evidence |
| ATT&CK control testing | `agent-verify` | control-performance-report |

## IOC sources

The advisory publishes machine-readable IOC feeds:

- https://www.ic3.gov/CSA/2026/QTFY_IOC_Files.csv
- https://www.ic3.gov/CSA/2026/QTFY_IOC_Infrastructure.csv

Production ingestion should preserve source, retrieval time, TLP marking, first/last-seen metadata, confidence, and review state. Any external enforcement action should continue through the repository's intelligence-compliance review gates.

## Completion standard

A QTFY defensive mission is not complete until hunting, exposed-edge review, segmentation verification, containment/recovery where needed, ATT&CK control tests, and evidence capture are all recorded.
