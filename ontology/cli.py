from __future__ import annotations

import argparse
import json

from .models import Entity, Relation
from .store import OntologyStore


def emit(value):
    print(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


def main():
    parser = argparse.ArgumentParser(
        prog="python -m ontology.cli"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser("status")

    entity = sub.add_parser("entity")
    entity.add_argument("query")

    add_entity = sub.add_parser("add-entity")
    add_entity.add_argument("type")
    add_entity.add_argument("name")
    add_entity.add_argument("--jurisdiction")

    add_relation = sub.add_parser("add-relation")
    add_relation.add_argument("source")
    add_relation.add_argument("relation")
    add_relation.add_argument("target")
    add_relation.add_argument(
        "--confidence",
        default="confirmed",
    )

    path = sub.add_parser("path")
    path.add_argument("source")
    path.add_argument("target")

    args = parser.parse_args()
    store = OntologyStore()

    if args.command == "status":
        emit(store.status())
        return

    if args.command == "entity":
        emit(store.search_entities(args.query))
        return

    if args.command == "add-entity":
        result = store.add_entity(
            Entity(
                type=args.type,
                name=args.name,
                jurisdiction=args.jurisdiction,
            )
        )
        emit(result.model_dump())
        return

    if args.command == "add-relation":
        source = store.resolve_one(args.source)
        target = store.resolve_one(args.target)

        if source is None:
            raise SystemExit(
                f"Unknown source entity: {args.source}"
            )

        if target is None:
            raise SystemExit(
                f"Unknown target entity: {args.target}"
            )

        result = store.add_relation(
            Relation(
                source=source.id,
                target=target.id,
                type=args.relation,
                confidence=args.confidence,
            )
        )
        emit(result.model_dump())
        return

    if args.command == "path":
        emit(
            store.path(
                args.source,
                args.target,
            )
        )


if __name__ == "__main__":
    main()
