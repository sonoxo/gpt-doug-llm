"""Exact citation anchor verification and downstream invalidation; not truth scoring."""
import hashlib
from .repair import affected_nodes


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def anchor(document_id, text, start, end):
    if not isinstance(document_id, str) or not document_id or not isinstance(text, str):
        raise ValueError("document identity and text required")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        raise ValueError("invalid Unicode character offsets")
    return {"document": document_id, "sha256": text_hash(text), "start": start,
            "end": end, "quote": text[start:end]}


def verify(citation, documents):
    try:
        text = documents[citation["document"]]
        expected = anchor(citation["document"], text, citation["start"], citation["end"])
        return all(citation[k] == expected[k] for k in expected)
    except (KeyError, TypeError, ValueError):
        return False


def audit(claims, documents):
    dependencies = {key: claim.get("depends_on", []) for key, claim in claims.items()}
    direct = []
    for key, claim in claims.items():
        citations = claim.get("citations", [])
        if not isinstance(citations, list):
            raise ValueError("citations must be lists")
        if not citations or not all(verify(c, documents) for c in citations):
            direct.append(key)
    affected = affected_nodes(dependencies, direct)
    return {"direct_invalid": sorted(direct), "invalidated": affected,
            "claims": {key: "REVIEW" if key in affected else "ANCHORS_VALID"
                       for key in sorted(claims)},
            "semantic_support": "not_evaluated"}
