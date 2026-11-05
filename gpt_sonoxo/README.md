# GPT-SONOXO — Local Neural Command Center

GPT-SONOXO is a local, **read-only**, responsive web application inside
sonoxo/gpt-doug-llm. It uses free [Ollama](https://ollama.com/) inference and
the existing GPT-DOUG BrainRouter for *advisory role routing*.

## macOS quick start (Apple Silicon or Intel)

Ollama's API listens on **127.0.0.1:11434**; GPT-Sonoxo listens on
**127.0.0.1:8765**. These are separate processes.

1. Install Ollama if missing: `brew install ollama`.
   Check it with `curl -fsS http://127.0.0.1:11434/api/tags`.
   If that returns JSON, **Ollama is already running**; do not run
   `ollama serve` again. The `address already in use` message on port
   11434 is normal when a service already owns the port.
2. Get the GPT-Sonoxo development branch and pull the local model:

   ```sh
   git clone --depth 1 --branch feat/gpt-sonoxo-local-command-center \
     https://github.com/sonoxo/gpt-doug-llm.git ~/Downloads/gpt-sonoxo-local
   cd ~/Downloads/gpt-sonoxo-local
   ollama pull qwen2.5:3b
   python3 -m gpt_sonoxo
   ```

3. Keep that terminal open and visit http://127.0.0.1:8765/ .
   The browser URL may carry a harmless tracking query parameter; the server
   serves the homepage regardless of that parameter.

No pip installation is required when using `python3 -m gpt_sonoxo` from the
repository root. Alternatively `python3 -m pip install -e .` installs the
`gpt-sonoxo` console command. Set `GPT_SONOXO_MODEL` to the name of
another local Ollama chat model if preferred.

If the browser says `ERR_CONNECTION_REFUSED` on **8765**, GPT-Sonoxo
itself is not listening. Run `python3 -m gpt_sonoxo` from the repository
root and check for its ready message. This is unrelated to Ollama's
different port 11434.

## Features

- Responsive Sonoxo visual design, local chat, and model selection
- API endpoints: /api/health, /api/models, /api/ontology, /api/chat
- Existing GPT-DOUG BrainRouter for role *selection*, not agent execution
- Graph: GPT-DOUG, XUNIA, ZYRA, THEGREENHOUSE, Sonoxo Fleet, Ollama
- No paid APIs, account registration, cloud requirement, or API tokens
- History held only in the current browser tab's memory; never saved
- Emergency stop: GPT_DOUG_AI_BLOCK_ALL=1 blocks chat inference
- Loopback-only interface, strict origin/host checks, input size limits

## Limits and safety

Do not expose this server through a public tunnel, unrestricted proxy, or
port forwarding. It does not have user authentication and is designed for
a single operator running it on their own Mac.

The ontology graph is conceptual, **not a report of live service status**.
GPT-Sonoxo cannot execute tools, modify repositories, deploy, self-replicate,
or run unattended workflows. The existing Almighty Sonoxo MLM is a distinct
masked-token training model and is not the chat backend.

## Validation

From the repository root:

    python3 -m unittest tests.test_gpt_sonoxo -v

Tests mock Ollama inference and validate the local HTTP service. For actual
inference, start Ollama, install a local chat model and use the browser UI.
