# XUNIA Forge — Free AI Engineering Supertool

One local-first workspace that connects five open-source projects without copying or modifying their upstream code.

| Layer | Project | Role |
|---|---|---|
| Model gateway | [LiteLLM](https://github.com/BerriAI/litellm) | OpenAI-compatible routing across local or remote models |
| Infrastructure | [OpenTofu](https://github.com/opentofu/opentofu) | Reproducible start/stop lifecycle |
| Python runtime | [uv](https://github.com/astral-sh/uv) | Fast locked control-plane environment |
| Research | [SearXNG](https://github.com/searxng/searxng) | Private metasearch with JSON results |
| Coding | [Continue](https://github.com/continuedev/continue) | IDE agent connected to the LiteLLM gateway |

## Launch

Requirements: Docker Desktop and Python 3.11+. `uv` and OpenTofu are optional for the direct Docker route.

```bash
cd xunia-forge
cp .env.example .env
./forge up
```

Open <http://127.0.0.1:8787>. The gateway is at `http://127.0.0.1:4000/v1` and private search is at `http://127.0.0.1:8088`.

### Connect a free local model

Run any OpenAI-compatible local inference server, then put its endpoint and model name in `.env`. No Ollama dependency is required. The default assumes a server at port `1234`:

```dotenv
LOCAL_LLM_BASE_URL=http://host.docker.internal:1234/v1
LOCAL_MODEL_NAME=local-model
```

Copy `continue/config.yaml` into a Continue configuration directory, or use it as the model configuration reference. Continue then talks to LiteLLM, not directly to a vendor.

## Commands

```bash
./forge up       # start the stack
./forge down     # stop it
./forge status   # health report
./forge logs     # follow service logs
./forge test     # integration checks
./forge tofu     # OpenTofu-managed deployment
```

## Free means

The orchestration software is open source and the default stack has no paid API requirement. Model compute still has to come from your own machine or a provider account. Usage fees are never silently created. Search providers can rate-limit public instances.

## Security boundary

Services bind to `127.0.0.1`, SearXNG JSON access is local, secrets stay in ignored `.env`, containers run with reduced privileges where supported, and the control plane does not execute arbitrary shell commands.
