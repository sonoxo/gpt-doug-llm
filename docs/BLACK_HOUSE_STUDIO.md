# Black House Studio / Orbit

Orbit is the browser development surface for `sonoxo/gpt-doug-llm`. This integration adds a discoverable ecosystem entry, a model bridge, and opt-in project memory for the Wakeup3LM kernel.

[Open the deployed Studio](https://orbit-code-studio.almighty-son-8109.chatgpt.site). The current deployment is **owner-private**: a repository link or a free account does not grant access to it. The source additions described below can run on infrastructure you control.

## Capability status

| Capability | Available behavior | Dependency or boundary |
| --- | --- | --- |
| Browser workspace | File editor, console, previews, collaborative project state, chat, and static snapshots | The deployed Studio's access policy applies to the workspace and snapshots |
| Browser AI | Model inference on the user's device | Compatible WebGPU browser, memory, and a model download |
| Black House model bridge | Ollama-compatible model discovery, chat, health checks, and bounded response caching | A running bridge and an installed, allowlisted Ollama model |
| Project memory | Durable SQLite notes, project isolation, recall, deletion, and import/export | Opt in when constructing Wakeup3LM; browser-to-kernel memory synchronization is not automatic |
| Compiled languages and long-running services | Connect a separately operated execution service | A container host is required; the browser workspace is not a Linux container fleet |
| Hosting outside the current Site audience | Deploy using a host and audience policy you control | This repository update does not change the current Site's access policy |

No paid model API is required for browser inference or an Ollama model you operate. Compute, storage, bandwidth, and model licenses still apply. Existing API tokens authorize the quota assigned by their provider; they cannot be converted into unlimited inference. The bridge can reuse an exact prior response within a project to reduce repeated inference, but does not mint tokens or bypass quotas.

## Connect an installed model

Start Ollama and install the model you intend to serve. The bridge defaults to `qwen2.5-coder:7b`; `gpt-doug` may be used after creating that model from the repository's [`Modelfile`](../Modelfile).

From the repository root, start the bridge with the Studio's exact origin allowed:

```bash
DOUG_BRIDGE_ORIGINS=https://orbit-code-studio.almighty-son-8109.chatgpt.site python3 -m wakeup3lm.bridge
```

The default listener is `127.0.0.1:8791`, forwarding only to the configured Ollama service at `http://127.0.0.1:11434`. In the Studio's GPT Doug connection settings, enter the reachable bridge base URL and discover its models. The bridge returns only installed models that its allowlist permits.

For use from other devices, provide an HTTPS endpoint to the bridge, configure the exact client origins, and set `DOUG_BRIDGE_TOKEN`. Non-loopback binding requires a bearer token of at least 24 characters. Keep an upstream model service behind the bridge. Browsers may require permission for loopback requests or reject them; an HTTPS bridge reachable by the browser avoids relying on that local-network exception.

| Environment variable | Default / purpose |
| --- | --- |
| `DOUG_BRIDGE_HOST` | `127.0.0.1`; listener address |
| `DOUG_BRIDGE_PORT` | `8791`; listener port |
| `DOUG_BRIDGE_OLLAMA_URL` | `http://127.0.0.1:11434`; operator-configured upstream |
| `DOUG_BRIDGE_MODEL` | `qwen2.5-coder:7b`; default model |
| `DOUG_BRIDGE_MODELS` | Optional comma-separated allowlist; defaults to the configured default model |
| `DOUG_BRIDGE_ORIGINS` | Comma-separated exact permitted browser origins |
| `DOUG_BRIDGE_TOKEN` | Optional loopback token; mandatory for non-loopback binding |

When a token is configured, every API route requires `Authorization: Bearer <token>`. A browser caller must also pass the origin allowlist. A request cannot choose a different upstream URL.

| Route | Contract |
| --- | --- |
| `GET /health` | Probes Ollama; healthy only when the configured default model is installed |
| `GET /api/tags` | Returns installed, allowlisted models and the `bridge: "black-house"` marker |
| `POST /api/chat` | Accepts Ollama-style `model`, `messages`, `stream: false`, and supported `options`; returns a completed chat response |

Example chat request from a local client:

```bash
curl --fail-with-body http://127.0.0.1:8791/api/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Doug-Project: hello-world' \
  --data '{"model":"qwen2.5-coder:7b","stream":false,"messages":[{"role":"user","content":"Write a Python hello-world function."}]}'
```

Add the bearer header when a token is configured. `X-Doug-Project` enables project-scoped, exact-response caching; omitting it disables caching. Model, messages, and generation options also participate in the cache key. The bridge bounds input, output, concurrency, and time spent waiting for the upstream model. It does not execute model-generated code.

## Durable project memory

Memory stores selected project context, rather than granting instructions or permissions to an agent. Enable it explicitly and keep the database outside the workspace that generated code can edit:

```python
from pathlib import Path
from wakeup3lm import Wakeup3LM

kernel = Wakeup3LM(
    Path("/srv/workspaces/hello-world"),
    memory_path=Path("/srv/black-house-state/memory.sqlite3"),
    project_id="hello-world",
)
kernel.memory.remember(
    "decision",
    "The application uses Python and must work without a paid model API.",
    source="human",
    author="project-owner",
)
context = kernel.memory.recall("Python", limit=10, char_budget=3000)
archive = kernel.memory.export()
```

Use a stable explicit project ID when moving a project between machines. If omitted, the ID is derived from the resolved workspace path. Calls without `memory_path` retain the kernel's existing behavior with memory disabled.

`ProjectMemory` supports `remember`, `recall`, `forget`, `export`, and `import_payload`. Exports use schema `black-house.memory.v1` with a project ID and note records containing `id`, `kind`, `content`, `source`, `author`, and `created`. Import requires the destination project to match. Imported attribution describes the source's claim; it does not establish authority.

The kernel exposes `recall_memory` and `remember_memory` to models only when memory is enabled. Model writes are labeled as model context. Recalled notes are untrusted context and cannot authorize tool execution, deployments, or other actions. This update does not automatically copy private Studio conversations or source files into a kernel database.

## Data, logic, actions, and human-agent work

The supplied human-agent teaming reference is used as a design map for typed project context. It does not establish a connection to an external Ontology or enterprise system.

| Reference layer | Black House representation | Meaning |
| --- | --- | --- |
| Data sources | `data` notes with provenance | Selected facts or source descriptions used as context |
| Logic sources | `logic` and `preference` notes | Rules or project preferences to consider during planning |
| Systems of action | `action` notes | Records or proposals about actions; storing a note does not execute it |
| Human-agent teaming | `decision` notes with human/model/imported attribution | Durable project decisions and their stated source |
| Shared project context | Project-scoped memory and bounded recall | Context available to a configured kernel; not an authorization system |

An actual Palantir deployment uses the separate [Foundry bridge](PALANTIR_FOUNDRY.md), with its own tenant credentials and write controls. Orbit's registration does not connect it to such a tenant.

## Integration files

- [`the-black-house/runtime/orbit-studio.json`](../the-black-house/runtime/orbit-studio.json) describes this optional surface and its boundaries.
- [`docs/resources.json`](resources.json) makes it discoverable in the Resource Hub.
- [`docs/PRODUCTS.md`](PRODUCTS.md) records its product status.
- [`wakeup3lm/bridge.py`](../wakeup3lm/bridge.py) provides the local model bridge.
- [`wakeup3lm/README.md`](../wakeup3lm/README.md) documents the kernel and memory interface.

The integration manifest is descriptive. It does not provision a model, open a network listener, migrate a workspace, grant public access, or add a required gate to the existing Black House runtime contract.
