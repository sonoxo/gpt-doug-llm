"""One-command CLI for GPT-DOUG Dataset Civilization."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .engine import FleetError, connect, manifest_from_file, report, run, search

ROOT = Path(__file__).resolve().parents[1]
DB = Path.home() / ".local/share/gpt-doug/dataset-fleet/index.sqlite"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GPT-DOUG Dataset Civilization: free local fleet")
    parser.add_argument("command", choices=["run", "status", "search", "export", "manifest"])
    parser.add_argument("query", nargs="?", help="Search text for search command")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=Path("data_fleet/manifest.json"))
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "manifest":
            data=manifest_from_file(args.root/args.manifest if not args.manifest.is_absolute() else args.manifest)
            result={"schema":data["schema"],"datasets":[{"id":s["id"],"path":s["path"],"sensitivity":s["sensitivity"]} for s in data["datasets"]]}
        elif args.command == "run":
            result=run(args.root,args.manifest,args.db,workers=args.workers,max_attempts=args.retries)
        else:
            if not args.db.expanduser().exists():
                raise FleetError("no local index; run python3 -m data_fleet run first")
            con=connect(args.db)
            try:
                if args.command == "search":
                    if not args.query:
                        raise FleetError("search requires a query")
                    result={"schema":"gpt-doug.dataset-fleet.search.v1","query":args.query,"matches":search(con,args.query)}
                else:
                    mf_path=(args.root/args.manifest if not args.manifest.is_absolute() else args.manifest)
                    result=report(con,manifest_from_file(mf_path))
            finally:
                con.close()
        output=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(output,encoding="utf-8")
            print("Saved "+str(args.out))
        else:
            print(output,end="")
        return 0
    except (FleetError,ValueError,OSError,FileNotFoundError,json.JSONDecodeError) as exc:
        print("GPT-DOUG DATA FLEET BLOCKED: "+str(exc),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
