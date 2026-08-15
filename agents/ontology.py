"""A small formal ontology for agent task execution.

Instead of the planner producing freeform numbered-list prose, it's asked
to produce a typed graph conforming to this schema: a Task has ordered
Steps, each Step may produce an Artifact and must satisfy zero or more
Constraints, and is assigned to an Agent role. This makes planning
structured, checkable data instead of just text an executor re-parses by
eyeballing numbers.

Deliberately NOT using a heavy OWL/RDF stack — local 7B-class models are
unreliable at strict formats (observed elsewhere in this codebase: extra
prose corrupting numbered-list parsing, malformed JSON from a hosted
builder). This is a plain JSON Schema, validated by hand (no jsonschema
dependency), with the caller expected to fall back to legacy free-text
planning if the model can't produce valid ontology JSON.
"""
from __future__ import annotations

VALID_AGENT_ROLES = {"planner", "executor", "reviewer", "subagent"}

TASK_GRAPH_SCHEMA_DESCRIPTION = """Respond with ONLY a JSON object (no prose, no markdown fences) matching this shape:
{
  "task": "<restatement of the overall task>",
  "steps": [
    {
      "id": "s1",
      "description": "<concrete, actionable description of this step>",
      "assigned_agent": "executor",
      "produces": "<short description of the artifact/output this step yields>",
      "constraints": ["<any specific requirement this step's output must satisfy>"],
      "requires_subagent": false
    }
  ]
}
Rules: 3-6 steps. assigned_agent is always "executor" unless the step is complex enough to need its own nested agent chain, in which case set requires_subagent to true. constraints may be an empty list. Output nothing except this JSON object."""


class OntologyError(ValueError):
    pass


def validate_task_graph(data):
    """Validates a parsed task-graph dict against the schema. Raises
    OntologyError with a specific reason on any violation. Returns the
    same dict (not a copy) if valid, for convenient chaining."""
    if not isinstance(data, dict):
        raise OntologyError("task graph must be a JSON object")
    if "task" not in data or not isinstance(data["task"], str):
        raise OntologyError("missing or non-string 'task'")
    if "steps" not in data or not isinstance(data["steps"], list) or not data["steps"]:
        raise OntologyError("'steps' must be a non-empty array")

    seen_ids = set()
    for i, step in enumerate(data["steps"]):
        if not isinstance(step, dict):
            raise OntologyError(f"step {i} is not an object")
        for field in ("id", "description"):
            if field not in step or not isinstance(step[field], str) or not step[field].strip():
                raise OntologyError(f"step {i} missing valid '{field}'")
        if step["id"] in seen_ids:
            raise OntologyError(f"duplicate step id '{step['id']}'")
        seen_ids.add(step["id"])

        role = step.get("assigned_agent", "executor")
        if role not in VALID_AGENT_ROLES:
            raise OntologyError(f"step {step['id']} has invalid assigned_agent '{role}'")
        step["assigned_agent"] = role

        step.setdefault("produces", "")
        if not isinstance(step["produces"], str):
            raise OntologyError(f"step {step['id']} 'produces' must be a string")

        step.setdefault("constraints", [])
        if not isinstance(step["constraints"], list) or not all(isinstance(c, str) for c in step["constraints"]):
            raise OntologyError(f"step {step['id']} 'constraints' must be a list of strings")

        step.setdefault("requires_subagent", False)
        if not isinstance(step["requires_subagent"], bool):
            raise OntologyError(f"step {step['id']} 'requires_subagent' must be a boolean")

    return data


def extract_json_object(text):
    """Best-effort extraction of the first top-level {...} JSON object
    from arbitrary model output (which may include prose/fences around
    it). Returns the raw substring, or raises OntologyError."""
    start = text.find("{")
    if start == -1:
        raise OntologyError("no '{' found in output")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise OntologyError("no matching closing '}' found (likely truncated output)")
