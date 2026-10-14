# GPT-Doug CL1 organoid digital twin + evidence swarm

This feature uses the public Cortical Labs `cl-sdk` interface in **simulator-only** mode and a bounded public-evidence crawler.

It does **not** grow cells, create a physical organoid, stimulate living tissue, attach to a physical CL1, or connect to arbitrary global infrastructure.

## Architecture

```text
CL1 SDK simulator
      |
      v
synthetic neural recording
      |
      v
organoid digital twin -----> GMRO provenance graph
                               ^
                               |
               allowlisted public evidence swarm
                               |
                               v
                         human review gate
```

## Simulator

```bash
python3.12 -m venv .venv-cl1
. .venv-cl1/bin/activate
python -m pip install cl-sdk
python -m research_lab.cl1_organoid_swarm simulator --seconds 3 --output cl1-organoid-sim.h5
```

The command refuses a known physical CL1 installation marker and never issues stimulation calls.

## Public evidence swarm

```bash
python -m research_lab.cl1_organoid_swarm evidence-swarm --workers 4
```

The swarm reads only the explicit HTTPS source allowlist in
`intel/sources/cl1-organoid-authorized-sources.json`. Redirects remain HTTPS,
responses are size-bounded, and no credentials, login sessions, private APIs,
device targets, or arbitrary hostnames are accepted.

## Topology

```bash
python -m research_lab.cl1_organoid_swarm topology
```

This prints the software graph for the simulator, digital twin, evidence swarm,
GMRO, and human-review boundary.

## Why this is not called a "real organoid"

Source code can interface with supported CL1 software, but it cannot manufacture
living tissue. A physical organoid requires wet-lab cell culture, sterile
handling, biological provenance, ethics/biosafety review, and institutionally
approved procedures. This repository therefore keeps software simulation and
biological experimentation as separate domains.
