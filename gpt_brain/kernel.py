from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .memory import BrainMemory
from .models import AgentSpec, BrainResult
from .ontology import OntologyIndex
from .router import BrainRouter

ChatFn = Callable[[list[dict[str, str]], Optional[str], dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class BrainConfig:
    model: Optional[str] = None
    temperature: float = 0.2
    max_agents: int = 4
    memory_limit: int = 8
    ontology_limit: int = 12


class BrainKernel:
    """Ontology-first orchestrator over GPT-Doug's existing provider facade."""

    def __init__(
        self,
        *,
        chat_fn: Optional[ChatFn] = None,
        memory: Optional[BrainMemory] = None,
        ontology: Optional[OntologyIndex] = None,
        router: Optional[BrainRouter] = None,
        config: Optional[BrainConfig] = None,
    ) -> None:
        self.chat_fn = chat_fn or self._repo_chat
        self.memory = memory or BrainMemory()
        self.ontology = ontology or OntologyIndex()
        self.router = router or BrainRouter()
        self.config = config or BrainConfig()

    @staticmethod
    def _repo_chat(messages, model, options):
        from agents import llm_backend
        return llm_backend.chat_once(messages, model, options)

    def _call(self, system: str, user: str) -> str:
        result = self.chat_fn(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            self.config.model,
            {"temperature": self.config.temperature},
        )
        if result.get("error"):
            detail = (result.get("message") or {}).get("content", "")
            raise RuntimeError(f"brain provider error: {result['error']}: {detail}")
        return str((result.get("message") or {}).get("content", "")).strip()

    @staticmethod
    def _context_block(title: str, items: list[dict[str, Any]]) -> str:
        return f"{title}:\n" + (json.dumps(items, ensure_ascii=False, indent=2) if items else "[]")

    def _run_agent(
        self,
        agent: AgentSpec,
        task: str,
        memory_ctx: list[dict[str, Any]],
        ontology_ctx: list[dict[str, Any]],
    ) -> tuple[str, str]:
        user = "\n\n".join(
            [
                f"TASK:\n{task}",
                self._context_block("ONTOLOGY CONTEXT", ontology_ctx),
                self._context_block("RECALLED MEMORY", memory_ctx),
                "Return a concise artifact with explicit uncertainty and provenance references when available.",
            ]
        )
        return agent.name, self._call(agent.system_prompt, user)

    def run(self, task: str) -> BrainResult:
        task = (task or "").strip()
        if not task:
            raise ValueError("task must be non-empty")

        run_id = uuid.uuid4().hex[:12]
        memory_ctx = self.memory.recall(task, self.config.memory_limit)
        ontology_ctx = self.ontology.search(task, self.config.ontology_limit)
        agents = self.router.route(task, self.config.max_agents)

        outputs: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=max(1, len(agents))) as pool:
            futures = {
                pool.submit(self._run_agent, a, task, memory_ctx, ontology_ctx): a.name
                for a in agents
            }
            for future in as_completed(futures):
                name, output = future.result()
                outputs[name] = output

        critique = self._call(
            "You are the final GPT-Doug critic. Do not expose hidden chain-of-thought. Return a compact audit summary.",
            "\n\n".join(
                [
                    f"TASK:\n{task}",
                    "SPECIALIST OUTPUTS:\n" + json.dumps(outputs, ensure_ascii=False, indent=2),
                    "List only material contradictions, unsupported claims, evidence gaps, and integration defects.",
                ]
            ),
        )

        answer = self._call(
            "You are GPT-Doug Brain, an ontology-first orchestration layer. Produce the final usable result, "
            "not private reasoning. Preserve provenance and distinguish fact from inference.",
            "\n\n".join(
                [
                    f"TASK:\n{task}",
                    self._context_block("ONTOLOGY CONTEXT", ontology_ctx),
                    self._context_block("RECALLED MEMORY", memory_ctx),
                    "SPECIALIST OUTPUTS:\n" + json.dumps(outputs, ensure_ascii=False, indent=2),
                    f"CRITIQUE:\n{critique}",
                    "Synthesize the best supported answer or build artifact. State uncertainty. "
                    "Do not claim actions succeeded unless evidence in the supplied context proves they did.",
                ]
            ),
        )

        provenance = sorted(
            {
                str(row.get("provenance"))
                for row in memory_ctx
                if row.get("provenance")
            }
            | {f"ontology:{row['path']}" for row in ontology_ctx}
        )
        self.memory.add(
            "episodic",
            f"Task: {task}\nOutcome: {answer[:4000]}",
            provenance=f"brain-run:{run_id}",
            metadata={"agents": sorted(outputs), "provenance": provenance},
        )

        return BrainResult(
            answer=answer,
            run_id=run_id,
            agents=sorted(outputs),
            ontology_context=ontology_ctx,
            memory_context=memory_ctx,
            critique=critique,
            provenance=provenance,
        )
