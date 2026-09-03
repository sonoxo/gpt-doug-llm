# BLACK HOUSE // PACKET ANALYSIS RUNBOOK

## Objective

Turn packet captures from owned labs or supplied evidence into source-traceable findings.

## Analysis sequence

1. Record the PCAP source and authorization context.
2. Identify major protocols and endpoints.
3. Establish a time window and baseline traffic pattern.
4. Narrow to the event under investigation.
5. Preserve the display filter or query used.
6. Separate observation from interpretation.
7. Assign confidence.
8. Document mitigation and follow-up evidence.

## Useful Wireshark display-filter examples

```text
arp
dns
tcp
udp
icmp
http
tls
wlan.fc.type == 0
wlan.fc.type_subtype == 0x0c
```

The wireless management-frame filters above are intended for PCAP analysis and detection. They do not transmit frames or alter a network.

## Finding template

```text
Scope:
Evidence source:
Time range:
Filter:
Observation:
Interpretation:
Security impact:
Confidence:
Mitigation:
Retest evidence:
```

## Quality gate

A Black House packet finding must be reproducible from the preserved evidence. Assertions that cannot be traced to packets, logs, configuration, or an independently verified source remain hypotheses.
