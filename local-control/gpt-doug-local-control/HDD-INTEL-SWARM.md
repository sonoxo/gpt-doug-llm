# GPT-Doug MAXLLM HDD Intel Swarm

The HDD intelligence layer extends the XUNIA / ZYRA local-control gateway with read-first local disk metadata analysis.

## Capabilities

- `hdd_index`: parallel local metadata index, 1-32 workers, hard cap 100,000 files
- `hdd_search`: search indexed path/name with category/extension filters
- `hdd_summary`: category, extension, file-count, and byte totals
- `hdd_large_files`: largest indexed files
- `hdd_recent`: recently modified files
- `hdd_duplicate_candidates`: same-name + same-size metadata candidates only

The index records path/name, extension, category, size, and modification time. It does not read file contents, hash files, upload data, or delete anything.

## Governance

HDD indexing is limited to the user's home directory and `/Volumes`. Credential/keychain paths are denied. The server remains bound to `127.0.0.1:8765` with no public listener or cloud callback.

HDD intelligence actions are read-only and do not require arming. Existing control/write/shell actions still require an explicit arm for at most five minutes. PANIC STOP remains available.

## Local launch

From the package directory:

```bash
chmod +x HDD-INTEL-SWARM.command
./HDD-INTEL-SWARM.command
```

The launcher starts the bridge, creates a metadata index of up to 25,000 files in the user's home directory with 8 workers, and opens the local dashboard.
