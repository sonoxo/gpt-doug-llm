from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx
from rapidfuzz import fuzz, process

from .models import Entity, Relation


class OntologyStore:
    def __init__(self, root: Path | str = ".doug/ontology"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

        self.entities_path = self.root / "entities.jsonl"
        self.relations_path = self.root / "relations.jsonl"

        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}

        self.load()

    def load(self) -> None:
        self.entities = {}
        self.relations = {}

        if self.entities_path.exists():
            for line in self.entities_path.read_text(
                encoding="utf-8"
            ).splitlines():
                if line.strip():
                    entity = Entity.model_validate_json(line)
                    self.entities[entity.id] = entity

        if self.relations_path.exists():
            for line in self.relations_path.read_text(
                encoding="utf-8"
            ).splitlines():
                if line.strip():
                    relation = Relation.model_validate_json(line)
                    self.relations[relation.id] = relation

    def _write_entities(self) -> None:
        with self.entities_path.open("w", encoding="utf-8") as fh:
            for entity in self.entities.values():
                fh.write(entity.model_dump_json() + "\n")

    def _write_relations(self) -> None:
        with self.relations_path.open("w", encoding="utf-8") as fh:
            for relation in self.relations.values():
                fh.write(relation.model_dump_json() + "\n")

    def add_entity(self, entity: Entity) -> Entity:
        self.entities[entity.id] = entity
        self._write_entities()
        return entity

    def add_relation(self, relation: Relation) -> Relation:
        if relation.source not in self.entities:
            raise KeyError(f"Unknown source entity: {relation.source}")

        if relation.target not in self.entities:
            raise KeyError(f"Unknown target entity: {relation.target}")

        self.relations[relation.id] = relation
        self._write_relations()
        return relation

    def status(self) -> dict:
        types: Dict[str, int] = {}

        for entity in self.entities.values():
            types[entity.type] = types.get(entity.type, 0) + 1

        relation_types: Dict[str, int] = {}

        for relation in self.relations.values():
            relation_types[relation.type] = (
                relation_types.get(relation.type, 0) + 1
            )

        return {
            "entities": len(self.entities),
            "relations": len(self.relations),
            "entity_types": types,
            "relation_types": relation_types,
            "data_directory": str(self.root),
        }

    def search_entities(
        self,
        query: str,
        limit: int = 10,
        score_cutoff: int = 50,
    ) -> List[dict]:
        labels: Dict[str, str] = {}

        for entity in self.entities.values():
            labels[entity.name] = entity.id

            for alias in entity.aliases:
                labels[alias] = entity.id

        results = process.extract(
            query,
            list(labels.keys()),
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=score_cutoff,
        )

        found = []
        seen = set()

        for label, score, _ in results:
            entity_id = labels[label]

            if entity_id in seen:
                continue

            seen.add(entity_id)
            entity = self.entities[entity_id]

            found.append(
                {
                    "score": score,
                    "entity": entity.model_dump(),
                }
            )

        return found

    def resolve_one(self, query: str) -> Optional[Entity]:
        matches = self.search_entities(query, limit=1)

        if not matches:
            return None

        return Entity.model_validate(matches[0]["entity"])

    def graph(self) -> nx.MultiDiGraph:
        graph = nx.MultiDiGraph()

        for entity in self.entities.values():
            graph.add_node(
                entity.id,
                **entity.model_dump(),
            )

        for relation in self.relations.values():
            graph.add_edge(
                relation.source,
                relation.target,
                key=relation.id,
                **relation.model_dump(),
            )

        return graph

    def path(
        self,
        source_query: str,
        target_query: str,
    ) -> List[dict]:
        source = self.resolve_one(source_query)
        target = self.resolve_one(target_query)

        if source is None:
            raise KeyError(
                f"Could not resolve source: {source_query}"
            )

        if target is None:
            raise KeyError(
                f"Could not resolve target: {target_query}"
            )

        graph = self.graph().to_undirected()

        node_path = nx.shortest_path(
            graph,
            source=source.id,
            target=target.id,
        )

        return [
            self.entities[node_id].model_dump()
            for node_id in node_path
        ]
