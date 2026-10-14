# CL1 mitochondrial evidence + 3D reference model

This module adds an evidence-grounded **reference visualization** for mitochondrial anatomy relevant to living neurons used by Cortical Labs CL1.

It deliberately does **not** claim that a mitochondrion from a specific CL1 neuron has been imaged, segmented, or reconstructed. Public CL1 documentation exposes neural recording/stimulation interfaces and simulator workflows, not mitochondrial microscopy, ATP measurements, membrane potential, ROS, or organelle-resolved telemetry.

## Evidence registry

`intel/sources/cl1-mitochondria-2026-10-13-evidence.json`

The registry separates:

- Cortical Labs first-party CL1 / CL API documentation;
- the 2026 CL API technical preprint;
- peer-reviewed mitochondrial structure sources for cristae, ATP synthase, and MICOS;
- explicit prohibited inferences.

## Commands

```bash
python3 -m research_lab.cl1_mitochondria evidence
python3 -m research_lab.cl1_mitochondria model
python3 -m research_lab.cl1_mitochondria html --output /tmp/cl1-mitochondria.html
open /tmp/cl1-mitochondria.html
```

The generated HTML is self-contained and offline. It is a 3D-style educational representation of canonical mitochondrial anatomy, not an experimental reconstruction.

## CL1 simulator bridge

The existing safe bridge remains simulator-only:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install cl-sdk
python -m research_lab.cl1_simulator_bridge --simulator --seconds 3 --output cl1-sim-recording.h5
```

That recording can provide electrical neural data from the SDK simulator. It cannot establish mitochondrial morphology or metabolic state.

## Research upgrade path

1. Keep CL1 electrical recordings and mitochondrial evidence as separate provenance domains.
2. If future authorized microscopy data become available, ingest image metadata and segmentation provenance without replacing the generic reference model.
3. Add quantitative mitochondrial features only when directly measured (for example morphology, membrane potential, ROS, ATP/ADP, or respiration).
4. Never infer mitochondrial health directly from spiking activity without a validated multimodal experiment.
