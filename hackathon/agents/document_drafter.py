"""
Agent #2 — Doug Document Drafter (Professional Agents Track)

Autonomous legal/contract review agent for small businesses.
Reads contracts, flags risky clauses, suggests edits, generates summary.

Free deployment:
  - Streamlit Cloud (free hosting)
  - GitHub Pages (free)
  - Local machine
  - HuggingFace Spaces (free)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

SYSTEM_PROMPT = """You are Doug Document Drafter, an autonomous contract review agent for small businesses.

Process:
1. User uploads a contract (PDF, DOCX, or text)
2. You read and extract all clauses
3. You flag risky clauses using:
   - Zyra compliance check (jurisdiction-aware)
   - Knowledge base search for known contract risks
4. You suggest edits for each risky clause
5. You generate a 1-page summary for the lawyer
6. You only surface the user when there's an ambiguous clause needing their input

You do NOT give legal advice. You flag risks and suggest the user consult a lawyer.
"""


RISKY_CLAUSE_INDICATORS = [
    "indemnify", "liability", "termination", "non-compete",
    "arbitration", "governing law", "warranty", "breach",
    "penalty", "liquidated damages", "intellectual property",
    "confidentiality", "exclusivity", "auto-renewal",
]


def review_contract(text: str, jurisdiction: str = "US-NY") -> dict:
    """Review a contract for risky clauses.
    
    Args:
        text: Contract text
        jurisdiction: Legal jurisdiction
    
    Returns:
        Review with flagged clauses, risk assessment, and summary
    """
    from hackathon.strands_tools import compliance_check, knowledge_search
    
    # Split into clauses (simplified: split by numbered sections or paragraphs)
    import re
    clauses = re.split(r'(?=\d+\.\s|\([a-z]\)\s|\n[A-Z][A-Z][A-Z])', text)
    clauses = [c.strip() for c in clauses if c.strip() and len(c.strip()) > 20]
    
    findings = []
    for i, clause in enumerate(clauses):
        clause_lower = clause.lower()
        for indicator in RISKY_CLAUSE_INDICATORS:
            if indicator in clause_lower:
                # Check compliance
                comp = compliance_check(f"Contract clause about {indicator}", jurisdiction)
                
                # Search knowledge base
                kb = knowledge_search(f"contract risk {indicator}", top_n=1)
                
                severity = "HIGH" if indicator in ("indemnify", "liability", "non-compete", "penalty") else "MEDIUM"
                
                finding = {
                    "clause_number": i + 1,
                    "indicator": indicator,
                    "severity": severity,
                    "clause_preview": clause[:150],
                    "compliance": comp,
                    "knowledge_match": kb.get("results", [{}])[0].get("summary", "") if kb.get("results") else "",
                    "suggestion": f"Review this {indicator} clause with a lawyer. May contain unfavorable terms.",
                }
                findings.append(finding)
                break  # One indicator per clause
    
    # Generate summary
    critical_findings = [f for f in findings if f["severity"] == "HIGH"]
    needs_lawyer = len(critical_findings) > 0
    
    return {
        "total_clauses": len(clauses),
        "flagged_clauses": len(findings),
        "critical_findings": len(critical_findings),
        "needs_lawyer": needs_lawyer,
        "summary": f"Contract has {len(clauses)} clauses. {len(findings)} flagged for review. {len(critical_findings)} need immediate lawyer review.",
        "findings": findings[:15],
        "recommendation": "CONSULT_LAWYER" if needs_lawyer else "LOW_RISK",
    }


if __name__ == "__main__":
    sample_contract = """
    1. This agreement is between Company A and Company B.
    2. Company A shall indemnify Company B against all claims.
    3. Either party may terminate this agreement with 30 days notice.
    4. This agreement includes a non-compete clause for 5 years.
    5. All disputes shall be resolved through arbitration in Delaware.
    6. Company A grants Company B an exclusive license to the software.
    """
    result = review_contract(sample_contract)
    print(json.dumps(result, indent=2))
