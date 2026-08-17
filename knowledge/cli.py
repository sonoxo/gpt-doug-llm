import argparse
import json
from pathlib import Path

from .store import KnowledgeStore


def main():
    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser("build")
    sub.add_parser("status")

    search = sub.add_parser("search")
    search.add_argument("query")

    context = sub.add_parser("context")
    context.add_argument("query")

    args = parser.parse_args()

    root = Path.cwd()

    store = KnowledgeStore(
        root
        / ".doug"
        / "knowledge"
    )

    if args.command == "build":
        result = store.rebuild(root)

    elif args.command == "status":
        result = store.status()

    elif args.command == "search":
        result = store.search(
            args.query
        )

    elif args.command == "context":
        print(
            store.context(
                args.query
            )
        )
        return

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
