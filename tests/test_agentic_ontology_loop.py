from agentic import AgenticDoug


def test_ontology_is_retrieved_before_finish():
    calls = []

    def retrieve(goal):
        calls.append("ontology")
        return {"fact": "trusted"}

    def reason(goal, context, history):
        calls.append("reason")
        return {"action": "finish", "input": "done"}

    doug = AgenticDoug(
        retrieve=retrieve,
        reason=reason,
        act=lambda x: "",
        verify=lambda x, y: True,
        propose=lambda x: "unused",
    )

    result = doug.run("test")

    assert result.completed is True
    assert calls[:2] == ["ontology", "reason"]


def test_new_knowledge_becomes_proposal():
    proposals = []
    turns = {"count": 0}

    def reason(goal, context, history):
        turns["count"] += 1

        if turns["count"] == 1:
            return {"action": "propose", "input": "Doug learned a fact"}

        return {"action": "finish", "input": "proposal created"}

    def propose(fact):
        proposals.append(fact)
        return "proposal-001"

    doug = AgenticDoug(
        retrieve=lambda goal: [],
        reason=reason,
        act=lambda x: "",
        verify=lambda x, y: True,
        propose=propose,
    )

    result = doug.run("learn")

    assert result.completed is True
    assert proposals == ["Doug learned a fact"]


def test_tool_actions_are_verified():
    verified = []

    def verify(command, output):
        verified.append((command, output))
        return True

    turns = {"count": 0}

    def reason(goal, context, history):
        turns["count"] += 1

        if turns["count"] == 1:
            return {"action": "tool", "input": "what time is it"}

        return {"action": "finish", "input": "verified"}

    doug = AgenticDoug(
        retrieve=lambda goal: [],
        reason=reason,
        act=lambda command: "8:03 PM",
        verify=verify,
        propose=lambda fact: "proposal",
    )

    result = doug.run("get time")

    assert result.completed is True
    assert verified == [("what time is it", "8:03 PM")]
