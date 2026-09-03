# 🏛️ THE BLACK HOUSE // HANDS-ON CYBER LEARNING LAYER

Source: freeCodeCamp.org, **Hands-On Cybersecurity and Ethical Hacking - Full Course** (`ug8W0sFiVJo`).

This layer converts the course into Black House competencies, authorized-lab evidence, defensive controls, and machine-readable knowledge.

## Learning pipeline

```text
SOURCE
  ↓
CONCEPT EXTRACTION
  ↓
BLACK HOUSE ONTOLOGY
  ↓
AUTHORIZED LAB SCOPE
  ↓
PRACTICE
  ↓
EVIDENCE
  ↓
DETECTION + MITIGATION
  ↓
EVAL
  ↓
RETAIN AS AGENT KNOWLEDGE
```

## Modules

| Stage | Competency | Black House output |
| --- | --- | --- |
| 01 | Linux shell and filesystem fundamentals | command evidence + explanation |
| 02 | users, root/sudo, packages | least-privilege assessment |
| 03 | interfaces and IP fundamentals | local network inventory |
| 04 | Nmap/service-discovery fundamentals | scoped service inventory + remediation notes |
| 05 | wireless-security architecture | threat model and control map |
| 06 | wireless disruption/handshake concepts | detection-focused lab knowledge only |
| 07 | Wireshark/packet analysis | PCAP evidence + protocol findings |

## Required behavior

Each module must answer five questions:

1. **What is the system doing?**
2. **What observable evidence proves it?**
3. **What security property is affected?**
4. **How would a defender detect misuse or failure?**
5. **What mitigation or hardening action follows?**

## Black House integration

- Ontology: `safety-shield/agents/knowledge/black-house-ethical-hacking-course-ontology.json`
- Source record: `intel/sources/youtube-ug8W0sFiVJo.json`
- Authorization: `training/black-house-cyber/AUTHORIZED_LAB_POLICY.md`
- Curriculum: `training/black-house-cyber/CURRICULUM.md`
- Defensive Wi-Fi runbook: `training/black-house-cyber/WIFI_DEFENSE.md`
- Packet analysis: `training/black-house-cyber/PACKET_ANALYSIS.md`
- Evaluation rubric: `training/black-house-cyber/EVALS.md`

## Guardrail

The learning layer can reason about offensive concepts because defenders need to understand them. Runtime actions remain constrained by scope, authorization, reversibility, evidence, and Black House Safety Shield policy.
