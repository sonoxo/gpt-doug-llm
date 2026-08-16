"""
✓ 8/10 Agent Marketplace — create, sell, and install custom agents
Open-source marketplace where developers publish agents and earn revenue.
"""
from __future__ import annotations
import json, os, time, uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class MarketplaceAgent:
    agent_id: str
    name: str
    author: str
    description: str
    category: str  # everyday, professional, good_neighbor
    price_usd: float  # 0 = free
    rating: float = 0.0
    installs: int = 0
    created_at: str = ""
    tags: list = field(default_factory=list)
    code_path: str = ""

class AgentMarketplace:
    """Marketplace for custom GPT Doug agents. Free to list, 10% platform fee."""
    CATEGORIES = {"everyday", "professional", "good_neighbor"}
    FEE_PERCENT = 10  # platform takes 10% of paid agent sales

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir or Path.home() / ".gpt-doug" / "marketplace")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_file = self.data_dir / "catalog.json"
        self._catalog = self._load()

    def _load(self) -> list:
        if self.catalog_file.exists():
            return json.loads(self.catalog_file.read_text())
        # Seed with built-in agents
        return self._seed_catalog()

    def _seed_catalog(self) -> list:
        builtins = [
            {"agent_id": "sentinel-bot", "name": "Zyra Sentinel Bot", "author": "sonoxo",
             "description": "Home network security scanner", "category": "everyday", "price_usd": 0, "rating": 5.0, "installs": 42},
            {"agent_id": "code-reviewer", "name": "Doug Code Reviewer", "author": "sonoxo",
             "description": "Autonomous PR review with Zyra security", "category": "professional", "price_usd": 19, "rating": 4.8, "installs": 17},
            {"agent_id": "emergency-mesh", "name": "Community Emergency Mesh", "author": "sonoxo",
             "description": "Neighborhood emergency coordinator", "category": "good_neighbor", "price_usd": 0, "rating": 5.0, "installs": 8},
            {"agent_id": "invoice-ninja", "name": "Zyra Invoice Ninja", "author": "sonoxo",
             "description": "Freelancer invoice & payment chaser", "category": "professional", "price_usd": 9, "rating": 4.5, "installs": 23},
            {"agent_id": "health-tracker", "name": "Doug Health Tracker", "author": "sonoxo",
             "description": "Medication & appointment manager", "category": "everyday", "price_usd": 4, "rating": 4.2, "installs": 11},
            {"agent_id": "school-coordinator", "name": "Doug School Coordinator", "author": "sonoxo",
             "description": "PTA volunteer & event matcher", "category": "good_neighbor", "price_usd": 0, "rating": 4.0, "installs": 5},
        ]
        self._catalog = builtins
        self._save()
        return builtins

    def _save(self):
        self.catalog_file.write_text(json.dumps(self._catalog, indent=2))

    def list_agents(self, category: str = "", free_only: bool = False) -> list:
        agents = self._catalog
        if category: agents = [a for a in agents if a["category"] == category]
        if free_only: agents = [a for a in agents if a["price_usd"] == 0]
        return agents

    def publish(self, name: str, author: str, description: str, category: str, price: float, tags: list = None) -> dict:
        if category not in self.CATEGORIES:
            raise ValueError(f"category must be one of {self.CATEGORIES}")
        agent = {"agent_id": str(uuid.uuid4())[:8], "name": name, "author": author,
                "description": description, "category": category, "price_usd": price,
                "rating": 0.0, "installs": 0, "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tags": tags or []}
        self._catalog.append(agent)
        self._save()
        return agent

    def install(self, agent_id: str) -> dict:
        for a in self._catalog:
            if a["agent_id"] == agent_id:
                a["installs"] += 1
                self._save()
                return {"status": "installed", "agent": a["name"], "price": a["price_usd"],
                        "fee": round(a["price_usd"] * self.FEE_PERCENT / 100, 2) if a["price_usd"] > 0 else 0}
        return {"status": "not_found"}

    def revenue_report(self, author: str) -> dict:
        """Calculate potential revenue for an author."""
        agents = [a for a in self._catalog if a["author"] == author]
        total_revenue = sum(a["installs"] * a["price_usd"] * (1 - self.FEE_PERCENT/100) for a in agents)
        return {"author": author, "agents": len(agents), "total_installs": sum(a["installs"] for a in agents),
                "revenue_usd": round(total_revenue, 2), "fee_collected": round(total_revenue * self.FEE_PERCENT/100, 2)}

if __name__ == "__main__":
    mp = AgentMarketplace()
    print(json.dumps(mp.list_agents(), indent=2))
    print("---")
    print(json.dumps(mp.revenue_report("sonoxo"), indent=2))
