# BioPineal v0.5 — user-supplied lithium patent evidence nexus

**Status:** offline research software. No chemical equipment, patent license, validated scientific discovery or Nobel Peace Prize outcome is asserted.

## Source evidence — 2026-10-13

A user-provided USPTO Patent Public Search excerpt identifies **US 12,760,393 B1** (normalized: US12760393B1), titled **Methods and apparatuses for Li extraction and generation of high purity lithium hydroxide**. It attributes the patent to **PolyPlus Battery Company** and names inventors Steven J. Visco, Yevgeniy S. Nimon, and Bruce D. Katz.

The provided material describes lithium-bearing brines and recycling inputs, a selectively lithium-ion-conductive ceramic membrane with a cation-exchange laminate, an output that includes lithium hydroxide, and potential hydrogen and chlorine gaseous coproducts. The excerpt gives CPC classes C22B26/12, C25B1/16, C25B9/19 and C25B13/07.

**Independent verification gap:** Public lookups on October 13 did not retrieve this exact newly listed patent. The stored excerpt is labeled USER PROVIDED / INDEPENDENTLY UNVERIFIED. The reference URL https://patents.google.com/patent/US12760393B1/en is not proof that an official record was retrieved. Similar PolyPlus patents do not corroborate the precise grant.

## Real delivered software

The extension reuses the established PINEAL memory platform rather than a separate dataset:

- Existing patent validation, public metadata source host rules and SQLite provenance/audit chain.
- Typed knowledge graph in the ontology/lithium_nexus_v1.json file with **17 nodes and 16 edges**: inventor/company attribution, potential feedstocks, technical concepts, possible outputs, hazardous coproducts, legal and independent safety approvals.
- An explicit import preview that writes nothing, and an opt-in single-record atomic/idempotent SQLite import.
- A terminal visual graph, Graphviz DOT, offline CSP-locked HTML dashboard, and bounded watch of **actual local** indexed records.
- Local context search after import, not any automated website scraping.

## One-command Mac preview

From the GPT-Doug repository root:

~~~bash
bash run-GPT-Doug-BioPineal.command
~~~

Or:

~~~bash
bash scripts/doug-max bio-pineal audit
bash scripts/doug-max bio-pineal preview
bash scripts/doug-max bio-pineal status
bash scripts/doug-max bio-pineal map
bash scripts/doug-max bio-pineal dot > /tmp/biopineal-graph.dot
bash scripts/doug-max bio-pineal html > /tmp/biopineal-dashboard.html
bash scripts/doug-max bio-pineal watch --frames 20 --interval 1
~~~

To **explicitly write only this third-party excerpt metadata** into the existing PINEAL SQLite store:

~~~bash
bash scripts/doug-max bio-pineal import-reference --commit
bash scripts/doug-max bio-pineal status
bash scripts/doug-max bio-pineal map
~~~

No paid models, online feeds or external API credentials are required. Reading status may initialize a private local SQLite state file under ~/.local/share/gpt-doug-pineal. Running the above commands does not contact PolyPlus or USPTO.

## Required review gates and attribution

- **Intellectual property:** PolyPlus Battery Company is the stated third-party assignee. GPT-Doug and ZYRA do not acquire ownership or freedom to operate. Patent counsel must independently review the exact source, grants, jurisdiction, status and claims.
- **Physical process hazards:** hydrogen may be flammable; chlorine is toxic; lithium hydroxide is corrosive. Qualified process-safety and environmental professionals must review any independent physical proposal.
- **No dangerous instructions:** the implementation includes no apparatus assembly procedure, operating settings, gas handling, chemical manufacturing recipe or hardware actuator.
- **No biological or peace extrapolation:** lithium materials descriptions do not establish BioPineal neural effects, clinical results, community benefits or validated Nobel Peace Prize impact.
- **Source confidence:** User-supplied descriptive excerpt is indexed for research only, never promoted to VERIFIED without external human/source review.
- **Privacy:** No donor, beneficiary, user credentials, or private material is collected or posted to GitHub.

## Testing and development

~~~bash
cd integrations/gpt-doug-pineal
python3 -m pip install -e '.[test]'
python3 -m pytest -q
~~~

The new tests cover ontology drift, provenance, denial flags, local SQLite import, idempotence, tampered graph failures, context retrieval, CSP-locked HTML, bounded terminal watch, and no-network behavior.

This is **not a validated chemical system or legal patent opinion**. It is a working patent research and visualization layer inside GPT-Doug PINEAL.
