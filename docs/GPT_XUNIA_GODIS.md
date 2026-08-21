# GPT-XUNIA-GODIS: local Ollama + RAG + Agent + MCP stack

This adds a terminal-ready implementation of the four-layer AI analogy:

| XUNIA profile | Analogy | Runtime capability |
|---|---|---|
| `gpt-xunia-brain` | Brain | Core LLM reasoning and generation |
| `gpt-xunia-rag` | Brain + books | Local file retrieval + grounded Ollama answer |
| `gpt-xunia-agent` | Brain + hands | Existing bounded ZYRA Agent Core using an Ollama model |
| `gpt-xunia-mcp` | Nervous system | Reasoning profile for MCP-connected tools/resources |
| `gpt-xunia-godis` | Full stack | Orchestrator profile spanning all four capabilities |

`GODIS` is the runtime/profile name. It does not represent a claim of authority or divinity.

## One-command install

```bash
bash scripts/install_xunia_godis.sh
```

The installer checks for Ollama, pulls the default base model (`qwen2.5-coder:7b`) when needed, creates all five local profiles, and runs the doctor check. Set `XUNIA_BASE_MODEL` before running the script if you want a different Ollama-compatible base model.

The Git repository stores the Modelfiles and runtime code, not multi-gigabyte model weights. Ollama manages the local model layers on the user's machine.

## Terminal commands

```bash
# full orchestrator chat
ollama run gpt-xunia-godis

# equivalent through the XUNIA command center
python3 xunia_godis.py run godis

# one-shot brain request
python3 xunia_godis.py ask brain "explain this repository"

# local RAG over a folder
python3 xunia_godis.py rag . "where is the Ollama model selected?"

# bounded repository Agent Core
python3 xunia_godis.py agent . "add a deterministic status check and test it"

# health/status
python3 xunia_godis.py doctor
python3 xunia_godis.py models
```

## MCP support

The MCP adapter uses the current official Python SDK v2, which supports MCP `2026-07-28` and negotiates older protocol-era servers automatically.

Install the optional dependency:

```bash
pip install -r requirements-mcp.txt
```

List tools from a Streamable HTTP server:

```bash
python3 xunia_godis.py mcp-list --url http://127.0.0.1:8000/mcp
```

List tools from a stdio server:

```bash
python3 xunia_godis.py mcp-list --stdio python3 server.py
```

Call a tool:

```bash
python3 xunia_godis.py mcp-call add '{"a":1,"b":2}' --url http://127.0.0.1:8000/mcp
```

## Design boundaries

- Ollama is local by default at `http://127.0.0.1:11434`.
- RAG reads local text/code files and excludes common generated/vendor directories.
- Agent execution is delegated to the repository's existing `ZyraAgent`, retaining its checkpoints, budgets, validation gates, and rollback behavior.
- MCP connections occur only when the user explicitly supplies a server URL or stdio command.
- Models do not receive magical terminal or network access. Deterministic runtime code remains the authority for actions.
