# GPT-Doug-LLM: 99,999,999 Logical Agents x REA

This creates a compressed, deterministic **logical-agent address space**, not 99,999,999 physical processes, LLM instances, model-weight copies, or deployed bots. The default reference is public `openai/gpt-oss-20b`, but its weights are not required to create the virtual plan. There is **no network access**, and REA is not invoked unless explicitly opted in.

## Correct the Mac `ModuleNotFoundError`

The user was running from `~/Downloads` instead of the GPT-Doug source checkout. Create an isolated local checkout (does not overwrite another project):

```sh
git clone --depth 1 --branch feat/openai-open-weight-rea-mirror https://github.com/sonoxo/gpt-doug-llm.git "$HOME/Downloads/gpt-doug-rea-swarm"
bash "$HOME/Downloads/gpt-doug-rea-swarm/scripts/doug-rea-swarm" --count 99999999 --slots 8 --sample 12 --output "$HOME/Downloads/gpt-doug-virtual-99m.json"
```

If the checkout already exists, update it separately instead of cloning over it. Running `bash /path/to/repo/scripts/doug-rea-swarm` from **any directory** switches to the source root before importing the Python package.

## Meaning of the result

- `indexed_virtual_agents`: 99,999,999 deterministically addressable IDs; no object list is allocated.
- `concurrent_slot_limit`: 8 default logical partitions; no workers or threads are started.
- `sample`: bounded preview of virtual agent IDs, roles, and slot assignments.
- `active_processes_started`, `weights_copied`, `agents_executing_inference`: always 0.
- `rea_inspection_status`: `not-run` until verified local weights are explicitly inspected.
- `--output`: optional JSON file, created exclusively (no overwrites).

REA is a static artifact-analysis tool, not a means to recover proprietary OpenAI model weights, replicate an API service, access satellites, or run millions of independent models.

## Optional: use actual REA analysis evidence

After separately downloading an eligible, licensed model with the adjacent mirror tool **and** installing REA from https://github.com/morluto/rea on the Mac:

```sh
bash scripts/doug-rea-swarm --count 99999999 --slots 8 --inspect-rea
```

`--inspect-rea` reuses the model mirror's local REA evidence workflow and fails closed if no verified downloaded safetensors/GGUF artifact is available. There is no network retrieval by the virtual-fleet planner. For model download and license instructions, read `integrations/openai_model_mirror/README.md`.

Validation:

```sh
python3 -m unittest discover -s tests -p 'test_openai_model_swarm.py' -v
```

The simulator is useful for architecture and indexing tests only; running real inference across workers requires explicit model installation, compatible hardware, a scheduler, and safety/performance validation. No remote deployment or self-propagation is provided.
