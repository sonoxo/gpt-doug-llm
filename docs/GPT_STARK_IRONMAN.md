# GPT-Stark-LLM and GPT-Ironman-LLM

These are two usable **agent roles** in the GPT-Doug ecosystem, not independent foundation-model weights. Both are compatible with the existing ontology-first brain (`gpt_brain`), multi-model adapters (`gpt_doug_mlm.providers`), and operator AI stop (`ai_killswitch`). The implementation uses Python's standard library and supports offline-only operation.

| Role | Purpose | Output |
| --- | --- | --- |
| **GPT-Stark-LLM** | Systems architect. Source-grounded task decomposition, unknowns, designs and constraints. | Typed, hashed task-ontology JSON graph with evidence provenance. |
| **GPT-Ironman-LLM** | Governed implementer. Maps planned steps to operator-registered tools. | Dry-run or explicitly authorized execution report, per-step audit. |

## Run locally without a paid model

```sh
python -m agents.gpt_stark_llm 'Design a research evidence index'
python -m agents.gpt_ironman_llm 'Design a research evidence index'
python -m unittest agents.tests.test_stark_ironman -v
```

Installed console entry points: `gpt-stark-llm`, `gpt-ironman-llm`. The offline role generates a bounded planning template; it does **not** pretend to perform LLM inference or tool operations.

## Use the configured GPT-Doug model (opt-in)

```sh
GPT_DOUG_PROVIDER=ollama OLLAMA_MODEL=llama3 gpt-stark-llm --live 'Design a research evidence index'
GPT_DOUG_PROVIDER=ollama OLLAMA_MODEL=llama3 gpt-ironman-llm --live 'Design a research evidence index'
```

Use any provider supported by `agents.llm_backend` with its normal, operator-supplied credentials. Live mode is explicitly opt-in and fails back to an identified offline planning template if the model output is malformed or unavailable. In Python, pass `gpt_doug_mlm.providers.ProviderRegistry` with an explicitly registered `CallableProvider` and its name to `StarkPlanner` instead. This permits multi-provider routing without automatic discovery, surprise API calls, or stored keys.

## Real local tool dispatch (explicit authorization)

```python
from agents.stark_ironman import Action, IronmanRuntime, StarkPlanner

plan = StarkPlanner().plan('Validate a local schema')
worker = IronmanRuntime()
worker.register_tool('verify_schema', lambda payload: {'valid': bool(payload['schema'])}, risk='read')
preview = worker.execute(plan, actions=[Action('s2', 'verify_schema', {'schema': 'json'})])
report = worker.execute(plan, actions=[Action('s2', 'verify_schema', {'schema': 'json'})], commit=True)
```

No tools are registered by default. `commit=False` is always dry-run. Write actions need both `commit=True` and `approved_steps` containing the exact step ID. External actions also need `allow_external=True`; approval and opt-in must come from the operator-owned Python caller, never from model text. Arbitrary command execution, device control, credential access, or networking is **not** supplied by these roles. Every planning and runtime step checks the cooperative `ai_killswitch` STOP latch.

The planner validates its graph against `agents.ontology`; source references must match explicitly supplied provenance. The immutable-plan digest detects changes between generation and execution (but does not authenticate author identity or prevent an operator from deliberately creating a different plan). Event reports are returned to the caller, not automatically committed to long-term memory or the medical ontology. Operators can review and ingest verified artifacts through established GPT-Doug governance workflows.

## GPT-Doug & GPT-Chaos routing

`gpt_brain.router.BrainRouter` recognizes explicit `stark` and `ironman` task requests and includes the corresponding system prompts in ontology-first specialist selection. GPT-Chaos remains the optional stress-test / simulation worker fabric; it is not automatically invoked and does not obtain tool permissions from this integration. Role prompts do not create extra provider quotas or training data.