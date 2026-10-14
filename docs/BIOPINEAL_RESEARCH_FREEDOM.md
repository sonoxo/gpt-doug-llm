# BioPINEAL Research Freedom Rule v1

**Rule:** `BIOPINEAL_NO_UNNECESSARY_GUARDRAILS_V1`  
**Scope:** local, bounded, synthetic / properly authorized research only.  
**Project authority:** `RESEARCH_ONLY`. This is a project workflow rule, **not** a law, military order, credential, third-party contract or patent license.

## Principle

Local scientific exploration should not require extra administrative approval when the action is wholly offline, non-executing outside its sandbox, based on permitted synthetic inputs, and already passes mandatory technical validation. **No additional review** does not mean no constraints or permission to disable security safeguards.

**No-extra-review operations:** local source lookup, read-only heartbeat monitoring, reading the operator's own local pseudonymous profile, bounded classical quantum mathematics, validation of a synthetic scenario, and checking the versioned ontology schema.

**Not covered by the exception:** registering or changing identities, research publication, optional PINEAL writes, external networks/hardware, obtaining credentials, changing authority, accessing private or classified data, modifying model weights, autonomous agents with external actions, and any weapons or military actuation. Those retain ordinary data-rights, human review, operational, and security requirements, or remain outside this project's scope entirely.

Patent content is published research evidence **not** a license or proof of freedom to operate. The repository MIT license applies to the software under that license; it does not confer rights to third-party patents, vendor platforms, branding, human subjects, controlled data or non-owned datasets. Legal/compliance assessment of actual hardware, proprietary implementation, commercialization, or real research subjects is outside this rule.

## CLI

```bash
bash scripts/doug-max warfighter biopineal freedom --action source_search
bash scripts/doug-max warfighter biopineal freedom --action simulate_classical_quantum
bash scripts/doug-max warfighter biopineal freedom --action publish
python3 -m unittest research_lab.warfighter.tests.test_research_freedom -v
```

The evaluator reports `NO_EXTRA_REVIEW_REQUIRED` for allowed **classes** and `NORMAL_CONTROLS_REQUIRED` otherwise. It **does not execute any requested action**, change `scripts/doug-max`'s existing preflight, bypass PINEAL/ZYRA policy, approve publication, change the repository license, or grant new privileges. Each operation still enforces its own input validation, resource limits, applicable law and authorization.

Rule configuration: [`safety-shield/ontology/biopineal-research-freedom-v1.json`](../safety-shield/ontology/biopineal-research-freedom-v1.json), with exact immutable allowed-action set checked by [`research_freedom.py`](../research_lab/warfighter/research_freedom.py). Any scope expansion requires normal code review, security review and updated tests. The policy is a local research convenience, not an authentication or sandboxing boundary.
