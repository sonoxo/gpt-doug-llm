from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class AgentEvent:
    kind: str
    data: Any


@dataclass
class AgentResult:
    completed: bool
    answer: str
    events: List[AgentEvent] = field(default_factory=list)


class AgenticDoug:
    """
    Ontology-first autonomous loop.

    FLOW:
    GOAL
      -> RETRIEVE ONTOLOGY
      -> REASON
      -> ACT / PROPOSE
      -> VERIFY
      -> REPLAN
      -> FINISH

    Trusted ontology is never mutated directly.
    New knowledge goes through the proposal callback.
    """

    def __init__(
        self,
        retrieve: Callable[[str], Any],
        reason: Callable[[str, Any, List[AgentEvent]], Dict[str, str]],
        act: Callable[[str], str],
        verify: Callable[[str, str], bool],
        propose: Callable[[str], str],
        max_steps: int = 8,
    ) -> None:
        self.retrieve = retrieve
        self.reason = reason
        self.act = act
        self.verify = verify
        self.propose = propose
        self.max_steps = max_steps

    def run(self, goal: str) -> AgentResult:
        history: List[AgentEvent] = []

        for _ in range(self.max_steps):
            # Ontology is consulted before every decision.
            context = self.retrieve(goal)
            history.append(AgentEvent("ontology_retrieval", context))

            decision = self.reason(goal, context, history)
            action = decision.get("action", "").lower()
            payload = decision.get("input", "")

            history.append(AgentEvent("decision", decision))

            if action == "finish":
                return AgentResult(True, payload, history)

            if action == "propose":
                proposal_id = self.propose(payload)
                history.append(
                    AgentEvent(
                        "ontology_proposal",
                        {"id": proposal_id, "content": payload},
                    )
                )
                continue

            if action == "tool":
                output = self.act(payload)
                history.append(
                    AgentEvent("tool_result", {"input": payload, "output": output})
                )

                passed = self.verify(payload, output)
                history.append(
                    AgentEvent("verification", {"passed": passed})
                )
                continue

            history.append(
                AgentEvent("error", "Unknown action: {}".format(action))
            )

        return AgentResult(
            False,
            "Maximum agent steps reached before verification.",
            history,
        )
