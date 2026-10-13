# BioPineal × Cortical Labs CL1: simulator integration

## What this does
Adds a **read-only**, **simulator-only** CL1 API example to GPT-Doug. This does **not** fabricate an organoid, grow neurons, claim real learning, or communicate with a physical CL1.

Official sources:
- https://docs.corticallabs.com/
- https://docs.corticallabs.com/cl
- https://pypi.org/project/cl-sdk/
- https://github.com/Cortical-Labs/cl-api-doc/

## Local installation (Python 3.12+)
```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install cl-sdk
python -m research_lab.cl1_simulator_bridge --simulator --seconds 3 --output cl1-sim-recording.h5
```

Cortical Labs documents `cl.open()` and `neurons.record()` as the preferred recording interface. The simulator normally provides synthetic, non-learning neural activity, so its output cannot establish biological learning or functional organoid behavior.

## Scope and safety
- Requires explicit `--simulator`; refuses known physical CL1 installation marker `/opt/cl-api-whl`.
- Makes no stimulation or actuation calls.
- Recording runs for at most 10 seconds, then stops.
- This marker is not a comprehensive physical-hardware detector; launch only in a dedicated local simulator virtual environment.
- The recorded HDF5 file is a research artifact, not personal or physiological measurement.
- Do not connect agent swarm execution to real biological stimulation.

## Hardware roadmap (requires specialists and authorization)
1. Validate sensor/recording data schema and provenance.
2. Measure simulated network firing statistics from HDF5 using documented `cl.RecordingView` analysis routines.
3. Introduce a read-only ontology adapter for approved research artifacts.
4. Review ethics, biosafety, cellular-source provenance, experimental design and institutional approvals.
5. Obtain CL1 or authorized Cortical Cloud access and conduct separately approved, human-supervised experiments.

The CL1 architecture uses living neurons cultured on a silicon multielectrode interface. This project implements software integration only, not the biological substrate.
