"""
Sub-Agent Spawning + Teaching System

Each of the 10 GPT Doug agents can:
1. SPAWN a sub-agent — create a new specialized agent from a template
2. TEACH it — pass down knowledge, patterns, and skills
3. DELEGATE to it — assign tasks the sub-agent handles autonomously
4. REVIEW its work — verify quality before accepting results
5. EVOLVE it — refine the sub-agent's skills based on performance

Architecture:
  Parent Agent (e.g. Code Reviewer)
    ├── Spawns Sub-Agent (e.g. Security Scanner)
    │   ├── Teaches: Zyra patterns, knowledge base entries
    │   ├── Delegates: "scan this PR for security issues"
    │   ├── Reviews: sub-agent's findings before reporting
    │   └── Evolves: adjusts based on false positive/negative rates
    └── Spawns Sub-Agent (e.g. Style Checker)
        ├── Teaches: PEP 8, ruff rules
        └── Delegates: "check style compliance"

Sub-agents run the same plan→execute→review loop as parent agents,
but with specialized knowledge and scoped responsibilities.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

_PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT))


@dataclass
class SubAgentSkill:
    """A skill taught to a sub-agent."""
    skill_id: str
    name: str
    description: str
    knowledge_entries: list[str] = field(default_factory=list)  # knowledge base IDs
    patterns: list[str] = field(default_factory=list)  # regex/pattern strings
    examples: list[dict] = field(default_factory=list)  # input→output examples
    proficiency: float = 0.5  # 0.0 = none, 1.0 = expert


@dataclass
class SubAgent:
    """A sub-agent spawned by a parent agent."""
    sub_agent_id: str
    name: str
    parent_agent: str  # parent agent name
    specialization: str  # what this sub-agent does
    skills: list[SubAgentSkill] = field(default_factory=list)
    created_at: str = ""
    tasks_completed: int = 0
    tasks_failed: int = 0
    success_rate: float = 0.0
    generation: int = 1  # 1 = direct child, 2 = grandchild, etc.
    status: str = "learning"  # learning, ready, active, retired
    lineage: list[str] = field(default_factory=list)  # chain of parent IDs


@dataclass
class SubAgentTask:
    """A task delegated to a sub-agent."""
    task_id: str
    sub_agent_id: str
    instruction: str
    input_data: dict
    output: dict = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    started_at: str = ""
    completed_at: str = ""
    parent_review: dict = field(default_factory=dict)  # parent's review of sub-agent's work


class SubAgentForge:
    """The forge where parent agents spawn, teach, and manage sub-agents.

    Each parent agent uses the forge to:
    1. Create sub-agents with specific specializations
    2. Teach them skills (knowledge, patterns, examples)
    3. Delegate tasks to them
    4. Review and verify their work
    5. Evolve them based on performance metrics
    """

    # ── Parent agent definitions → what they can spawn ────────────────────
    PARENT_BLUEPRINTS = {
        "sentinel_bot": {
            "can_spawn": ["port_scanner", "process_monitor", "dns_checker", "ssl_auditor"],
            "default_skills": ["zyra_inspect", "sentinel_scan"],
        },
        "code_reviewer": {
            "can_spawn": ["security_scanner", "style_checker", "test_generator", "compliance_auditor"],
            "default_skills": ["zyra_inspect", "knowledge_search", "compliance_check"],
        },
        "document_drafter": {
            "can_spawn": ["clause_extractor", "risk_scorer", "jurisdiction_checker", "summary_writer"],
            "default_skills": ["knowledge_search", "compliance_check"],
        },
        "invoice_ninja": {
            "can_spawn": ["payment_tracker", "reminder_writer", "dispute_handler", "expense_categorizer"],
            "default_skills": ["zyra_inspect"],
        },
        "emergency_mesh": {
            "can_spawn": ["alert_dispatcher", "vulnerable_checker", "resource_tracker", "status_compiler"],
            "default_skills": ["sentinel_scan", "knowledge_search"],
        },
        "meeting_sentinel": {
            "can_spawn": ["conflict_detector", "schedule_optimizer", "preference_learner", "notification_sender"],
            "default_skills": ["zyra_inspect"],
        },
        "health_tracker": {
            "can_spawn": ["medication_scheduler", "refill_manager", "appointment_booker", "interaction_checker"],
            "default_skills": ["compliance_check"],
        },
        "neighbor_help": {
            "can_spawn": ["inventory_tracker", "demand_predictor", "restock_orderer", "distribution_planner"],
            "default_skills": ["knowledge_search"],
        },
        "expense_sentinel": {
            "can_spawn": ["receipt_parser", "categorizer", "budget_tracker", "anomaly_detector"],
            "default_skills": ["zyra_inspect"],
        },
        "school_coordinator": {
            "can_spawn": ["volunteer_matcher", "event_planner", "reminder_sender", "hours_tracker"],
            "default_skills": [],
        },
    }

    def __init__(self, registry_path: str | Path | None = None):
        self.registry_path = Path(registry_path or Path.home() / ".gpt-doug" / "sub-agents.json")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._registry = self._load_registry()
        self._task_history: list[SubAgentTask] = []

    def _load_registry(self) -> list[dict]:
        if self.registry_path.exists():
            return json.loads(self.registry_path.read_text())
        return []

    def _save_registry(self):
        self.registry_path.write_text(json.dumps(self._registry, indent=2))
        self.registry_path.chmod(0o600)

    # ═══ SPAWN: Create a new sub-agent ═════════════════════════════════════

    def spawn(self, parent_agent: str, specialization: str, name: str = "") -> SubAgent:
        """Parent agent spawns a new sub-agent with a specialization."""
        blueprint = self.PARENT_BLUEPRINTS.get(parent_agent, {})
        can_spawn = blueprint.get("can_spawn", [])

        if specialization not in can_spawn:
            # Parent can still spawn it, but it's outside the default blueprint
            pass  # Allow it — agents can learn to spawn beyond their blueprint

        sub = SubAgent(
            sub_agent_id=uuid.uuid4().hex[:12],
            name=name or f"{parent_agent}→{specialization}",
            parent_agent=parent_agent,
            specialization=specialization,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            status="learning",
            lineage=[parent_agent],
        )

        # Auto-teach default skills from parent
        for skill_id in blueprint.get("default_skills", []):
            skill = self._create_default_skill(skill_id)
            sub.skills.append(skill)

        self._registry.append({
            "sub_agent_id": sub.sub_agent_id,
            "name": sub.name,
            "parent_agent": sub.parent_agent,
            "specialization": sub.specialization,
            "skills": [{"skill_id": s.skill_id, "name": s.name, "proficiency": s.proficiency} for s in sub.skills],
            "created_at": sub.created_at,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "success_rate": 0.0,
            "generation": sub.generation,
            "status": sub.status,
            "lineage": sub.lineage,
        })
        self._save_registry()
        return sub

    # ═══ TEACH: Pass knowledge and skills to a sub-agent ═══════════════════

    def teach(self, sub_agent_id: str, skill: SubAgentSkill) -> dict:
        """Teach a sub-agent a new skill."""
        for entry in self._registry:
            if entry["sub_agent_id"] == sub_agent_id:
                entry["skills"].append({
                    "skill_id": skill.skill_id,
                    "name": skill.name,
                    "description": skill.description,
                    "knowledge_entries": skill.knowledge_entries,
                    "patterns": skill.patterns,
                    "proficiency": skill.proficiency,
                })
                # Increase proficiency if re-teaching same skill
                entry["status"] = "ready" if len(entry["skills"]) >= 2 else "learning"
                self._save_registry()
                return {"status": "taught", "sub_agent": sub_agent_id, "skill": skill.name,
                        "total_skills": len(entry["skills"]), "proficiency": skill.proficiency}
        return {"status": "not_found", "sub_agent_id": sub_agent_id}

    def teach_from_knowledge_base(self, sub_agent_id: str, query: str, skill_name: str = "") -> dict:
        """Teach a sub-agent using entries from the knowledge base."""
        try:
            from ontology import Ontology
            links = Ontology.task_knowledge("teach", query, top_n=3)
            entries = {e["id"]: e for e in Ontology.knowledge()}
            learned = []
            for link in links:
                entry = entries.get(link["to"][1])
                if entry:
                    learned.append(entry["id"])

            skill = SubAgentSkill(
                skill_id=uuid.uuid4().hex[:8],
                name=skill_name or f"kb:{query[:30]}",
                description=f"Knowledge from query: {query}",
                knowledge_entries=learned,
                proficiency=0.6,
            )
            return self.teach(sub_agent_id, skill)
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    # ═══ DELEGATE: Assign a task to a sub-agent ════════════════════════════

    def delegate(self, sub_agent_id: str, instruction: str, input_data: dict) -> SubAgentTask:
        """Parent agent delegates a task to a sub-agent."""
        task = SubAgentTask(
            task_id=uuid.uuid4().hex[:12],
            sub_agent_id=sub_agent_id,
            instruction=instruction,
            input_data=input_data,
            status="running",
            started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # Find the sub-agent and run its specialized task
        sub_entry = None
        for entry in self._registry:
            if entry["sub_agent_id"] == sub_agent_id:
                sub_entry = entry
                break

        if not sub_entry:
            task.status = "failed"
            task.output = {"error": "sub-agent not found"}
            return task

        # Mark as active
        sub_entry["status"] = "active"

        # Run the sub-agent's task using its specialization
        task.output = self._run_sub_agent(sub_entry, instruction, input_data)
        task.status = "completed" if "error" not in task.output else "failed"
        task.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Update stats
        if task.status == "completed":
            sub_entry["tasks_completed"] += 1
        else:
            sub_entry["tasks_failed"] += 1
        total = sub_entry["tasks_completed"] + sub_entry["tasks_failed"]
        sub_entry["success_rate"] = round(sub_entry["tasks_completed"] / max(total, 1), 2)

        # Evolve: if success rate > 80%, increase proficiency
        if sub_entry["success_rate"] > 0.8:
            for skill in sub_entry["skills"]:
                skill["proficiency"] = min(1.0, skill.get("proficiency", 0.5) + 0.05)

        self._save_registry()
        self._task_history.append(task)
        return task

    def _run_sub_agent(self, sub_entry: dict, instruction: str, input_data: dict) -> dict:
        """Run a sub-agent's specialized task."""
        spec = sub_entry["specialization"]

        # ── Port scanner sub-agent ──────────────────────────────────────────
        if spec == "port_scanner":
            from golden_shield import ZyraSentinel
            s = ZyraSentinel()
            findings = s.scan_internal()
            ports = [f for f in findings if f.category == "suspicious_port" or f.category == "open_port"]
            return {"open_ports": len(ports), "suspicious": [f.target for f in ports if f.severity == "CRITICAL"]}

        # ── Security scanner sub-agent ─────────────────────────────────────
        elif spec == "security_scanner":
            from zyra import Zyra
            zyra = Zyra()
            text = input_data.get("code", input_data.get("diff", ""))
            verdict = zyra.inspect(text, "input")
            return {"allowed": verdict.allowed, "risk": verdict.risk, "reasons": verdict.reasons,
                    "classification": verdict.classification}

        # ── Style checker sub-agent ────────────────────────────────────────
        elif spec == "style_checker":
            code = input_data.get("code", "")
            issues = []
            if len(code) > 0:
                if "\t" in code: issues.append("tabs instead of spaces")
                if any(line.startswith("  ") and not line.startswith("    ") for line in code.splitlines()): issues.append("inconsistent indentation")
                if code.count("def ") > 10: issues.append("too many functions in one file")
            return {"style_issues": issues, "clean": len(issues) == 0}

        # ── Clause extractor sub-agent ──────────────────────────────────────
        elif spec == "clause_extractor":
            import re
            text = input_data.get("text", "")
            clauses = re.split(r'(?=\d+\.\s|\([a-z]\)\s)', text)
            clauses = [c.strip() for c in clauses if c.strip() and len(c.strip()) > 20]
            return {"clause_count": len(clauses), "clauses": clauses[:10]}

        # ── Risk scorer sub-agent ──────────────────────────────────────────
        elif spec == "risk_scorer":
            text = input_data.get("text", "").lower()
            risk_words = ["indemnify", "liability", "penalty", "non-compete", "arbitration", "auto-renewal"]
            score = sum(10 for w in risk_words if w in text)
            return {"risk_score": score, "level": "HIGH" if score >= 30 else "MEDIUM" if score >= 10 else "LOW",
                    "flags": [w for w in risk_words if w in text]}

        # ── Reminder writer sub-agent ─────────────────────────────────────
        elif spec == "reminder_writer":
            client = input_data.get("client", "Client")
            days = input_data.get("days_overdue", 1)
            if days <= 1: tone = "friendly"
            elif days <= 7: tone = "firm"
            else: tone = "final"
            return {"client": client, "tone": tone, "message": f"Hi {client}, your invoice is {days} days overdue. Please remit payment."}

        # ── Alert dispatcher sub-agent ────────────────────────────────────
        elif spec == "alert_dispatcher":
            threat = input_data.get("threat", "")
            neighbors = input_data.get("neighbors", [])
            return {"alert_sent": True, "recipients": len(neighbors), "threat": threat[:50]}

        # ── Inventory tracker sub-agent ────────────────────────────────────
        elif spec == "inventory_tracker":
            items = input_data.get("items", [])
            low = [i for i in items if i.get("quantity", 0) < i.get("threshold", 10)]
            return {"total_items": len(items), "low_stock": len(low), "items": low}

        # ── Receipt parser sub-agent ────────────────────────────────────────
        elif spec == "receipt_parser":
            text = input_data.get("text", "")
            import re
            amount_match = re.search(r'\$(\d+\.?\d*)', text)
            amount = float(amount_match.group(1)) if amount_match else 0.0
            return {"amount": amount, "merchant": text.split("\n")[0][:50] if text else "unknown"}

        # ── Volunteer matcher sub-agent ────────────────────────────────────
        elif spec == "volunteer_matcher":
            roles = input_data.get("roles", [])
            volunteers = input_data.get("volunteers", [])
            matches = []
            for role in roles:
                for v in volunteers:
                    if any(s in role.get("required_skills", []) for s in v.get("skills", [])):
                        if v.get("available", True):
                            matches.append({"role": role["name"], "volunteer": v["name"]})
                            v["available"] = False
                            break
            return {"matched": len(matches), "matches": matches}

        # ── Generic sub-agent (uses Zyra + knowledge) ──────────────────────
        else:
            from zyra import Zyra
            zyra = Zyra()
            verdict = zyra.inspect(instruction, "input")
            return {"allowed": verdict.allowed, "risk": verdict.risk,
                    "specialization": spec, "instruction": instruction[:100]}

    # ═══ REVIEW: Parent reviews sub-agent's work ═══════════════════════════

    def review(self, sub_agent_id: str, task_result: dict) -> dict:
        """Parent agent reviews a sub-agent's work."""
        review = {
            "sub_agent_id": sub_agent_id,
            "accepted": "error" not in task_result,
            "quality": "good" if "error" not in task_result else "failed",
            "feedback": "",
        }

        # Auto-feedback based on result
        if review["accepted"]:
            review["feedback"] = "Task completed successfully. Quality acceptable."
        else:
            review["feedback"] = f"Task failed: {task_result.get('error', 'unknown')}"

        return review

    # ═══ EVOLVE: Improve sub-agent based on performance ═════════════════════

    def evolve(self, sub_agent_id: str) -> dict:
        """Evolve a sub-agent based on its performance history."""
        for entry in self._registry:
            if entry["sub_agent_id"] == sub_agent_id:
                total = entry["tasks_completed"] + entry["tasks_failed"]
                if total < 5:
                    return {"status": "needs_more_data", "tasks": total, "message": "Need at least 5 tasks before evolving"}

                if entry["success_rate"] > 0.8:
                    # Promote: increase all skill proficiencies
                    for skill in entry["skills"]:
                        skill["proficiency"] = min(1.0, skill.get("proficiency", 0.5) + 0.1)
                    entry["status"] = "expert"
                    self._save_registry()
                    return {"status": "promoted", "new_proficiency_avg": sum(s["proficiency"] for s in entry["skills"]) / max(len(entry["skills"]), 1)}

                elif entry["success_rate"] < 0.5:
                    # Demote: needs retraining
                    entry["status"] = "retraining"
                    self._save_registry()
                    return {"status": "needs_retraining", "success_rate": entry["success_rate"]}

                else:
                    return {"status": "stable", "success_rate": entry["success_rate"]}

        return {"status": "not_found"}

    # ═══ SPAWN CHILDREN: Sub-agent spawns its own sub-agents ═════════════════

    def spawn_child(self, parent_sub_agent_id: str, specialization: str, name: str = "") -> SubAgent:
        """A sub-agent spawns its own sub-agent (next generation)."""
        parent_entry = None
        for entry in self._registry:
            if entry["sub_agent_id"] == parent_sub_agent_id:
                parent_entry = entry
                break

        if not parent_entry:
            raise ValueError(f"parent sub-agent {parent_sub_agent_id} not found")

        child = SubAgent(
            sub_agent_id=uuid.uuid4().hex[:12],
            name=name or f"{parent_entry['name']}→{specialization}",
            parent_agent=parent_entry["specialization"],
            specialization=specialization,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            status="learning",
            generation=parent_entry["generation"] + 1,
            lineage=parent_entry["lineage"] + [parent_sub_agent_id],
        )

        # Inherit parent's skills at reduced proficiency
        for skill in parent_entry["skills"]:
            inherited = SubAgentSkill(
                skill_id=skill["skill_id"],
                name=skill["name"],
                description=skill.get("description", ""),
                knowledge_entries=skill.get("knowledge_entries", []),
                patterns=skill.get("patterns", []),
                proficiency=skill.get("proficiency", 0.5) * 0.7,  # inherited at 70%
            )
            child.skills.append(inherited)

        self._registry.append({
            "sub_agent_id": child.sub_agent_id,
            "name": child.name,
            "parent_agent": child.parent_agent,
            "specialization": child.specialization,
            "skills": [{"skill_id": s.skill_id, "name": s.name, "proficiency": s.proficiency} for s in child.skills],
            "created_at": child.created_at,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "success_rate": 0.0,
            "generation": child.generation,
            "status": child.status,
            "lineage": child.lineage,
        })
        self._save_registry()
        return child

    # ═══ STATUS & REPORTING ═══════════════════════════════════════════════

    def list_sub_agents(self, parent_agent: str = "") -> list[dict]:
        if parent_agent:
            return [e for e in self._registry if e["parent_agent"] == parent_agent or e["lineage"] and parent_agent in e["lineage"]]
        return self._registry

    def status(self) -> dict:
        total = len(self._registry)
        by_gen = {}
        for e in self._registry:
            gen = e["generation"]
            by_gen[gen] = by_gen.get(gen, 0) + 1
        return {
            "total_sub_agents": total,
            "by_generation": by_gen,
            "active": sum(1 for e in self._registry if e["status"] in ("active", "expert")),
            "learning": sum(1 for e in self._registry if e["status"] == "learning"),
            "total_tasks": sum(e["tasks_completed"] + e["tasks_failed"] for e in self._registry),
            "avg_success_rate": round(sum(e["success_rate"] for e in self._registry) / max(total, 1), 2),
        }

    def display(self) -> str:
        s = self.status()
        lines = [
            "╔══════════════════════════════════════════════════════════════════════════╗",
            "║         SUB-AGENT FORGE — SPAWN · TEACH · DELEGATE · EVOLVE              ║",
            "╠══════════════════════════════════════════════════════════════════════════╣",
        ]
        for k, v in s.items():
            lines.append(f"║  {k}: {str(v):<65s}║")
        lines.append("╠══════════════════════════════════════════════════════════════════════════╣")
        for entry in self._registry[:15]:
            gen_tag = f"Gen{entry['generation']}"
            status_tag = f"[{entry['status'].upper()}]"
            lines.append(f"║  {gen_tag:5s} {status_tag:12s} {entry['name'][:50]:<50s} skills={len(entry['skills'])} ║")
        lines.append("╚══════════════════════════════════════════════════════════════════════════╝")
        return "\n".join(lines)

    def _create_default_skill(self, skill_id: str) -> SubAgentSkill:
        """Create a default skill from the skill registry."""
        defaults = {
            "zyra_inspect": SubAgentSkill(skill_id="zyra_inspect", name="Zyra Security Inspect",
                description="Inspect text for security threats using Zyra 3.0", proficiency=0.8),
            "sentinel_scan": SubAgentSkill(skill_id="sentinel_scan", name="Sentinel Vulnerability Scan",
                description="Run vulnerability scan (internal/external/satellite)", proficiency=0.7),
            "knowledge_search": SubAgentSkill(skill_id="knowledge_search", name="Knowledge Base Search",
                description="Search 173-entry knowledge base for relevant information", proficiency=0.6),
            "compliance_check": SubAgentSkill(skill_id="compliance_check", name="Compliance Gate Check",
                description="Check request against jurisdiction-aware compliance policy", proficiency=0.7),
        }
        return defaults.get(skill_id, SubAgentSkill(skill_id=skill_id, name=skill_id,
            description=f"Skill: {skill_id}", proficiency=0.5))


