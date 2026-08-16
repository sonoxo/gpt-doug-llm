from .types import Task

CODE_WORDS = {
    "code","python","javascript","typescript","react","api","bug","fix",
    "terminal","bash","git","github","function","class","server","frontend",
    "backend","database","html","css","deploy"
}

TOOL_WORDS = {
    "search","browse","github","file","terminal","run","deploy",
    "database","email","calendar","download","upload"
}

REASONING_WORDS = {
    "analyze","reason","compare","plan","design","architecture",
    "why","strategy","evaluate","solve"
}

def classify(prompt: str) -> Task:
    p = prompt.lower()
    words = set(p.replace("/", " ").replace("-", " ").split())

    needs_code = bool(words & CODE_WORDS)
    needs_tools = bool(words & TOOL_WORDS)
    needs_reasoning = bool(words & REASONING_WORDS) or not needs_code

    complexity = 0.25
    complexity += min(len(prompt) / 4000, 0.35)
    complexity += 0.15 if needs_code else 0
    complexity += 0.15 if needs_tools else 0
    complexity += 0.10 if needs_reasoning else 0
    complexity = min(complexity, 1.0)

    if needs_code:
        kind = "coding"
    elif needs_tools:
        kind = "tool"
    elif needs_reasoning:
        kind = "reasoning"
    else:
        kind = "general"

    return Task(
        prompt=prompt,
        task_type=kind,
        complexity=complexity,
        needs_code=needs_code,
        needs_tools=needs_tools,
        needs_reasoning=needs_reasoning,
    )
