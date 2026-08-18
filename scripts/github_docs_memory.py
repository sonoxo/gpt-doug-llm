from pathlib import Path
import re
import sqlite3
import subprocess
import sys

ROOT = Path.cwd()
CACHE = Path.home() / ".cache" / "gpt-doug-max" / "github-docs"
DB = ROOT / "memory" / "gpt-doug-max" / "github_docs.sqlite3"


def sync_docs():
    CACHE.parent.mkdir(parents=True, exist_ok=True)

    if (CACHE / ".git").exists():
        subprocess.run(
            ["git", "-C", str(CACHE), "pull", "--ff-only"],
            check=True,
        )
    else:
        subprocess.run(
            [
                "git", "clone",
                "--depth", "1",
                "--filter=blob:none",
                "--sparse",
                "https://github.com/github/docs.git",
                str(CACHE),
            ],
            check=True,
        )
        subprocess.run(
            [
                "git", "-C", str(CACHE),
                "sparse-checkout", "set",
                "content", "LICENSE", "README.md",
            ],
            check=True,
        )


def clean_markdown(text):
    text = re.sub(r"\A---.*?---", "", text, flags=re.S)
    text = re.sub(r"{%.*?%}", " ", text, flags=re.S)
    text = re.sub(r"{{.*?}}", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def source_url(path):
    rel = path.relative_to(CACHE / "content").with_suffix("")
    parts = list(rel.parts)

    if parts and parts[-1] == "index":
        parts = parts[:-1]

    return "https://docs.github.com/en/" + "/".join(parts)


def build():
    sync_docs()
    DB.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS github_docs (
            path TEXT PRIMARY KEY,
            title TEXT,
            body TEXT NOT NULL,
            source_url TEXT NOT NULL,
            git_commit TEXT NOT NULL
        )
    """)

    commit = subprocess.check_output(
        ["git", "-C", str(CACHE), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    count = 0

    for path in (CACHE / "content").rglob("*.md"):
        raw = path.read_text(errors="ignore")

        title_match = re.search(
            r"^title:\s*[\"']?(.*?)[\"']?\s*$",
            raw,
            flags=re.M,
        )

        title = (
            title_match.group(1)
            if title_match
            else path.stem.replace("-", " ").title()
        )

        conn.execute(
            """
            INSERT OR REPLACE INTO github_docs
            (path, title, body, source_url, git_commit)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(path.relative_to(CACHE)),
                title,
                clean_markdown(raw),
                source_url(path),
                commit,
            ),
        )

        count += 1

    conn.commit()
    conn.close()

    print("GPT-DOUG-MAX MEMORY READY")
    print("GitHub Docs pages:", count)
    print("Database:", DB)
    print("Source commit:", commit)


def search(query, limit=5):
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    words = [w.lower() for w in re.findall(r"[A-Za-z0-9_-]+", query)]

    if not words:
        return

    rows = conn.execute(
        "SELECT title, body, source_url FROM github_docs"
    ).fetchall()

    scored = []

    for row in rows:
        haystack = (row["title"] + " " + row["body"]).lower()
        score = sum(haystack.count(word) for word in words)

        if score:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)

    for score, row in scored[:limit]:
        print("\n[" + str(score) + "] " + row["title"])
        print(row["source_url"])

        body = re.sub(r"\s+", " ", row["body"])
        print(body[:500])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        search(" ".join(sys.argv[2:]))
    else:
        build()