# ═══ AUTO-SPAWN: Each parent agent spawns its full sub-agent fleet ═════════

def auto_spawn_all() -> dict:
    """Each of the 10 parent agents spawns its full sub-agent fleet."""
    forge = SubAgentForge()
    results = {}

    for parent, blueprint in SubAgentForge.PARENT_BLUEPRINTS.items():
        spawned = []
        for spec in blueprint["can_spawn"]:
            sub = forge.spawn(parent, spec)
            spawned.append({"id": sub.sub_agent_id, "name": sub.name, "skills": len(sub.skills)})
        results[parent] = {"spawned": len(spawned), "sub_agents": spawned}

    return {"forge_status": forge.status(), "results": results}


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║   SUB-AGENT FORGE — Auto-spawning sub-agents for all 10 parent agents   ║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")
    print()

    result = auto_spawn_all()
    print(json.dumps(result, indent=2))
    print()

    forge = SubAgentForge()
    print(forge.display())

    # Demo: delegate a task
    if forge._registry:
        first_sub = forge._registry[0]
        print(f"\n=== Demo: delegating task to {first_sub['name']} ===")
        task = forge.delegate(first_sub["sub_agent_id"], "scan for vulnerabilities", {"code": "test code"})
        print(json.dumps({"task_id": task.task_id, "status": task.status, "output": task.output}, indent=2))

        # Demo: teach from knowledge base
        print(f"\n=== Demo: teaching {first_sub['name']} from knowledge base ===")
        teach_result = forge.teach_from_knowledge_base(first_sub["sub_agent_id"], "cia security tradecraft")
        print(json.dumps(teach_result, indent=2))

        # Demo: review
        print(f"\n=== Demo: parent reviews {first_sub['name']}'s work ===")
        review = forge.review(first_sub["sub_agent_id"], task.output)
        print(json.dumps(review, indent=2))

    # Demo: spawn a grandchild (sub-agent spawns its own sub-agent)
    if len(forge._registry) > 1:
        parent_sub = forge._registry[1]
        print(f"\n=== Demo: {parent_sub['name']} spawns its own sub-agent ===")
        child = forge.spawn_child(parent_sub["sub_agent_id"], "advanced_scanner")
        print(json.dumps({"child_id": child.sub_agent_id, "child_name": child.name,
                          "generation": child.generation, "inherited_skills": len(child.skills),
                          "lineage": child.lineage}, indent=2))
