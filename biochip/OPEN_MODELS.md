# BioChip open-model adapter

Provides discovery and inference for **any installed chat model exposed through a supported local server**; it does not ship, download, train, or automatically run all models.

Supported adapters:
- Ollama (native /api/tags and /api/chat); for locally installed Qwen, DeepSeek, Gemma, Llama, Mistral, GPT-OSS and other models.
- OpenAI-compatible localhost APIs (/v1/models and /v1/chat/completions): vLLM, llama.cpp server, LM Studio, LocalAI and similar servers.

**A model being discoverable is not a license verification.** Review model cards and license terms before installation or distribution. Servers must be started separately; this component makes no paid requests.

## Example

```bash
# Install Ollama from its official distribution and separately pull a model you choose.
python3 - <<'PY'
from biochip import BioChip
from biochip.models import ModelRouter
router = ModelRouter()
models, errors = router.discover()
print("Available:", models, "Offline:", errors)
if models:
    chip = BioChip("biochip.sqlite3")
    print(router.chat_with_memory(models[0], "Explain ontology memory",
                                 chip=chip, actor="local-user"))
PY
python3 -m unittest discover -s biochip/tests -v
```

Connections are restricted to HTTP loopback endpoints to reduce accidental data disclosure and SSRF exposure. A model server can still execute arbitrary model-specific plugins or unsafe configurations independently: only use trusted local servers and approved models. No conversation or prompt is persisted by this adapter unless `save_reply_key` is explicitly supplied. The BioChip owner field is *not* an authentication system; any production service must authenticate its caller and bind the actor itself. Network exposure and authorization require separate review.
