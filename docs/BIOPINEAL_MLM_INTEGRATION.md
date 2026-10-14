# GPT-Doug-LLM + GPT-Doug-MLM + GPT-Doug-BioPineal

## Integrated research roles

- **GPT-Doug-LLM** — existing orchestration and oversight policies in the repository.
- **GPT-Doug-MLM** — existing multidisciplinary proof-search and locally registered model adapters.
- **GPT-Doug-BioPineal** — added command `gpt-doug-biopineal` for provenance-preserving biological patent research metadata and optional model-assisted review. This is not a physical chip or laboratory control system.

## Source limitations

The user-provided text is an excerpt from a USPTO Patent Public Search results page dated 2026-10-13. The bibliographic records below have not been independently checked against the current official database; all rights remain with their respective patent holders. No patent ownership, clinical benefit, regulatory approval, patent validity, or invention rights are claimed for GPT-Doug.

Reference metadata:
- US 12760085 B1 — *Enhanced T-cell receptor star and application thereof*; China Immunotech (Beijing) Biotechnology Co., Ltd.
- US 12760292 B2 — *Base editors, compositions, and methods for modifying the mitochondrial genome*; Broad Institute, University of Washington, Harvard College.
- US 12757878 B2 — *System for detecting extracellular purinergic receptor ligand, and non-human animal having the system introduced thereinto*; Chugai Seiyaku.

Use this material for **patent classification, provenance, bibliographic indexing, and high-level analysis** only. Do not turn genetic modification protocols, viral vector details, or animal procedures into self-executing laboratory workflows.

## CLI

```bash
python -m gpt_doug_mlm.biopineal status
python -m gpt_doug_mlm.biopineal patents --topic mitochondria
python -m pytest tests/test_biopineal_integration.py -q
```

After package installation, the same status query is available as `gpt-doug-biopineal status`.

BioPineal requires explicitly provided local model callables; there is no automatic remote network access, hardware actuator, biological operation, or model self-creation.
