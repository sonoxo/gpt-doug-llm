from __future__ import annotations


def explain(subject: str) -> dict:
    clean = subject.strip()
    if not clean:
        raise ValueError("subject is required")
    return {
        "subject": clean,
        "format": "60_SECOND_EXPLAINER",
        "beats": [
            {"beat": "HOOK", "script": f"Most teams make {clean} harder than it needs to be."},
            {"beat": "WHAT", "script": f"{clean} is handled as one visible VA3LM workflow instead of disconnected steps."},
            {"beat": "HOW", "script": "Architect, coder, ontology, test, security, review, and evidence agents each handle a defined lane."},
            {"beat": "PROOF", "script": "Tests, security checks, ontology links, and evidence records show what happened before a build is approved."},
            {"beat": "BENEFIT", "script": "You move faster while keeping the work understandable, reviewable, and repeatable."},
            {"beat": "CTA", "script": "Open VA3LM on port 8088, give it a coding goal, and watch the workflow build itself."},
        ],
        "visuals": [
            "problem headline", "goal enters VA3LM", "agents light up in sequence",
            "tests and security turn green", "approval gate", "verified build card",
        ],
    }
