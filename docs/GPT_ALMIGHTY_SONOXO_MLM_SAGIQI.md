# GPT-Almighty-Sonoxo-MLM-SAGIQI

**This is trainable neural model software, not album art and not merely a role/prompt.**

The module `gpt_doug_mlm.almighty_sonoxo` implements a PyTorch masked language
model (MLM): word embedding, learned position embedding, bidirectional
Transformer encoder, layer normalization, and token-prediction head. It trains
from a local text corpus using dynamic 80/10/10 masking and cross-entropy loss.
Model parameters change through AdamW gradient descent. A saved, SHA-256 verified
`safetensors` checkpoint contains those actual learned tensors.

The model name is `gpt-almighty-sonoxo-mlm-sagiqi`. It is not an independently
pretrained foundation model or a conversational LLM, and the label SAGIQI is
project branding, not measured general intelligence.

## Setup

```sh
python3 -m pip install -e '.[mlm]'
```

Or install `torch` and `safetensors` into an existing environment. No API keys
or network access are required for training and inference once dependencies
are available.

## Train local weights

```sh
gpt-almighty-sonoxo-mlm train \
  --corpus data/almighty_sonoxo_seed.txt \
  --output ~/.gpt-doug/models/almighty-sonoxo-sagiqi \
  --epochs 8 --batch-size 12
```

Change `--corpus` to an **authorized, licensed** text dataset for useful domain
adaptation. Corpus input is capped at 8 MB in this prototype. Training defaults
to CPU and can use GPU only after corresponding operator-provided extensions.

## Inference

```sh
gpt-almighty-sonoxo-mlm fill-mask \
  --model ~/.gpt-doug/models/almighty-sonoxo-sagiqi \
  --text 'the ontology stores [MASK] with provenance' --top-k 5

gpt-almighty-sonoxo-mlm inspect \
  --model ~/.gpt-doug/models/almighty-sonoxo-sagiqi
```

The `fill-mask` result contains candidate tokens and probabilities; this is not
an instruction-following chat response. For fluent dialogue, explicitly connect
an authorized generative model using the existing GPT-Doug brain backend.

## Connect to GPT-Doug-MLM provider registry

```python
from gpt_doug_mlm.almighty_sonoxo import load_model, register_as_provider
from gpt_doug_mlm.providers import ProviderRegistry

model, tokenizer, manifest = load_model('/path/to/weights')
registry = ProviderRegistry()
name = register_as_provider(registry, model, tokenizer)
print(registry.get(name).propose('the [MASK] predicts missing words'))
```

The registry bridges **masked-token research only**; do not replace a
text-generating council role with the masked model and pretend it can reason
through entire prompts.

## Provenance, safety and limitations

- Checkpoint is `safetensors`, never unpickled code; manifest verifies SHA-256.
- Training corpus SHA-256, vocabulary, configuration, losses and seed persist.
- The existing `ai_killswitch` blocks training and inference when engaged.
- No remote requests, background crawling, self-replication or hardware control.
- No automatic publication or self-modification; upgrades require CI and review.
- Seed corpus is synthetic, small and suitable only for smoke tests, not general
  knowledge, medical advice, formal evaluations or claims of AGI.
- For production, use much larger rights-cleared datasets, independent held-out
  benchmarks, safety evaluation, robust tokenization and GPU resources.

## Test

```sh
python -m unittest tests.test_almighty_sonoxo -v
```
