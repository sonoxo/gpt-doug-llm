# SKULL-LLM — GPT-DOUG local neural intelligence

SKULL-LLM is a new **two-part, free/open-source** subsystem inside
`sonoxo/gpt-doug-llm`. It does **not** claim to be the world's smartest
model, to have trained frontier-scale weights, or to have completed
benchmarking that has not actually been run.

1. **Useful inference now:** a local-only Ollama-backed planner / answerer /
   critic / reviser integrated with GPT-Doug's existing `gpt_brain` ontology
   and `BrainMemory`. Retrieval is bounded; memory writes require opt-in;
   the central AI emergency stop is checked before and after every inference.
2. **Trainable neural core:** a real PyTorch decoder-only Transformer with
   causal scaled-dot-product attention, RoPE, RMSNorm, SwiGLU, tied token
   embeddings, next-token cross-entropy, and CPU / Apple MPS / CUDA training.
   The reference tokenizer is UTF-8 *bytes*, and the checkpoint starts
   from random weights. Its tiny example will **not** match a pretrained
   model's language capabilities.

## SKULL ASCII command deck

The terminal UI uses **plain 7-bit ASCII** with no curses, colors, animation,
Unicode glyphs, external terminal dependencies, or paid API calls.
Three commands are available:

```bash
skull-llm banner                    # anatomically shaded ASCII skull
skull-llm portrait --width 90       # full-height shaded anatomical art
skull-llm network                   # static architecture of neural pipeline
skull-llm dashboard                 # real local Ollama / PyTorch readiness
skull-llm dashboard --width 80      # force a fixed console width
```

`python3 -m skull_llm banner` (or `portrait`, `network`, or `dashboard`) works from a
source checkout without installing the CLI. `banner` and `network` have
no backend requirements; `dashboard` queries only the configured loopback
Ollama endpoint and the local emergency-stop flag. If Ollama is unavailable,
it shows **OFFLINE** rather than pretending to be connected. The output
strips escape/control characters from model names and provider messages.

Interactive `skull-llm ask` sessions automatically show the banner when
standard output is a TTY; JSON and redirected command output remain clean.
The topology diagram is architectural, *not* a live network traffic map.

### Photo-accurate ASCII from a user-owned image

The new default skull is **anatomy-inspired procedurally shaded art** with
orbital cavities, brow, nasal aperture, cheekbones, maxilla, teeth, and jaw.
It is a visual illustration, not a CT scan. For a much closer resemblance to
a particular skull reference, convert a locally stored image directly into
high-density grayscale ASCII using optional **Pillow**:

```bash
python3 -m pip install Pillow
skull-llm portrait --image ~/Pictures/skull-reference.png --width 100
```

The image is read on the local computer only; no network upload is required.
Use `--invert` if needed for light-on-dark terminal photographs. The image
decoder rejects oversized files, output stays ASCII-only, and the width is
bounded for terminal display. The rendering uses the source photograph's
actual contrast; unlike the procedural art, this can capture exact contours.


## Run local inference on a Mac — no API key

Install Ollama from its official distribution, start it, then pull an
open-weight model. The following model matches the repository's root Modelfile.
Verify its license, RAM and disk requirements before use.

```bash
ollama pull qwen2.5-coder:7b
python3 -m pip install -e .
OLLAMA_MODEL=qwen2.5-coder:7b skull-llm doctor
OLLAMA_MODEL=qwen2.5-coder:7b skull-llm ask "Design an XUNIA knowledge graph"
```

In a checkout without an installed console script:

```bash
OLLAMA_MODEL=qwen2.5-coder:7b python3 -m skull_llm ask "Explain SKULL"
```

Use `--depth 1` for one model call, `--depth 2` (default) for
draft / critique / revision (three calls), and `--depth 3` for
plan / draft / critique / revision (four calls). Higher depth costs
additional **local inference time**, not money. Specify `--model`
to select an installed local model. `--json` reports call counts,
retrieval counts, critique, provenance and memory warnings.

By default, SKULL does **not** persist the question or response.
`--remember` opts into existing secret-filtered local GPT-Doug episodic
memory. The ontology is read from `config/global-ontology.json` and
memory from `~/.gpt-doug/brain-memory-v1.jsonl`; neither requires paid APIs.
External actions, web browsing, self-modification, and deployment are not
performed by the inference runtime. Retrieved text is explicitly marked
untrusted. Claims made by a model aren't proof of execution.

If `OLLAMA_BASE_URL` points outside HTTP loopback, requests fail
closed. The existing `ai_killswitch` must permit inference. Local data
can still be sensitive: review your prompts and machine access controls.

## Train the original small Transformer

PyTorch is optional: only training and checkpoint sampling require it.

```bash
python3 -m pip install -e '.[skull]'
skull-llm train ./authorized-corpus.txt --steps 100 --out ./skull-local.pt
skull-llm sample ./skull-local.pt "SKULL-LLM"
```

Example defaults: 2 layers, 128 dimensions, 4 attention heads,
128-token context, 8 sequences/batch. Training has finite steps,
seed control, gradient clipping and a maximum 32 MiB corpus size.
A 100-step byte-level model is an educational foundation, **not a
competitive chatbot**. Effective future upgrades require permissioned
high-quality data, appropriate pretraining resources, alignment work,
evaluations, and truthful comparisons against baselines. Do not train on
private or copyrighted datasets without rights.

Checkpoints use `torch.save`; loading requests `weights_only=True`.
Only load your own validated checkpoints.

## Validate

```bash
python3 -m unittest tests.test_skull_llm -v
python3 -m unittest tests.test_gpt_brain -v
```

PyTorch tests skip when the optional dependency is missing.
For an inference smoke test, Ollama and the configured model must be
running on the local computer. No live model was contacted when authoring
this change.

## Integrate with GPT-DOUG-LLM / XUNIA

- Same repository, existing ontology, existing memory provenance format.
- Uses `agents.llm_backend.OllamaProvider` and the global emergency stop.
- Separate package to avoid breaking existing GPT-Doug, XUNIA, Brain,
  or CLI entry points.
- Future work: benchmark against the current `gpt_brain` baseline using
  held-out tasks, explicit correctness scoring, latency and memory metrics;
  improve neural model only after measurable gains are observed.
