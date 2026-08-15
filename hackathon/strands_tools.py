"""
Strands Agents SDK integration for GPT Doug.

Wraps existing gpt-doug-llm modules as Strands tools so they can be
used by any Strands agent. This file is the bridge between our existing
security stack and the Strands framework.

Install:
  pip install strands-agents

Usage:
  from strands import Agent
  from hackathon.strands_tools import zyra_inspect, sentinel_scan, golden_shield_check

  agent = Agent(tools=[zyra_inspect, sentinel_scan, golden_shield_check])
  agent("Scan my system for vulnerabilities")
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root to path so we can import existing modules
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# ── Tool definitions for Strands SDK ───────────────────────────────────────
# Each function is decorated as a Strands tool. If strands is not installed,
# the decorators are no-ops so the code still works for testing.

try:
    from strands import tool as strands_tool
except ImportError:
    # Fallback: no-op decorator if Strands SDK not installed
    def strands_tool(func=None, **kwargs):
        if func is None:
            return lambda f: f
        return func


@strands_tool(description="Inspect text for security threats using Zyra 3.0 watchdog. Returns verdict with risk level, classification, and RICE signals.")
def zyra_inspect(text: str, direction: str = "input") -> dict:
    """Run Zyra inspection on text.
    
    Args:
        text: The text to inspect
        direction: "input" or "output"
    
    Returns:
        Verdict dict with allowed, risk, reasons, classification, rice_signals
    """
    from zyra import Zyra
    zyra = Zyra()
    verdict = zyra.inspect(text, direction)
    return {
        "allowed": verdict.allowed,
        "risk": verdict.risk,
        "reasons": verdict.reasons,
        "classification": verdict.classification,
        "rice_signals": verdict.rice_signals,
        "requires_approval": verdict.requires_approval,
        "redacted_text": verdict.text,
    }


@strands_tool(description="Run a full security sweep: internal (ports, processes, files, DNS), external (CVE feeds), satellite (orbital assets), dark web (exposure). Returns findings.")
def sentinel_scan(scan_type: str = "full") -> dict:
    """Run Zyra Sentinel vulnerability scan.
    
    Args:
        scan_type: "full", "internal", "external", "satellite", or "darkweb"
    
    Returns:
        Scan results with findings count, critical count, and details
    """
    from golden_shield import ZyraSentinel
    sentinel = ZyraSentinel()
    
    if scan_type == "internal":
        findings = sentinel.scan_internal()
    elif scan_type == "external":
        findings = sentinel.scan_external()
    elif scan_type == "satellite":
        findings = sentinel.scan_satellite()
    elif scan_type == "darkweb":
        findings = sentinel.scan_darkweb_exposure()
    else:
        report = sentinel.full_sweep()
        return {
            "scan_id": report.scan_id,
            "total_findings": report.total_findings,
            "critical_count": report.critical_count,
            "planetary_count": report.planetary_count,
            "internal": len(report.internal_findings),
            "external": len(report.external_findings),
            "satellite": len(report.satellite_findings),
            "darkweb": len(report.darkweb_findings),
            "duration_seconds": report.duration_seconds,
        }
    
    return {
        "scan_type": scan_type,
        "findings_count": len(findings),
        "critical_count": sum(1 for f in findings if f.severity in ("CRITICAL", "HIGH")),
        "findings": [
            {
                "severity": f.severity,
                "category": f.category,
                "target": f.target,
                "description": f.description,
                "recommendation": f.recommendation,
            }
            for f in findings[:20]
        ],
    }


@strands_tool(description="Check inbound request through Golden Shield perimeter defense. Eliminates threats, blocks attacks, rate-limits floods. Returns assessment.")
def golden_shield_check(text: str, source: str = "user") -> dict:
    """Run Golden Shield inspection on inbound request.
    
    Args:
        text: The request text
        source: Source identifier (for rate limiting)
    
    Returns:
        Assessment with action (ALLOW/QUARANTINE/BLOCK/ELIMINATE), risk level, reason
    """
    from golden_shield import GoldenShield
    shield = GoldenShield()
    assessment = shield.inspect_inbound(text, source)
    return {
        "action": assessment.action,
        "risk_level": assessment.risk_level,
        "reason": assessment.reason,
        "rate_limited": assessment.rate_limited,
        "classification": assessment.classification,
        "rice_signals": assessment.rice_signals,
        "threat_signals": assessment.threat_signals,
        "fingerprint": assessment.fingerprint[:12],
    }


@strands_tool(description="Search the knowledge base for relevant entries. Returns attributed, summarized knowledge matching the query.")
def knowledge_search(query: str, top_n: int = 5) -> dict:
    """Search the GPT Doug knowledge base.
    
    Args:
        query: Search query
        top_n: Maximum results to return
    
    Returns:
        Matching knowledge entries with confidence scores
    """
    from ontology import Ontology
    links = Ontology.task_knowledge("search", query, top_n=top_n)
    entries = {e["id"]: e for e in Ontology.knowledge()}
    results = []
    for link in links:
        entry = entries.get(link["to"][1])
        if entry:
            results.append({
                "id": entry.get("id"),
                "topic": entry.get("topic"),
                "attribution": entry.get("attribution"),
                "summary": entry.get("summary"),
                "confidence": link.get("confidence"),
                "matched_keywords": link.get("matched_keywords"),
            })
    return {"query": query, "results_count": len(results), "results": results}


@strands_tool(description="Submit a task to the agent daemon queue. The task will be picked up by the worker daemon and processed through the planner->executor->reviewer chain. Zyra-gated.")
def submit_task(task_id: str, prompt: str) -> dict:
    """Submit a task to the agent daemon.
    
    Args:
        task_id: Unique task identifier
        prompt: Task description
    
    Returns:
        Submission result with task path
    """
    from ontology import Ontology
    try:
        result = Ontology.submit_task(task_id, prompt)
        return {"status": "submitted", "task_id": task_id, "path": result.get("path")}
    except Exception as e:
        return {"status": "rejected", "reason": str(e)}


@strands_tool(description="Run the multi-agent chain: planner breaks down task, executor does the work, reviewer checks quality. Returns full trace.")
def agent_chain_run(task: str, max_depth: int = 4) -> dict:
    """Run the multi-agent task chain.
    
    Args:
        task: Task description in plain language
        max_depth: Maximum sub-agent spawning depth
    
    Returns:
        Full trace with planner, executor, and reviewer outputs
    """
    sys.path.insert(0, str(_PROJECT_ROOT / "agents"))
    try:
        import agent_chain
        trace = agent_chain.run(task)
        return {
            "run_id": trace.get("run_id"),
            "status": trace.get("status", "completed"),
            "steps": len(trace.get("steps", [])),
            "transcript_length": len(trace.get("transcript", "")),
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}


@strands_tool(description="Check compliance for a given request against jurisdiction-aware policy. Blocks autonomous weapons, social scoring, protected-trait inference.")
def compliance_check(request: str, jurisdiction: str = "US-NY") -> dict:
    """Check request against compliance gate.
    
    Args:
        request: The request to check
        jurisdiction: Jurisdiction code (e.g. US-NY, EU-DE)
    
    Returns:
        Compliance decision with allowed, reason, requires_review
    """
    from compliance import ComplianceGate, UserContext
    os.environ["GPT_DOUG_JURISDICTION"] = jurisdiction
    context = UserContext.from_environment()
    gate = ComplianceGate(context)
    decision = gate.inspect(request)
    return {
        "allowed": decision.allowed,
        "reason": decision.reason,
        "requires_review": decision.requires_review,
        "jurisdiction": jurisdiction,
    }


@strands_tool(description="Sterilize output through Golden Shield. Removes command injection, path disclosure, env var leaks, privilege escalation suggestions from model output.")
def sterilize_output(text: str) -> dict:
    """Run Golden Shield output sterilization.
    
    Args:
        text: Output text to sterilize
    
    Returns:
        Sterilized text and any threat signals found
    """
    from golden_shield import GoldenShield
    shield = GoldenShield()
    assessment = shield.inspect_outbound(text, "model")
    safe_text = assessment.zyra_verdict.text if assessment.zyra_verdict else text
    return {
        "action": assessment.action,
        "safe_text": safe_text,
        "threat_signals": assessment.threat_signals,
        "original_length": len(text),
        "sterilized": safe_text != text,
    }


# ── List all available tools ────────────────────────────────────────────────

AVAILABLE_TOOLS = [
    zyra_inspect,
    sentinel_scan,
    golden_shield_check,
    knowledge_search,
    submit_task,
    agent_chain_run,
    compliance_check,
    sterilize_output,
]

def get_all_tools():
    """Return all available Strands tools for agent creation."""
    return AVAILABLE_TOOLS
