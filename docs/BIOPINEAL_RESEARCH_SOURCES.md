# GPT-Doug BioPINEAL — Curated External Research Sources (v1)

**Status:** Read-only public-reference index. **Authority:** `RESEARCH_ONLY`.
**Captured for this version:** October 12, 2026. The entries are research context, not evidence that BioPINEAL has biological hardware or permission to implement third-party patented processes.

## Execute locally

From the `gpt-doug-llm` checkout on the BioPINEAL patent-integration feature branch:

```bash
bash scripts/doug-max warfighter biopineal sources
bash scripts/doug-max warfighter biopineal sources --query 20260308339
bash scripts/doug-max warfighter biopineal sources --query "cortical labs"
bash scripts/doug-max warfighter biopineal sources --topic biological_computing
python3 -m unittest research_lab.warfighter.tests.test_biopineal_sources -v
```

The `sources` command is an **offline filter** over a version-pinned, local, two-record JSON registry in `intel/sources/biopineal-2026-10-12-public-evidence.json`. It performs no internet queries, PINEAL store writes, neural stimulation, firmware changes, AI training, ontology publication, or patent-rights analysis. Each returned entry carries an individual SHA-256 and the registry SHA-256 for reproducibility; hashes are integrity references, not authenticated signatures or legal proofs.

## Two distinct references

| Local ID | Evidence and origin | Research relationship |
| --- | --- | --- |
| `us-pgpub:20260308339-A1` | User-supplied USPTO Patent Public Search capture, U.S. published **application** `US 20260308339 A1`, publication date **2026-10-08**, *Bio-assimilation master batch composition...*; inventor **Michael Stephens**, listed assignee **Smart Plastic Technologies, LLC** | `MATERIALS_SCIENCE_REFERENCE_ONLY` — a polymer degradation/bio-assimilation patent disclosure, **not** Cortical Labs research or a biological neural chip |
| `cortical-labs:cl1` | [Cortical Labs CL1 first-party product description](https://www.corticallabs.com/cl1.html); vendor describes living neurons on a silicon/electrode interface exchanging information through biOS | `EXTERNAL_BIOCOMPUTING_REFERENCE_ONLY` — an unrelated vendor description, **not** proof of access to its CL1 device or a link to the polymer patent |

The originally captured USPTO search box contained the phrase `cortical labs`. Search query text **is not attribution evidence**. The patent results list and selected polymer application do not establish that Cortical Labs invented, owns, licensed, or uses that patent.

### Patent record provenance

- Source: user-supplied Patent Public Search extraction (`US-PGPUB` page content).
- Captured text SHA-256: `fd01488625510df8bb52e0d27eb88e63c99fa0759ea0471b828ec3270ad5bfc9`.
- Official search entry point: [USPTO Patent Public Search](https://ppubs.uspto.gov/). The captured application ID should be searched there to review current status.
- The supplied text references continuation from a parent application associated with **US 12,668,672 B2**. That is a *different document* and does not transform the captured A1 application into an issued patent. [Related-family grant reference](https://patents.google.com/patent/US12668672B2/en).
- The patent application describes polyolefin carrier resin, an antioxidant package, transition-metal carboxylates, and possible subsequent microbial assimilation of degraded fragments. These are attributed application disclosures; no independent lab verification, biodegradation certification, patent ownership opinion, freedom-to-operate assessment, or implementation license is established by indexing them.

### Biological-computing reference provenance

- Source: [Cortical Labs CL1 official product page](https://www.corticallabs.com/cl1.html).
- The website discusses biOS, neuron-on-silicon stimulation/recording, self-contained life support and a closed-loop software environment. The registry identifies these statements as **vendor claims**, not independent performance measurements.
- The source index does not buy, connect to, emulate, or deploy software on the CL1. BioPINEAL's local quantum simulations remain **classical mathematical demos**; its mitochondrial units are abstract compute operations, not biological ATP or actual measured electrical energy.

## Safety and evidence constraints

`biopineal_sources.py` rejects malformed input, wrong classification, extra fields, renamed assignee/publisher, unauthorized authority flags, forged patent-grant assertions, false CL1 association, forged hardware connection and modified claims text without a corresponding intentional version update. The JSON's canonical SHA-256 is pinned in the module and must change when the curated source version is legitimately revised. This is a source-integrity guard, not tamper-proof security against modification of both code and data.

No records are copied into Warfighter operational readiness or the PINEAL persistent-memory database automatically. Additional data sources require their own provenance checks and human review. The public registry is not a government, legal, scientific, or patent-enforcement authority.
