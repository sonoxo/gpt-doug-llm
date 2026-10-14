# GPT-Doug bounded brute-force research engine

The breakthrough engine exhaustively searches a bounded hypothesis space across
CL1 simulator electrophysiology, CL1 biological-neural-network electrophysiology
as a reference modality, patient-derived tumor organoid response, GMRO molecular
profiles, and mitochondrial/metabolic reference modalities.

It is deliberately a **computational research prioritizer**, not a wet-lab
automation system and not a treatment engine.

## Run

```bash
bash scripts/gpt-doug-breakthrough --top 12
bash scripts/gpt-doug-breakthrough --domain oncology --top 20
bash scripts/gpt-doug-breakthrough --domain neurocomputing --top 20
```

The current Cartesian search contains:

```text
2 domains
x 6 modalities
x 5 research questions
x 5 endpoints
x 4 validation strategies
= 1,200 hypotheses
```

Every candidate receives deterministic scores for evidence proximity,
falsifiability, translational relevance, and validation strength. Candidates
that attempt to infer mitochondrial state from CL1 spikes alone are strongly
penalized because public CL1 interfaces do not provide mitochondrion-resolved
ATP, ROS, membrane-potential, or microscopy telemetry.

## Highest-value research directions

1. **Oncology:** fuse GMRO molecular context with patient-derived organoid
   functional response, test on prospective holdouts, and require independent
   replication before clinical interpretation.
2. **Resistance:** use longitudinal organoid response plus molecular evidence to
   discover reproducible resistance signatures; treat them as hypotheses until
   validated against clinical outcomes.
3. **CL1 software research:** benchmark closed-loop algorithms against the
   official SDK simulator first, then treat any biological BNN results as a
   separate, human-supervised evidence tier.
4. **Mitochondrial/neural research gap:** any relationship between electrical
   dynamics and mitochondrial state requires matched orthogonal measurements;
   spikes alone are insufficient.

No module here grows cells, stimulates physical CL1 hardware, or makes patient
treatment decisions.
