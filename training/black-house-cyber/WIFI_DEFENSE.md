# BLACK HOUSE // WIRELESS DEFENSE RUNBOOK

## Purpose

Retain the course's wireless-security concepts as defensive knowledge and isolated-lab competencies.

## Threat model

Black House tracks these concepts:

- access point and client roles;
- managed vs monitor-mode concepts;
- 2.4 GHz and 5 GHz channel awareness;
- WPA/WPA2 four-way-handshake purpose;
- management-frame abuse, including deauthentication/disassociation patterns;
- password-guessing risk against weak passphrases;
- packet-capture evidence and defensive telemetry.

## Detection workflow

```text
AUTHORIZED TELEMETRY
  ↓
IDENTIFY MANAGEMENT/AUTHENTICATION EVENTS
  ↓
BASELINE NORMAL RATE + SOURCES
  ↓
FIND BURSTS / REPEATED FAILURES / SOURCE ANOMALIES
  ↓
CORRELATE WITH CLIENT DISCONNECTS
  ↓
ASSESS CONFIDENCE
  ↓
MITIGATE + RETEST
```

## Defensive indicators

Potential indicators include unusually frequent deauthentication/disassociation frames, repeated reconnect cycles, authentication failures, abrupt client churn, or activity inconsistent with the known AP/client inventory. None is conclusive alone.

## Mitigations

- use strong unique wireless passphrases;
- prefer modern WPA2/WPA3 configurations appropriate to supported hardware;
- enable protected management frames where supported and operationally appropriate;
- maintain an authorized AP inventory;
- monitor authentication and client-disconnect telemetry;
- remove obsolete or insecure wireless configurations;
- segment untrusted or guest devices;
- preserve PCAP/log evidence when investigating anomalies.

## Lab boundary

Active disruption, forced client disconnects, or credential-recovery experiments are not autonomous Black House actions. Such techniques may only be represented in a declared isolated lab with operator-owned infrastructure and explicit scope. The default Black House behavior is detection, explanation, hardening, and evidence preservation.
