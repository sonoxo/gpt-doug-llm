"""Deterministic three-way object merge with explicit unresolved conflicts."""
from copy import deepcopy
from .approval import digest

MISSING = object()


def reconcile(base, local, remote):
    for graph in (base, local, remote):
        if not isinstance(graph, dict) or any(not isinstance(k, str) or not k for k in graph):
            raise ValueError("named object maps required")
        digest(graph)  # Reject non-JSON/non-finite values before comparison.
    merged, conflicts, provenance = {}, [], {}
    for key in sorted(set(base) | set(local) | set(remote)):
        b, l, r = (g.get(key, MISSING) for g in (base, local, remote))
        if same(l, r):
            chosen, source = l, "both"
        elif same(l, b):
            chosen, source = r, "remote"
        elif same(r, b):
            chosen, source = l, "local"
        else:
            conflicts.append({"object": key, "base": entry(b), "local": entry(l), "remote": entry(r)})
            continue
        if chosen is not MISSING:
            merged[key] = deepcopy(chosen)
        provenance[key] = {"source": source, "deleted": chosen is MISSING}
    return {"status": "CONFLICT" if conflicts else "MERGED", "candidate": merged,
            "conflicts": conflicts, "provenance": provenance,
            "parents": {"base": digest(base), "local": digest(local), "remote": digest(remote)},
            "apply_allowed": not conflicts,
            "scope": "Object-level candidate only; host must validate schema, policy, and graph references."}


def entry(value):
    return {"present": value is not MISSING, "value": None if value is MISSING else value}


def same(left, right):
    if left is MISSING or right is MISSING:
        return left is right
    return digest(left) == digest(right)
