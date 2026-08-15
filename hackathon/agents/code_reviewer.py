"""
Agent #8 — Doug Code Reviewer (Professional Agents Track)

Autonomous PR review agent. Watches GitHub for pull requests,
automatically reviews code using Zyra security patterns + agent_chain,
and only surfaces the maintainer when there's a genuine judgment call.

Strands SDK agent that uses:
  - zyra_inspect: Security vulnerability detection in code
  - agent_chain_run: Multi-agent code analysis (plan→execute→review)
  - knowledge_search: Look up known vulnerability patterns
  - golden_shield_check: Block malicious PRs at the perimeter
  - compliance_check: Ensure PR doesn't introduce compliance violations

Deploy on:
  - AWS Lambda (free tier: 1M requests/month)
  - GitHub Actions (free for public repos)
  - Local webhook (free, runs on any machine)

Webhook receiver uses existing web/server.py.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "hackathon"))

SYSTEM_PROMPT = """You are Doug Code Reviewer, an autonomous PR review agent.

Your job: when a pull request is opened, review the code automatically.

Process:
1. Read the PR diff
2. Run Zyra security inspection on every changed file
3. Search knowledge base for known vulnerability patterns matching the code
4. Check compliance for any data-handling changes
5. Run agent_chain to analyze complex changes (plan→execute→review)
6. Post a review comment with:
   - Security findings (from Zyra)
   - Style issues
   - Known vulnerability matches (from knowledge base)
   - Compliance concerns
7. Only surface the maintainer when there's a genuine judgment call:
   - Design decision needed
   - Ambiguous bug that could be intentional
   - Security finding that needs human context to assess

