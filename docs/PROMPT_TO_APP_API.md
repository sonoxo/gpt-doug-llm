# Prompt-to-App API

An open-source, local-first alternative for the core **describe an app → generate source files** workflow. It does not copy Replit code or require a paid model API.

## Requirements

- Python 3.10+
- Ollama (or an Ollama-compatible local HTTP server)
- A local coding model, default: `qwen2.5-coder:7b`

## Start

```bash
ollama pull qwen2.5-coder:7b
python3 prompt_api.py
```

The service listens on `http://127.0.0.1:8790` by default.

## Generate an app

```bash
curl -X POST http://127.0.0.1:8790/generate \
  -H 'Content-Type: application/json' \
  -d '{"name":"todo-demo","prompt":"Build a clean browser todo app with localStorage, filters, and dark mode."}'
```

Generated files are written under `./prompt-app-projects/<name>/`.

## Endpoints

- `GET /health` — service/model configuration
- `GET /projects` — list generated projects
- `GET /projects/:name` — project metadata
- `POST /generate` — generate and materialize a project from a prompt

## Configuration

- `PROMPT_APP_HOST` — bind host, default `127.0.0.1`
- `PROMPT_APP_PORT` — port, default `8790`
- `PROMPT_APP_WORKSPACE` — generated-project root
- `PROMPT_APP_OLLAMA_URL` — model endpoint
- `PROMPT_APP_MODEL` — local model name

## Security boundary

The API validates project names and relative file paths, rejects traversal, limits request/file counts and sizes, and writes only inside its workspace. **Generated code is not automatically executed.** A production runner should execute untrusted generated projects only inside a real container/VM sandbox with CPU, memory, filesystem, process, and network limits.

## License

This addition follows the repository's MIT license. It is an independent implementation and is not Replit source code.
