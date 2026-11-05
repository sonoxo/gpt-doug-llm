# GPT-SONOXO — Local Neural Command Center

GPT-SONOXO is a local, **read-only**, responsive web application inside
sonoxo/gpt-doug-llm. It uses free [Ollama](https://ollama.com/) inference and
the existing GPT-DOUG BrainRouter for *advisory role routing*.

## macOS quick start

Install Ollama using Homebrew, then run it (Terminal tab 1):

    brew install ollama
    ollama serve

In Terminal tab 2, download the model and install GPT-Sonoxo:

    ollama pull qwen2.5:3b
    cd gpt-doug-llm
    python3 -m pip install -e .
    gpt-sonoxo

Open http://127.0.0.1:8765 in a browser.

You can also use python3 -m gpt_sonoxo from the repository root.
Set GPT_SONOXO_MODEL=llama3.2:3b to select another Ollama model
that has already been downloaded.

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
