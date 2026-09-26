from .models import AgentSpec


AGENTS: dict[str, AgentSpec] = {
    "ontology": AgentSpec(
        "ontology",
        "Ground requests in the shared semantic model and identify relevant objects/links.",
        "You are GPT-Doug's ontology specialist. Use supplied ontology context as source of truth. "
        "Separate source-backed facts from inference. Return a concise task artifact, not hidden reasoning.",
    ),
    "research": AgentSpec(
        "research",
        "Evaluate evidence, sources, uncertainty and research gaps.",
        "You are GPT-Doug's evidence specialist. Identify what is known, what is uncertain, and what "
        "evidence would change the conclusion. Do not fabricate citations or results.",
    ),
    "builder": AgentSpec(
        "builder",
        "Design or implement software, schemas, workflows and tests.",
        "You are GPT-Doug's builder. Produce concrete implementation artifacts, interfaces, tests, "
        "migration steps, or code-level decisions. Prefer small compatible changes.",
    ),
    "critic": AgentSpec(
        "critic",
        "Attack assumptions, contradictions, safety gaps and unsupported claims.",
        "You are GPT-Doug's adversarial critic. Look for contradictions, missing evidence, unsafe leaps, "
        "and failure modes. Be specific and evidence-aware.",
    ),
    "reviewer": AgentSpec(
        "reviewer",
        "Check completeness, consistency and deliverable quality.",
        "You are GPT-Doug's reviewer. Check whether the requested task is actually satisfied and list "
        "only material defects or missing pieces.",
    ),
}


class BrainRouter:
    KEYWORDS = {
        "ontology": {"ontology", "graph", "schema", "entity", "relationship", "knowledge"},
        "research": {"research", "study", "evidence", "medical", "cancer", "clinical", "paper", "patent"},
        "builder": {"build", "code", "repo", "implement", "api", "app", "test", "deploy", "clone"},
        "critic": {"audit", "verify", "risk", "safety", "attack", "contradiction", "review"},
    }

    def route(self, task: str, max_agents: int = 4) -> list[AgentSpec]:
        words = {w.strip(".,:;!?()[]{}\"'").lower() for w in task.split()}
        scored: list[tuple[int, str]] = []
        for name, keys in self.KEYWORDS.items():
            scored.append((len(words & keys), name))
        scored.sort(key=lambda item: item[0], reverse=True)
        chosen = [name for score, name in scored if score > 0]
        if not chosen:
            chosen = ["ontology", "builder"]
        if "critic" not in chosen:
            chosen.append("critic")
        unique: list[str] = []
        for name in chosen:
            if name not in unique:
                unique.append(name)
        return [AGENTS[name] for name in unique[:max_agents]]
