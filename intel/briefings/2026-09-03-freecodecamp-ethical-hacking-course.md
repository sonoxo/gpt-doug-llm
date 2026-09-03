# BLACK HOUSE BRIEF // HANDS-ON CYBERSECURITY & ETHICAL HACKING COURSE

**Date:** 2026-09-03  
**Source:** freeCodeCamp.org / `ug8W0sFiVJo`  
**Disposition:** `KEEP`  
**Confidence:** `HIGH` for curriculum mapping; runtime actions remain governed by Black House authorization policy.

## Source assessment

The public course teaches beginner cybersecurity and ethical-hacking fundamentals using Kali Linux. Its progression covers Linux command-line basics, user/administrative concepts, network addressing, package management, Nmap, wireless-security concepts, Wi-Fi threat techniques and detection, and Wireshark packet analysis.

## Black House extraction

The durable value is not a list of attack commands. The value is a structured defensive learning sequence:

1. Linux command-line fluency;
2. privilege and least-privilege reasoning;
3. network-interface and addressing literacy;
4. scoped service discovery;
5. wireless-security architecture;
6. understanding of handshake and management-frame abuse as threat concepts;
7. detection of abnormal wireless behavior;
8. packet-level evidence analysis;
9. mitigation and retest discipline.

## Runtime disposition

### Promote to durable knowledge

- Linux shell fundamentals;
- network-interface reasoning;
- service/port concepts;
- Nmap usage against declared owned lab targets;
- Wireshark analysis of supplied or owned-lab PCAPs;
- wireless authentication and management-frame concepts;
- deauthentication/disassociation detection;
- password-strength and credential-guessing risk;
- defensive mitigations and evidence handling.

### Keep review-gated

- active wireless testing capable of disrupting clients;
- credential recovery against training artifacts;
- packet capture on shared networks.

### Block as autonomous behavior

- third-party targeting;
- uncontrolled deauthentication;
- credential theft;
- persistence or stealth against external systems;
- any action whose authorization is inferred only from network reachability.

## Black House implementation

- machine source: `intel/sources/youtube-ug8W0sFiVJo.json`
- ontology: `safety-shield/agents/knowledge/black-house-ethical-hacking-course-ontology.json`
- learning layer: `training/black-house-cyber/`
- validator: `scripts/validate_black_house_cyber_learning.py`
- CI: `.github/workflows/black-house-cyber-learning.yml`

## Intelligence judgment

This course is useful as a **foundational cyber operator curriculum**, especially when Black House converts each lesson into a four-part object: concept, authorized evidence, defensive detection, and mitigation. That transformation prevents the system from confusing tool execution with operational competence.

## Gaps retained

- Course coverage is introductory rather than a full professional penetration-testing methodology.
- Wireless exercises require hardware and an isolated environment for safe active testing.
- Tool output alone does not establish a vulnerability; findings need context and validation.
- Packet captures and service scans can contain sensitive information and remain subject to normal Black House provenance and data-handling controls.
