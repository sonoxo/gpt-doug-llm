from __future__ import annotations

from .types import Task


CODE_WORDS = {
    "code", "python", "javascript", "typescript", "react",
    "api", "bug", "fix", "terminal", "bash", "git",
    "github", "function", "class", "server", "frontend",
    "backend", "database", "html", "css", "deploy",
    "build", "compile", "test", "repository", "repo",
}

TOOL_WORDS = {
    "search", "browse", "github", "file", "terminal",
    "run", "deploy", "database", "download", "upload",
    "inspect", "execute", "project",
}

REASONING_WORDS = {
    "analyze", "reason", "compare", "plan", "design",
    "architecture", "why", "strategy", "evaluate",
    "solve", "recommend", "decide", "debug",
}

SECURITY_WORDS = {
    "security", "audit", "secret", "token", "key",
    "vulnerability", "defense", "defensive", "permission",
    "credential", "safe",
}

FILE_WORDS = {
    "file", "folder", "repository", "repo",
    "source", "project", "workspace",
}


def classify(prompt: str) -> Task:
    p = prompt.lower()
    words = set(
        p.replace("/", " ")
         .replace("-", " ")
         .replace("_", " ")
         .split()
    )

    needs_code = bool(words & CODE_WORDS)
    needs_tools = bool(words & TOOL_WORDS)
    needs_security = bool(words & SECURITY_WORDS)
    needs_files = bool(words & FILE_WORDS)
    needs_reasoning = bool(words & REASONING_WORDS) or not needs_code

    complexity = 0.20
    complexity += min(len(prompt) / 3000, 0.30)
    complexity += 0.15 if needs_code else 0
    complexity += 0.10 if needs_tools else 0
    complexity += 0.10 if needs_reasoning else 0
    complexity += 0.10 if needs_security else 0
    complexity += 0.05 if needs_files else 0
    complexity = min(complexity, 1.0)

    if needs_security:
        task_type = "security"
    elif needs_code:
        task_type = "coding"
    elif needs_tools:
        task_type = "tool"
    elif needs_reasoning:
        task_type = "reasoning"
    else:
        task_type = "general"

    return Task(
        prompt=prompt,
        task_type=task_type,
        complexity=complexity,
        needs_code=needs_code,
        needs_tools=needs_tools,
        needs_reasoning=needs_reasoning,
        needs_security=needs_security,
        needs_files=needs_files,
    )
