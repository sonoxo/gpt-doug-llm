# Reef Continual-Learning Integration

GPT-DOUG-LLM integrates with [Human-Agent-Society/reef](https://github.com/Human-Agent-Society/reef) through a small dependency-free HTTP bridge in [`reef_bridge.py`](../../reef_bridge.py).

## Why this bridge exists

Reef is continual-learning infrastructure for agents. Its public lifecycle is:

1. **Serve** — handle inference and record interactions.
2. **Observe** — attach feedback to recorded interactions.
3. **Grow** — produce candidate updates from eligible records.
4. **Commit** — evaluate and publish accepted artifact versions.

GPT-DOUG-LLM supports Python 3.9+, while the current Reef package requires Python 3.10+. The bridge therefore communicates with a Reef service over its documented HTTP endpoints instead of making `reef-infra` a mandatory GPT-DOUG dependency.

## Ontology mapping

| Reef-facing object | GPT-DOUG relationship |
| --- | --- |
| `AgentInteraction` | Task/inference execution record |
| `FeedbackReport` | Evaluation of an interaction/result |
| `LearningCandidate` | Proposed model or harness change |
| `ArtifactVersion` | Accepted, versioned learning artifact |

Links are explicit and provenance-preserving:

- `FeedbackReport --evaluates--> AgentInteraction`
- `LearningCandidate --derived_from--> AgentInteraction`
- `ArtifactVersion --commits--> LearningCandidate`

See [`manifest.json`](manifest.json) for the machine-readable registration.

## Configure

```bash
export REEF_BASE_URL="http://127.0.0.1:8901"
export REEF_TOKEN="reef-local"
export REEF_SCENARIO="gpt-doug"
```

`REEF_TIMEOUT` is optional and defaults to 60 seconds.

## Use

```python
from reef_bridge import ReefBridge

reef = ReefBridge()

completion = reef.chat_completion(
    model="your-model-id",
    messages=[{"role": "user", "content": "Return exactly: ready"}],
)

reef.feedback_for_completion(
    completion,
    score=1.0,
    feedback="matched expected output",
)
```

The completion contains `receipt_id`, copied from Reef's `x-reef-agent-record-id` response header. Feedback is always attached using that receipt so the learning path remains auditable.

## Governance

This integration does **not** automatically accept or publish candidate model/harness changes. Selection and version promotion remain controlled by the configured Reef recipe/policy. GPT-DOUG keeps the receipt and provenance boundary intact rather than inventing an unverified success state.

## Upstream attribution

- Project: `Human-Agent-Society/reef`
- Repository: https://github.com/Human-Agent-Society/reef
- License: Apache License 2.0
- Verified source tree at integration design time: `bea406927d5d168d62122a005673d7e5f558af7e`

No upstream source files are copied into this integration; the adapter implements the documented service contract.
