#!/usr/bin/env python3
"""GPT-XUNIA-GODIS local Ollama stack.

Provides terminal-ready profiles for the human analogy in the project:
LLM/Brain, RAG, Agent, and MCP, with GPT-XUNIA-GODIS as the orchestrator.
The module intentionally keeps network access limited to the configured local
Ollama endpoint and explicitly configured MCP servers.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_BASE_MODEL = os.environ.get("XUNIA_BASE_MODEL", "qwen2.5-coder:7b")
DEFAULT_TIMEOUT = float(os.environ.get("XUNIA_TIMEOUT", "90"))


@dataclass(frozen=True)
class Profile:
    key: str
    model: str
    role: str
    modelfile: Path


PROFILES: dict[str, Profile] = {
    "godis": Profile("godis", "gpt-xunia-godis", "orchestrator: brain + books + hands + connections", ROOT / "models/gpt-xunia-godis/Modelfile"),
    "brain": Profile("brain", "gpt-xunia-brain", "LLM core reasoning and generation", ROOT / "models/gpt-xunia-brain/Modelfile"),
    "rag": Profile("rag", "gpt-xunia-rag", "LLM + local retrieved knowledge", ROOT / "models/gpt-xunia-rag/Modelfile"),
    "agent": Profile("agent", "gpt-xunia-agent", "bounded repository agent", ROOT / "models/gpt-xunia-agent/Modelfile"),
    "mcp": Profile("mcp", "gpt-xunia-mcp", "MCP connection reasoning layer", ROOT / "models/gpt-xunia-mcp/Modelfile"),
}

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".jsx", ".ts", ".tsx", ".json",
    ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".css", ".html",
    ".sql", ".go", ".rs", ".java", ".kt", ".swift", ".c", ".h", ".cpp",
}
TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-]{1,}")


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, body: dict[str, Any] | None = None, timeout: float | None = None) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="GET" if body is None else "POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as response:
                raw = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OllamaError(f"Ollama unavailable at {self.base_url}: {exc}") from exc
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON") from exc
        if payload.get("error"):
            raise OllamaError(str(payload["error"]))
        return payload

    def installed_models(self) -> list[str]:
        payload = self._request("/api/tags", timeout=5)
        return [str(item.get("name")) for item in payload.get("models", []) if item.get("name")]

    def chat(self, model: str, prompt: str, *, system: str | None = None, context: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        if context:
            messages.append({"role": "system", "content": "LOCAL CONTEXT\n" + context})
        messages.append({"role": "user", "content": prompt})
        payload = self._request(
            "/api/chat",
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "keep_alive": "30m",
            },
        )
        content = str((payload.get("message") or {}).get("content") or "").strip()
        if not content:
            raise OllamaError("Ollama returned an empty response")
        return content


def resolve_profile(value: str) -> Profile:
    key = value.strip().lower()
    if key in PROFILES:
        return PROFILES[key]
    for profile in PROFILES.values():
        if key == profile.model:
            return profile
    raise ValueError(f"Unknown profile '{value}'. Choose: {', '.join(PROFILES)}")


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, check=check)


def _render_modelfile(path: Path, base_model: str) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("FROM "):
        raise ValueError(f"Invalid Modelfile: {path}")
    lines[0] = "FROM " + base_model
    return "\n".join(lines) + "\n"


def install_profiles(base_model: str, pull: bool = True) -> None:
    if shutil.which("ollama") is None:
        raise RuntimeError("Ollama is not installed or is not on PATH.")
    if pull:
        print(f"⬇️  Ensuring base model: {base_model}")
        _run(["ollama", "pull", base_model])
    for profile in PROFILES.values():
        if not profile.modelfile.exists():
            raise FileNotFoundError(profile.modelfile)
        rendered = _render_modelfile(profile.modelfile, base_model)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".Modelfile", delete=False) as handle:
            handle.write(rendered)
            temp_name = handle.name
        try:
            print(f"🧠 Building {profile.model} ({profile.role})")
            _run(["ollama", "create", profile.model, "-f", temp_name])
        finally:
            Path(temp_name).unlink(missing_ok=True)
    print("✅ GPT-XUNIA-GODIS Ollama stack installed.")


def doctor(client: OllamaClient) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ollama_binary": shutil.which("ollama"),
        "ollama_base_url": client.base_url,
        "expected_models": [p.model for p in PROFILES.values()],
        "installed_models": [],
        "missing_models": [],
        "healthy": False,
    }
    if not result["ollama_binary"]:
        result["error"] = "ollama binary not found on PATH"
        return result
    try:
        installed = client.installed_models()
    except Exception as exc:
        result["error"] = str(exc)
        return result
    result["installed_models"] = installed
    normalized = {name.split(":", 1)[0] for name in installed}
    missing = [p.model for p in PROFILES.values() if p.model not in installed and p.model not in normalized]
    result["missing_models"] = missing
    result["healthy"] = not missing
    return result


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


@dataclass(frozen=True)
class Chunk:
    path: str
    index: int
    text: str
    score: float = 0.0


def _iter_text_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix.lower() in TEXT_EXTENSIONS or not root.suffix:
            yield root
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield path


def build_chunks(root: Path, *, chunk_chars: int = 1800, max_file_bytes: int = 1_000_000) -> list[Chunk]:
    root = root.expanduser().resolve()
    chunks: list[Chunk] = []
    for path in _iter_text_files(root):
        try:
            if path.stat().st_size > max_file_bytes:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not text.strip():
            continue
        display = path.name if root.is_file() else str(path.relative_to(root))
        for index, start in enumerate(range(0, len(text), chunk_chars)):
            piece = text[start : start + chunk_chars].strip()
            if piece:
                chunks.append(Chunk(display, index, piece))
    return chunks


def retrieve(root: Path, question: str, *, top_k: int = 6) -> list[Chunk]:
    query_tokens = _tokenize(question)
    if not query_tokens:
        return []
    ranked: list[Chunk] = []
    for chunk in build_chunks(root):
        tokens = _tokenize(chunk.text)
        overlap = query_tokens & tokens
        if not overlap:
            continue
        exact_bonus = 2.0 if question.lower() in chunk.text.lower() else 0.0
        density = len(overlap) / max(1, len(query_tokens))
        score = exact_bonus + density + (len(overlap) / max(20, len(tokens)))
        ranked.append(Chunk(chunk.path, chunk.index, chunk.text, score))
    ranked.sort(key=lambda item: (-item.score, item.path, item.index))
    return ranked[: max(1, top_k)]


def format_context(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"[source:{chunk.path}#{chunk.index}]\n{chunk.text}" for chunk in chunks)


def run_rag(client: OllamaClient, root: Path, question: str, top_k: int) -> str:
    chunks = retrieve(root, question, top_k=top_k)
    if not chunks:
        return "No relevant local context was found."
    return client.chat(PROFILES["rag"].model, question, context=format_context(chunks))


def run_agent(root: Path, goal: str, client: OllamaClient) -> int:
    try:
        from zyra_agent import ZyraAgent, print_agent_report
    except ImportError as exc:
        raise RuntimeError("ZYRA Agent Core is unavailable in this checkout.") from exc
    agent = ZyraAgent(root.expanduser().resolve(), model=PROFILES["agent"].model, base_url=client.base_url)
    result = agent.run(goal, evolve=False)
    print_agent_report(result)
    return 0 if str(getattr(result, "status", "")).upper() in {"PASS", "PASSED", "SUCCESS", "COMPLETED", "KEPT"} else 1


def _mcp_imports():
    try:
        from mcp import Client, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as exc:
        raise RuntimeError('MCP support requires: pip install "mcp[cli]>=2,<3"') from exc
    return Client, StdioServerParameters, stdio_client


def _mcp_client_for(url: str | None, stdio: list[str] | None):
    Client, StdioServerParameters, stdio_client = _mcp_imports()
    if url:
        return Client(url)
    if not stdio:
        raise ValueError("Specify --url or --stdio.")
    params = StdioServerParameters(command=stdio[0], args=stdio[1:])
    return Client(stdio_client(params))


def _dump_obj(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_dump_obj(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _dump_obj(v) for k, v in value.items()}
    return repr(value)


async def mcp_list(url: str | None, stdio: list[str] | None) -> None:
    client = _mcp_client_for(url, stdio)
    async with client:
        result = await client.list_tools()
        payload = {
            "protocol_version": getattr(client, "protocol_version", None),
            "tools": [_dump_obj(tool) for tool in result.tools],
        }
        print(json.dumps(payload, indent=2))


async def mcp_call(url: str | None, stdio: list[str] | None, tool: str, arguments: dict[str, Any]) -> None:
    client = _mcp_client_for(url, stdio)
    async with client:
        result = await client.call_tool(tool, arguments)
        print(json.dumps(_dump_obj(result), indent=2))


def _add_mcp_target(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="MCP Streamable HTTP URL")
    group.add_argument("--stdio", nargs=argparse.REMAINDER, help="MCP stdio command followed by its arguments")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xunia-godis", description="GPT-XUNIA-GODIS local Ollama + RAG + Agent + MCP command center")
    sub = parser.add_subparsers(dest="command", required=True)

    install = sub.add_parser("install", help="Pull the base model and build all XUNIA Ollama profiles")
    install.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    install.add_argument("--no-pull", action="store_true", help="Do not pull the base model before creating profiles")

    sub.add_parser("doctor", help="Check Ollama and all XUNIA model profiles")
    sub.add_parser("models", help="List expected and installed Ollama models")

    run = sub.add_parser("run", help="Open an interactive Ollama terminal session")
    run.add_argument("profile", nargs="?", default="godis")

    ask = sub.add_parser("ask", help="Send one prompt to an XUNIA profile")
    ask.add_argument("profile")
    ask.add_argument("prompt", nargs="+")

    rag = sub.add_parser("rag", help="Ask a question grounded in local files")
    rag.add_argument("path")
    rag.add_argument("question", nargs="+")
    rag.add_argument("--top-k", type=int, default=6)

    agent = sub.add_parser("agent", help="Run the existing bounded ZYRA Agent Core using the XUNIA agent model")
    agent.add_argument("path")
    agent.add_argument("goal", nargs="+")

    mcp_tools = sub.add_parser("mcp-list", help="List tools from an MCP server using the current official Python SDK")
    _add_mcp_target(mcp_tools)

    mcp_invoke = sub.add_parser("mcp-call", help="Call a tool on an MCP server")
    mcp_invoke.add_argument("tool")
    mcp_invoke.add_argument("arguments", help="JSON object of tool arguments")
    _add_mcp_target(mcp_invoke)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = OllamaClient()

    if args.command == "install":
        install_profiles(args.base_model, pull=not args.no_pull)
        return 0
    if args.command == "doctor":
        report = doctor(client)
        print(json.dumps(report, indent=2))
        return 0 if report["healthy"] else 1
    if args.command == "models":
        report = doctor(client)
        for profile in PROFILES.values():
            installed = profile.model in report.get("installed_models", []) or profile.model in {x.split(":", 1)[0] for x in report.get("installed_models", [])}
            print(f"{'✅' if installed else '⬜'} {profile.model:<20} {profile.role}")
        return 0 if report.get("healthy") else 1
    if args.command == "run":
        profile = resolve_profile(args.profile)
        if shutil.which("ollama") is None:
            raise RuntimeError("Ollama is not installed or is not on PATH.")
        return subprocess.call(["ollama", "run", profile.model])
    if args.command == "ask":
        profile = resolve_profile(args.profile)
        print(client.chat(profile.model, " ".join(args.prompt)))
        return 0
    if args.command == "rag":
        print(run_rag(client, Path(args.path), " ".join(args.question), args.top_k))
        return 0
    if args.command == "agent":
        return run_agent(Path(args.path), " ".join(args.goal), client)
    if args.command == "mcp-list":
        asyncio.run(mcp_list(args.url, args.stdio))
        return 0
    if args.command == "mcp-call":
        try:
            payload = json.loads(args.arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("arguments must be a JSON object") from exc
        if not isinstance(payload, dict):
            raise ValueError("arguments must be a JSON object")
        asyncio.run(mcp_call(args.url, args.stdio, args.tool, payload))
        return 0
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OllamaError, RuntimeError, ValueError, FileNotFoundError) as exc:
        print(f"XUNIA ERROR // {exc}", file=sys.stderr)
        raise SystemExit(1)
