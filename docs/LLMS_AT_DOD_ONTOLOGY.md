# LLMs-at-DoD Public Reference Ontology

This ontology maps the public `sonoxo/LLMs-at-DoD` fork into GPT-DOUG as read-only, source-grounded reference context. The fork is pinned to commit `fc90483ae3a2db48d46eb3231eccf691cec6d346`; its verified upstream is the archived `deptofdefense/LLMs-at-DoD` repository.

## Graph coverage

The graph represents:

- the observed fork and upstream repository as distinct objects;
- five source artifacts with Git blob SHA and SHA-256 integrity data;
- four tutorials and six workflows;
- referenced models, frameworks, datasets, policy documents, organizations, and safety constraints;
- typed links between tutorial inputs, operations, outputs, attribution, and safety controls.

Each object and link resolves to repository metadata, a named README section, or exact notebook cell indices. `notebook_authored_claim` evidence remains attributed to the notebook and is not promoted to independently verified fact.

## Boundaries

The ontology is not an execution harness. It prohibits source-code execution, classified-data ingestion, credential storage, autonomous external fetch, autonomous training or publishing, network egress, and external mutation. It does not imply DoD affiliation, authorization, endorsement, certification, or operational authority for GPT-DOUG or the `sonoxo` fork.

## Verify

```bash
python3 tools/validate_llms_at_dod_ontology.py
python3 -m pytest -q tests/test_llms_at_dod_ontology.py
```

The validator checks source lineage, the pinned commit and artifact hashes, notebook cell bounds, schema declarations, typed endpoints, evidence references, bounded actions, and all authority guardrails.
