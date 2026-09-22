# UAP-MATRIX Shared Space

UAP-MATRIX is the project-level **Unified Agent Plane** shared by GPT-Doug and
GPT-Chaos.

It provides one durable local blackboard for:

- observations;
- hypotheses;
- evidence;
- dissent;
- plans;
- actions;
- results;
- faults; and
- recovery records.

GPT-Doug and GPT-Chaos are represented as **peer agents** in this layer.
Different runtime responsibilities do not create a rank hierarchy in the
shared-space contract.

## Quorum

A decision reaches `QUORUM_REACHED` only when both GPT-Doug and GPT-Chaos
record `SUPPORT`. A `DISSENT` vote moves the decision to `CONTESTED` and
the dissent event remains on the blackboard.

## Evidence and authority

UAP-MATRIX is coordination state, not an authority escalation mechanism.

The runtime explicitly records:

```text
execution_authority = NO_EXTERNAL_AUTHORITY_GRANTED
human_authority = true
```

Publishing an `ACTION` event does not execute that action. Existing policy,
authorization, tool, and human-review gates remain authoritative.

## State layout

By default:

```text
~/.gpt-doug/universal-hive/uap-matrix/
├── state.json
├── events.jsonl
└── checkpoints/
```

When constructed by the Universal Hive, the matrix lives directly under that
hive's configured state directory.

## CLI

```bash
uap-matrix status
uap-matrix publish GPT_DOUG OBSERVATION "signal detected"
uap-matrix propose GPT_DOUG "promote verified result"
uap-matrix vote GPT_CHAOS <decision-id> SUPPORT
uap-matrix checkpoint --label known-good
```

GPT-Chaos also exposes peer-specific commands:

```bash
gpt-chaos matrix-status
gpt-chaos matrix-publish HYPOTHESIS "challenge assumption"
gpt-chaos matrix-propose "alternate plan"
gpt-chaos matrix-vote <decision-id> DISSENT --evidence "missing proof"
```

The main GPT-Doug terminal exposes:

```text
/matrix
/matrix checkpoint
/matrix publish <channel> <message>
/matrix propose <statement>
/matrix vote <decision-id> <SUPPORT|DISSENT|ABSTAIN>
```

## Canonical loop

```text
OBSERVE
  -> WRITE SHARED SPACE
  -> DOUG + CHAOS REVIEW
  -> AGREEMENT OR PRESERVED DISSENT
  -> QUORUM
  -> EXISTING POLICY / HUMAN GATES
  -> TOOL EXECUTION, IF AUTHORIZED
  -> RESULT / FAULT
  -> CHECKPOINT / RECOVERY
```
