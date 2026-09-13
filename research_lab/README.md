# GPT-Doug Invention Lab

Four executable, standard-library research prototypes, wired into the existing
`scripts/doug-max` command. This is local experimentation, not a production
security boundary, patent grant, novelty finding, or freedom-to-operate opinion.

## Run

Python 3.9+; no installation or network required. From the repository root:

```bash
bash scripts/doug-max invention-lab demo
python3 -m unittest discover -s research_lab/tests -v
```

The demo evaluates eight synthetic assertions spanning all four modules and
returns nonzero on failure. It never contacts a model, executes a repair, changes
the live ontology, or issues real operational approval. Run evidence is synthetic,
not a measurement of production accuracy or patent novelty.

## Interfaces

| Module | Implemented mechanism | Interface |
|---|---|---|
| Evidence-bound admission | SHA-256 binding of mission, action and code/data/policy version maps; trusted issuer allowlist; expiration; SQLite atomic one-use receipt | `research_lab.approval.ApprovalGate` |
| Repair planning | Reverse dependency closure, deduplicated test selection, missing-coverage warnings and rollback revision boundary | `invention-lab repair input.json` |
| Offline reconciliation | Three-way object merge, explicit edit/edit and edit/delete conflicts, deletion vs null, parent hashes and selection provenance | `invention-lab reconcile input.json` |
| Research lineage | Document content hash, exact Unicode offsets and quote matching, transitive invalidation of dependent claims | `invention-lab lineage input.json` |

All CLI commands print JSON. Exit codes: 0 = checks passed/candidate ready;
1 = review required, conflict, invalid lineage, or failed demo; 2 = invalid input.
These are local research states and cannot substitute for Black House decisions.

### Repair input

```json
{"dependencies":{"source":[],"index":["source"]},"changed":["source"],"tests":{"source":["test_source"],"index":["test_index"]},"revisions":{"source":"commit-before-change","index":"commit-before-change"}}
```

An edge lists a node's upstream dependencies. Unknown graph nodes fail validation;
cycles terminate safely. A node without mapped tests or rollback revision requires
review. Revisions are user-supplied references, not resolved Git objects. The plan
does not diagnose root causes, generate patches, run selected tests, or restore
revisions. Existing full CI gates must remain enabled.

### Reconciliation input

```json
{"base":{"item":{"value":1}},"local":{"item":{"value":2}},"remote":{"item":{"value":1}}}
```

The base must be the actual common ancestor, supplied by a trusted host. Concurrent
edits to the same object are surfaced even if they affect different fields. No
last-writer-wins guessing. Conflicted objects are absent from the partial candidate;
never apply it while `apply_allowed` is false. Even when true, it means only that
this object merge is conflict-free: graph references, schema and current policy
must pass host validation before applying. Parent hashes identify the inputs but
do not authenticate who supplied them or prove ancestry.

### Lineage input

`documents` maps document IDs to full text. `claims` maps claim IDs to objects with
`citations` and optional `depends_on` claim IDs. Build citations through
`research_lab.lineage.anchor(document_id, text, start, end)`. It returns the
document ID, full-document SHA-256, Unicode character offsets, and exact quote.
Missing documents, changed content, bad offsets, forged quotes and uncited claims
require review. Invalid parent claims invalidate descendants. `ANCHORS_VALID`
means only that the citation bytes/offsets agree; it does not prove that the quote
supports a conclusion, that a claim is true, or that a patent applies.

### Admission API trust boundary

`ApprovalGate(database, approvers).issue(snapshot, authenticated_approver, now, ttl)`
returns a bearer receipt. `consume(receipt, current_snapshot, now)` returns a bool.
Snapshots require nonempty `mission`, `action` and resource maps `code`, `data`,
`policy`, each mapping resource IDs to lowercase SHA-256 strings.

The host must authenticate the approver, enforce mission-specific authority,
compute fresh version hashes from real resources, protect the SQLite database,
secure receipts, and supply a trusted clock. Callers cannot be allowed to choose
their own identity, clock, database or current evidence. The demo operator is
synthetic. No network approval endpoint is exposed. Revocation takes effect when
the host's approver allowlist is updated; receipts persist across process restarts.
Atomic consumption prevents concurrent replay against one SQLite database.

Consumption is not atomic with a real external action. A crash after consumption
can lose the attempt; a resource can change after the check. Production adapters
need an idempotent action protocol plus resource locking/version preconditions
and an authenticated approval service. Restoring an old database can restore old
receipts, so anti-rollback protection is a separate production requirement.

## Ecosystem integration

This PR connects the lab to GPT-Doug's CLI. ZYRA and XUNIA can import the APIs and
consume JSON outputs through their existing gates, but live cross-repo execution
is not wired here. Canonical Black House authority remains unchanged. The lab
does not write the patent corpus, activate research agents, or change Maven sync.

## Invention review

See [candidate disclosures](INVENTION_CANDIDATES.md). These designs use established
techniques; no uniqueness or patentability is inferred from passing tests. Record
actual human conception, prior art comparisons, public disclosure dates, and
specific measurable improvements before presenting a filing candidate.