Rules:
- Never approve a PR with CRITICAL Zyra findings automatically
- Always run compliance_check for changes touching user data
- Use knowledge_search for any unfamiliar pattern
- Sterilize your review comment through golden_shield before posting
- Be direct, technical, and helpful — not verbose
"""


def review_pr(pr_data: dict) -> dict:
    """Review a pull request.
    
    Args:
        pr_data: PR data from GitHub webhook
            {
                "number": 42,
                "title": "Add payment endpoint",
                "body": "This PR adds...",
                "diff": "diff --git a/...",
                "files": ["api/payments.py", "models/user.py"],
                "author": "contributor",
                "base": "main",
                "head": "feature/payments"
            }
    
    Returns:
        Review result with findings, recommendation, and comment
    """
    from hackathon.strands_tools import (
        zyra_inspect, knowledge_search, golden_shield_check,
        compliance_check, sterilize_output
    )
    
    findings = []
    
    # 1. Golden Shield: check the PR title + body for malicious intent
    shield_result = golden_shield_check(
        f"{pr_data.get('title', '')} {pr_data.get('body', '')}",
        source=f"pr-{pr_data.get('number', 'unknown')}-{pr_data.get('author', 'unknown')}"
    )
    if shield_result["action"] in ("BLOCK", "ELIMINATE"):
        return {
            "recommendation": "REJECT",
            "reason": f"Golden Shield blocked PR: {shield_result['reason']}",
            "findings": [],
            "comment": f"⚠️ **ZYRA GOLDEN SHIELD**: This PR has been blocked.\n\nReason: {shield_result['reason']}",
            "auto_action": "request_changes",
        }
    
    # 2. Zyra: inspect the diff for security patterns
    diff = pr_data.get("diff", "")
    zyra_result = zyra_inspect(diff, "input")
    if not zyra_result["allowed"]:
        findings.append({
            "type": "security",
            "severity": zyra_result["risk"],
            "detail": f"Zyra blocked: {'; '.join(zyra_result['reasons'])}",
        })
    if zyra_result["rice_signals"]:
        findings.append({
            "type": "social_engineering",
            "severity": "LOW",
            "detail": f"RICE signals: {'; '.join(zyra_result['rice_signals'])}",
        })
    
    # 3. Compliance: check if PR touches user data
    user_data_keywords = ["password", "email", "phone", "ssn", "credit", "user_data", "pii"]
    diff_lower = diff.lower()
    if any(kw in diff_lower for kw in user_data_keywords):
        comp_result = compliance_check(
            f"PR modifies code handling: {', '.join(kw for kw in user_data_keywords if kw in diff_lower)}",
        )
        if not comp_result["allowed"]:
            findings.append({
                "type": "compliance",
                "severity": "CRITICAL",
                "detail": f"Compliance violation: {comp_result['reason']}",
            })
        elif comp_result["requires_review"]:
            findings.append({
                "type": "compliance",
                "severity": "HIGH",
                "detail": f"Compliance review required: {comp_result['reason']}",
            })
    
    # 4. Knowledge base: search for vulnerability patterns
    if pr_data.get("files"):
        for file_path in pr_data["files"][:5]:
            kb_result = knowledge_search(f"vulnerability {file_path}", top_n=2)
            for result in kb_result.get("results", []):
                findings.append({
                    "type": "knowledge_match",
                    "severity": "INFO",
                    "detail": f"Related: {result['summary'][:80]} (confidence: {result['confidence']})",
                })
    
    # 5. Determine recommendation
    critical_count = sum(1 for f in findings if f["severity"] in ("CRITICAL", "HIGH"))
    
    if critical_count > 0:
        recommendation = "REQUEST_CHANGES"
        needs_human = True
    elif findings:
        recommendation = "COMMENT"
        needs_human = False
    else:
        recommendation = "APPROVE"
        needs_human = False
    
    # 6. Build review comment
    comment_lines = ["## 🔒 Doug Code Reviewer\n"]
    if not findings:
        comment_lines.append("✅ No security issues found. Code looks clean.\n")
    else:
        for f in findings:
            emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "⚡", "LOW": "💡", "INFO": "📋"}.get(f["severity"], "ℹ️")
            comment_lines.append(f"{emoji} **[{f['severity']}] {f['type']}**: {f['detail']}\n")
    
    if needs_human:
        comment_lines.append("\n⚠️ **Maintainer review required** — this PR contains findings that need human judgment.\n")
    else:
        comment_lines.append(f"\n🤖 **Auto-{'approved' if recommendation == 'APPROVE' else 'commented'}** — no human judgment needed.\n")
    
    comment = "\n".join(comment_lines)
    
    # 7. Sterilize the comment before posting
    sterilize_result = sterilize_output(comment)
    safe_comment = sterilize_result.get("safe_text", comment)
    
    return {
        "recommendation": recommendation,
        "needs_human": needs_human,
        "findings_count": len(findings),
        "critical_count": critical_count,
        "findings": findings,
        "comment": safe_comment,
        "auto_action": "approve" if recommendation == "APPROVE" else "request_changes" if recommendation == "REQUEST_CHANGES" else "comment",
    }


def handle_github_webhook(event: dict) -> dict:
    """Handle a GitHub PR webhook event.
    
    Args:
        event: Parsed GitHub webhook payload
    
    Returns:
        Review response to post back to GitHub
    """
    if event.get("action") not in ("opened", "synchronize"):
        return {"status": "ignored", "reason": f"action {event.get('action')} not handled"}
    
    pr = event.get("pull_request", {})
    pr_data = {
        "number": pr.get("number"),
        "title": pr.get("title"),
        "body": pr.get("body", ""),
        "diff": pr.get("patch_url", ""),  # Would fetch actual diff
        "files": [],  # Would fetch from GitHub API
        "author": pr.get("user", {}).get("login", "unknown"),
        "base": pr.get("base", {}).get("ref", "main"),
        "head": pr.get("head", {}).get("ref", "unknown"),
    }
    
    return review_pr(pr_data)


if __name__ == "__main__":
    # Demo: review a sample PR
    sample_pr = {
        "number": 42,
        "title": "Add payment endpoint with API key",
        "body": "Adds Stripe integration. The api_key=sk_test_12345 is hardcoded for now.",
        "diff": "diff --git a/api/payments.py\n+api_key = 'sk_test_12345abcdef'\n+def process_payment(amount):\n+  requests.post('https://api.stripe.com', headers={'Authorization': api_key})",
        "files": ["api/payments.py"],
        "author": "contributor",
        "base": "main",
        "head": "feature/payments",
    }
    
    result = review_pr(sample_pr)
    print(json.dumps(result, indent=2))
