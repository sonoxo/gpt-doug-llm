from dataclasses import dataclass

@dataclass
class Verification:
    score: float
    problems: list[str]

def verify_text(prompt: str, answer: str) -> Verification:
    problems = []

    if not answer.strip():
        problems.append("empty answer")

    if len(answer.strip()) < 8:
        problems.append("answer suspiciously short")

    lower = answer.lower()

    if "i can't" in lower and len(answer) < 100:
        problems.append("possible premature refusal")

    if "todo" in lower:
        problems.append("unfinished TODO marker")

    if "localhost:11434" in lower or "ollama" in lower:
        problems.append("forbidden Ollama dependency detected")

    score = max(0.0, 1.0 - 0.2 * len(problems))
    return Verification(score, problems)
