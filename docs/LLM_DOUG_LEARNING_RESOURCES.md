# llm-doug learning and NASA 3D resources

This update extends the existing GPT-DOUG worker knowledge catalog. `llm-doug` is the requested working name; the repository remains `sonoxo/gpt-doug-llm`.

## Included

- Seven Open Culture category references: courses, audiobooks, movies, podcasts, K-12, eBooks and languages.
- One NASA 3D reference, including the official hub and GitHub mirror.
- `knowledge/nasa_3d_inventory.json`: all 1,199 files returned by NASA's non-truncated Git tree at commit `11ebb4ee043715aefbba6aeec8a61746fad67fa7`. Paths, byte sizes, Git blob hashes and pinned links are included. File counts include metadata and support files; they are not counts of distinct models.

## How Doug uses it

`workers/ontology_workers.py` loads `workers/knowledge/*.jsonl`. Its existing keyword matcher supplies relevant entries to `workers/agent-daemon.py`, including attribution and source URLs. Example requests: "Open Culture audiobook", "Open Culture programming course", and "NASA 3D model texture". The detailed NASA inventory is available for file-based tools to inspect; it is not automatically inserted into every model prompt.

## Get the NASA asset files

From your local GPT-DOUG checkout, this downloads the official repository to a separate directory:

```bash
git clone https://github.com/nasa/NASA-3D-Resources.git ../llm-doug-nasa-3d
git -C ../llm-doug-nasa-3d checkout 11ebb4ee043715aefbba6aeec8a61746fad67fa7
```

These commands have not been executed in this environment. Check available disk space before downloading the asset collection. Preserve source attribution and consult NASA's media usage guidance linked from https://science.nasa.gov/3d-resources/ .

## Scope and validation

This is a reference catalog and complete NASA repository file inventory, not an Open Culture site mirror, a download of NASA binaries, model training, or a live deployment. Open Culture links do not establish blanket rights to redistribute third-party books, courses or films. Verify item-specific terms before copying source content.

Eight category retrieval checks passed using the existing loader and matcher functions, and all eight JSONL records passed field and unique-ID checks. The NASA inventory is non-truncated and contains 1,199 unique paths. The full repository test suite has not run because terminal GitHub cloning is blocked in this environment; this change stays in a draft PR pending the repository's full test gate.
