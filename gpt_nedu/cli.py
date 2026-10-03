"""Dependency-free learning menu and a real parameter-binding demonstration."""
import argparse
import json
import sqlite3

SOURCE = "https://xkcd.com/327/"
PAGE = "https://xunia.org/learn/nedu/"


def database_demo(name: str) -> dict:
    """Store arbitrary names as values in an isolated, disposable database."""
    db = sqlite3.connect(":memory:")
    try:
        db.execute("CREATE TABLE students (name TEXT)")
        db.execute("INSERT INTO students (name) VALUES (?)", ("Ada",))
        db.execute("INSERT INTO students (name) VALUES (?)", (name,))
        rows = [row[0] for row in db.execute("SELECT name FROM students ORDER BY rowid")]
        return {"students": rows, "table_intact": True, "method": "parameter binding"}
    finally:
        db.close()


def lesson() -> str:
    return (
        "GPT-NEDU // NOVICE EDU // GPT-DOUG + ZYRA + XUNIA\n\n"
        "1. OBSERVE: xkcd's school mistakes a student's name for database code.\n"
        "2. TRACE: input -> query construction -> database. The boundary breaks\n"
        "   when a program pastes untrusted text into executable SQL.\n"
        "3. REBUILD: pass the name separately using a placeholder: VALUES (?).\n"
        "4. VERIFY: the original name is stored and the student table survives.\n\n"
        "The AI remix changes the problem to prompt injection: text supplied as\n"
        "data tries to override a grader's instructions. SQL placeholders are\n"
        "not a general LLM defense. Separate trusted rules from source text,\n"
        "restrict tools, validate outputs, and review consequential decisions.\n"
        "No keyword filter or prompt alone guarantees protection.\n\n"
        f"Original reference: Randall Munroe, xkcd #327 — {SOURCE}\n"
        "GPT-NEDU is an educational module, not a newly trained model.\n"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="GPT-Doug novice education")
    parser.add_argument("action", nargs="?", choices=["menu", "lesson", "demo", "links"], default="menu")
    args = parser.parse_args(argv)
    if args.action == "lesson":
        print(lesson())
    elif args.action == "demo":
        print(json.dumps(database_demo("Robert'); DROP TABLE students;--"), indent=2))
        print("Only a temporary in-memory database was used. The name stayed data.")
    elif args.action == "links":
        print(f"Learning page (after Pages deployment): {PAGE}\nComic: {SOURCE}\n"
              "Source: https://github.com/sonoxo/gpt-doug-llm/tree/main/gpt_nedu")
    else:
        try:
            while True:
                print("\n[GPT-DOUG // GPT-NEDU]\n1 Learn\n2 Run safe database demo\n3 Source links\nq Return")
                choice = input("NEDU > ").strip().lower()
                if choice in {"q", "quit", "exit"}:
                    break
                action = {"1": "lesson", "2": "demo", "3": "links"}.get(choice)
                if action:
                    main([action])
                else:
                    print("Choose 1, 2, 3, or q.")
        except (EOFError, KeyboardInterrupt):
            print("\nReturning from GPT-NEDU.")
    return 0
