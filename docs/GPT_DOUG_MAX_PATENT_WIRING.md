# GPT-DOUG-MAX Patent Intelligence Fabric

GPT-DOUG-MAX is an explicit consumer and synthesis layer for the repository's USPTO patent-intelligence stack.

```text
USPTO PPUBS / saved PDFs
        ↓
ZYRA-MSS exhaustive corpus reader
        ↓  PDF validation + SHA-256 + full text + FTS5
GPT-DOUG USPTO patent-intel ontology
        ↓
GPT-DOUG-MAX deep analysis / synthesis
        ↔
ZYRA-MSS 100-role bounded research fleet
        ↓
ZYRAPALANTIR ontology/control plane
        ↓
GLASS ONION provenance + policy gate
        ↓
Palantir Maven software-assurance evidence
        ↓
GPT-REDPANDA CPR runtime integrity
        ↓
Human review / decision packet
```

## Commands

```bash
doug-max patent-wire status
doug-max patent-wire graph
doug-max patent-wire doctor
doug-max patent-wire search "ontology"
doug-max patent-intel summary
doug-max patent-search "access control"
doug-max patent-corpus resume

zyrapalantir patent-wire status
zyrapalantir patent-wire doctor
zyrapalantir mss patent-wiring
```

## Corpus behavior

The exhaustive reader stays local-first at:

```text
~/.config/gpt-doug/zyra-mss-uspto-palantir/
```

When `corpus.sqlite3` contains `documents_fts`, GPT-DOUG-MAX search uses the full local FTS5 corpus. If the exhaustive corpus is not ready, the bridge falls back to the curated provenance-preserving patent-intelligence index in the repository.

## Decision boundary

This fabric supports public patent research, architecture comparison, provenance, independent-design review, and human decision support. Search hits are not ownership proof. Document-front-page applicant/assignee fields remain document-level evidence only. Claim-level legal analysis, freedom-to-operate conclusions, consequential external actions, and destructive actions remain outside automatic execution and require appropriate human review.
