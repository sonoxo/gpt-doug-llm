# GPT-Doug recursive repository model

`gpt_brain.recursive_repo` builds a **lossless, commit-pinned SQLite memory model** of the entire tracked Git file tree. It records every path, directory relationship, file mode, Git object ID, and file byte payload; a bounded searchable layer indexes safe text and local Python/JS/TS imports. Git object references and SHA-256 attestations protect provenance. It uses only Python's standard library and local `git`.

**This is repository-augmented memory, not a freshly trained or fine-tuned LLM.** It does not fit the entire codebase inside a single prompt. GPT-Doug can retrieve precise, cited excerpts from the full indexed snapshot for ontology-first work.

## Full repository ingestion

After explicitly cloning your authorized repository:

```bash
git clone https://github.com/sonoxo/gpt-doug-llm.git
cd gpt-doug-llm
python3 -m gpt_brain.recursive_repo index --repo .
python3 -m gpt_brain.recursive_repo verify --repo .
python3 -m gpt_brain.recursive_repo stats
python3 -m gpt_brain.recursive_repo tree --depth 2
python3 -m gpt_brain.recursive_repo query 'ontology imports regression'
python3 -m gpt_brain.recursive_repo context 'quantum readiness'
```

The default snapshot is `~/.gpt-doug/recursive-repo.sqlite` and is created with owner-only permissions (0600). Set `--db /absolute/path.sqlite` to specify another location **outside** the checkout. To run through the GPT-Doug CLI: `gpt-doug repo index --repo .`, `gpt-doug repo verify --repo .`, `gpt-doug repo query ontology`.

To activate retrieval in the brain's normal `run` operation, pass `--repo-index ~/.gpt-doug/recursive-repo.sqlite`; the pinned, line-cited repository hits are supplied alongside existing ontology evidence and memory. This is **opt-in**: default brain behavior remains unchanged.

## Ontology and storage model

```text
Git commit SHA (immutable source)
    |
    +-- recursive paths / directories / parent-child links
    |     +-- tracked text files -> bounded, cited FTS5 chunks
    |     +-- tracked binary assets -> complete compressed blobs
    |     +-- symlinks -> link objects, never followed
    |     +-- gitlinks/submodules -> external commit pointers only
    |     +-- Git LFS -> pointer blobs, NOT external LFS objects
    |
    +-- edges: Python imports + local JS/TS module imports
    +-- SHA-256 object digests + complete manifest digest
    +-- immutable local retrieval -> optional brain model context
```

The Git tree listing is authoritative (`git ls-tree -r -l -z <commit>`), not an arbitrary filesystem walk. Reads use `git cat-file --batch`, so **untracked files, changed working-tree files, symlink targets and build outputs are not silently included**. A new `index` run replaces the existing database only after successfully reading and indexing the full tree. A partial index is never published as complete. The `verify --repo .` command rechecks that the source checkout remains at the stored commit and that every node matches the original tree.

The searchable side excludes potentially sensitive filenames and contents (private keys, credentials, `.env` patterns) even though their tracked blobs remain in the private lossless snapshot. Binary and symlink payloads are also not exposed to the LLM retrieval path. The model never executes repository text. Retrieved content is treated as **untrusted data** to resist prompt injection.

Git submodules reference separate repositories; their complete source is **not** within this repository's tracked Git blobs. Git LFS stores pointer files in Git; external media content requires a separate, explicitly authorized download. Every snapshot reports these limitations explicitly rather than claiming those external bytes were captured.

## Operational controls

- Read-only retrieval; no automatic push, merge, deployment, service calls, commands suggested by repository text, or self-modification.
- Size budgets: 32 MiB per tracked blob and 512 MiB total tracked bytes by default. Exceeding either fails closed; raise caps explicitly if the legitimate Git tree requires it.
- Exact commit SHA and per-object SHA-256; tree manifest hash; no execution of indexed files during ingestion.
- FTS5 lexical retrieval is local/offline. No network endpoint, paid embedding API, or model download is needed.
- The index is local private state: **do not commit or publicly upload the database**, as it contains complete tracked file contents.
- To evaluate adaptive changes, continue to use the separate bounded RSI supervisor's tests/benchmark/approval gates; indexing is read-only context, not proof an edit improves performance.

## Verification

```bash
python3 -m unittest tests.test_recursive_repo -v
python3 -m compileall -q gpt_brain/recursive_repo.py tests/test_recursive_repo.py
python3 -m gpt_brain.recursive_repo index --repo . --db "$HOME/.gpt-doug/recursive-repo.sqlite"
python3 -m gpt_brain.recursive_repo verify --repo .
```

The dedicated GitHub Actions workflow runs the fixture suite plus a complete real-repository index and verification for PRs. A passing fixture suite alone is **not** a verified full-repository ingest. Do not claim full coverage until the workflow's real-checkout verification completes.

### XUNIA Museum exhibit descriptor

**GPT-Doug Recursive Repository Model** — a self-hosted, commit-pinned knowledge map of the GPT-Doug source ecosystem, with live retrieval, code dependency graph, and verifiable provenance. Integration may be displayed in the XUNIA Museum after manual deployment authorization; this document alone does not publish the exhibit.
