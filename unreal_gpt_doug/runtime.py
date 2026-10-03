from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_PATH = ROOT / "workers" / "knowledge" / "unreal-engine-5-8.jsonl"
SOURCES_PATH = Path(__file__).resolve().parent / "sources.json"
ONTOLOGY_PATH = Path(__file__).resolve().parent / "ontology.json"

UNREAL_TERMS = {
    "unreal", "ue5", "ue 5", "blueprint", "uobject", "uclass", "uproperty",
    "nanite", "lumen", "niagara", "metasound", "chaos", "statetree",
    "smart object", "mover", "motion matching", "pose search", "control rig",
    "world partition", "pcg", "replication", "iris", "sequencer", "horde",
    "buildgraph", "gauntlet", "unreal insights", "networked physics", "mcp"
}

class UnrealGPTDoug:
    """Source-grounded UE 5.8 knowledge profile for GPT-Doug.

    This does not retrain model weights. It injects retrieved, attributed
    Unreal knowledge into the local prompt path and exposes a deterministic
    source/ontology status surface.
    """

    def __init__(self, root: str | Path | None = None, *, enabled: bool = True) -> None:
        self.root = Path(root or ROOT).resolve()
        self.enabled = enabled
        self.entries = self._load_jsonl(self.root / "workers" / "knowledge" / "unreal-engine-5-8.jsonl")
        self.sources = json.loads((self.root / "unreal_gpt_doug" / "sources.json").read_text(encoding="utf-8"))
        self.ontology = json.loads((self.root / "unreal_gpt_doug" / "ontology.json").read_text(encoding="utf-8"))

    @staticmethod
    def _load_jsonl(path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw:
                rows.append(json.loads(raw))
        return rows

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_+.-]+", text.lower()))

    def should_ground(self, prompt: str) -> bool:
        lower = prompt.lower()
        return any(term in lower for term in UNREAL_TERMS)

    def search(self, query: str, top_n: int = 6) -> list[dict[str, Any]]:
        q = query.lower().strip()
        qtokens = self._tokens(q)
        scored = []
        for entry in self.entries:
            keyword_hits = sum(1 for kw in entry.get("keywords", []) if kw.lower() in q)
            hay = " ".join([
                entry.get("topic", ""),
                entry.get("summary", ""),
                " ".join(entry.get("keywords", [])),
            ]).lower()
            token_hits = sum(1 for tok in qtokens if tok in hay)
            exact_topic = 3 if entry.get("topic", "").lower() in q or q in entry.get("topic", "").lower() else 0
            score = keyword_hits * 4 + token_hits + exact_topic
            if score:
                scored.append((score, entry))
        scored.sort(key=lambda x: (-x[0], x[1]["id"]))
        return [dict(entry, retrieval_score=score) for score, entry in scored[:max(1, min(top_n, 12))]]

    def context_for(self, prompt: str, top_n: int = 6) -> str:
        if not self.enabled or not self.should_ground(prompt):
            return ""
        matches = self.search(prompt, top_n=top_n)
        if not matches:
            return ""
        lines = [
            "UNREAL-GPT-DOUG SOURCE-GROUNDED CONTEXT // UE 5.8",
            "Use these project knowledge entries as context. Preserve feature maturity labels and distinguish Epic first-party facts from project synthesis.",
        ]
        for e in matches:
            lines.append(
                f"- [{e['id']}] ({e['attribution']}; {e.get('feature_status','UNKNOWN')}) "
                f"{e['summary']} SOURCE={e.get('source_url','')}"
            )
        return "\n".join(lines) + "\n\n"

    def ground_prompt(self, prompt: str) -> str:
        ctx = self.context_for(prompt)
        return ctx + prompt if ctx else prompt

    def status(self) -> dict[str, Any]:
        statuses: dict[str, int] = {}
        for e in self.entries:
            statuses[e.get("feature_status", "UNKNOWN")] = statuses.get(e.get("feature_status", "UNKNOWN"), 0) + 1
        return {
            "profile": "UNREAL-GPT-DOUG",
            "enabled": self.enabled,
            "engine_target": self.ontology["engine_target"],
            "knowledge_entries": len(self.entries),
            "source_records": len(self.sources["sources"]),
            "feature_status_counts": statuses,
            "primary_authority": self.sources["policy"]["primary_authority"],
            "mcp": {
                "plugin": "ModelContextProtocol",
                "friendly_name": "Unreal MCP",
                "default_endpoint": "http://127.0.0.1:8000/mcp",
                "status": "EXPERIMENTAL_IN_UE_5_8",
                "remote_exposure": "DO_NOT_EXPOSE_TO_UNTRUSTED_NETWORKS",
            },
        }

    def source_list(self, query: str = "") -> list[dict[str, Any]]:
        if not query:
            return self.sources["sources"]
        q = query.lower()
        return [s for s in self.sources["sources"] if q in s["id"].lower() or q in s["url"].lower()]

    def mcp_guide(self) -> dict[str, Any]:
        return {
            "purpose": "Connect GPT-Doug/Codex-compatible tooling to a running Unreal Editor through Epic's experimental Unreal MCP plugin.",
            "engine_plugin_identifier": "ModelContextProtocol",
            "friendly_name": "Unreal MCP",
            "toolset_dependency": "AllToolsets",
            "endpoint": "http://127.0.0.1:8000/mcp",
            "generate_client_config": "ModelContextProtocol.GenerateClientConfig Codex",
            "generate_all_clients": "ModelContextProtocol.GenerateClientConfig All",
            "start_server": "ModelContextProtocol.StartServer",
            "boundary": [
                "Keep the server local unless you deliberately secure a remote transport.",
                "Use source control before editor mutation.",
                "Enumerate tools/capabilities before acting.",
                "Prefer reversible changes and run automation tests after mutations.",
                "The Unreal Editor/project remains the execution source of truth.",
            ],
            "source": "https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor",
        }
