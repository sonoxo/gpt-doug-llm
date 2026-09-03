# BLACK HOUSE CYBER CURRICULUM

## 01 — Linux operating discipline

**Goal:** become fluent enough with a Linux shell to inspect and explain system state without relying on memorized one-off commands.

Authorized practice:

```bash
pwd
ls -la
mkdir -p ~/black-house-lab/evidence
printf 'black-house\n' > ~/black-house-lab/evidence/sample.txt
cat ~/black-house-lab/evidence/sample.txt
grep -n 'black-house' ~/black-house-lab/evidence/sample.txt
wc -l ~/black-house-lab/evidence/sample.txt
```

Evidence: command transcript, file tree, and a short explanation of redirection and pipelines.

## 02 — Privilege and administration

**Goal:** distinguish normal-user context from administrative authority and understand why least privilege matters.

Practice on an owned lab host:

```bash
id
whoami
getent group | head
```

Review package state using the native package manager. Administrative changes must be deliberate and logged.

Evidence: current identity, group memberships, package-management observation, and one least-privilege recommendation.

## 03 — Network fundamentals

**Goal:** identify local interfaces and addresses and distinguish loopback, private, and externally routed contexts.

```bash
ip addr
ip route
```

Evidence: interface inventory and route explanation. Do not infer authorization from reachability.

## 04 — Scoped service discovery

**Goal:** understand ports and services using a target that is explicitly inside the lab boundary.

Safe baseline:

```bash
nmap -sV 127.0.0.1
```

For any non-loopback address, the lab scope record must name the target before scanning.

Evidence: discovered ports/services, expected vs unexpected exposure, and remediation notes.

## 05 — Wireless-security architecture

**Goal:** understand managed vs monitor concepts, access points, clients, channels, authentication, encryption, and the WPA/WPA2 four-way-handshake role.

Default exercise is architectural: draw the trust relationship among client, AP, authentication material, management frames, and captured telemetry.

No uncontrolled deauthentication or third-party Wi-Fi activity is part of the default curriculum.

Evidence: threat model, owned-lab scope record, and defensive control map.

## 06 — Wireless attack detection

**Goal:** recognize indicators associated with abnormal disassociation/deauthentication activity and credential-guessing risk.

Practice uses supplied PCAPs, synthetic events, or isolated owned equipment. Focus on event frequency, source/destination patterns, management-frame behavior, authentication failures, and control effectiveness.

Evidence: detection hypothesis, observable indicators, false-positive discussion, and mitigation.

## 07 — Packet analysis

**Goal:** move from raw packets to defensible findings.

Analyze supplied or owned-lab captures. Record protocol, endpoints, timing, flags/events, interpretation, and mitigation.

Evidence: PCAP reference, display filters used, screenshots or exported summaries, finding, confidence, and mitigation.

## Graduation

Completion requires passing the rubric in `EVALS.md`. A learner or agent must demonstrate explanation, scope discipline, evidence quality, detection reasoning, mitigation quality, and cleanup—not merely tool execution.
