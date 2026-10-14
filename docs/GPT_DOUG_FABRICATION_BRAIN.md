# GPT-Doug Fabrication Brain

Offline, deterministic engineering draft support for mechanical design, civilian vehicle subassemblies, welding, robotics and FDM 3D-printing review. This is not a machine controller, CAD-certified design, or safety certification.

## Run from the existing GPT-Doug checkout

```bash
python3 -m fabrication_brain status
python3 -m fabrication_brain demo --output build/fabrication-demo
open build/fabrication-demo/preview.html
python3 -m fabrication_brain plan examples/fabrication_brain/utility_rover.json --output build/custom-demo
python3 -m pytest tests/test_fabrication_brain.py -q
```

## Outputs

- `preview.html`: offline interactive box-proxy part visualization
- `assembly-preview.scad`: OpenSCAD bounding-box proxy
- `design.normalized.json`: normalized input
- `assembly-plan.json`: dependency-ordered, review-only assembly planning
- `assembly.mmd`: Mermaid dependency graph
- `bom.csv`: parts and source-supplied quantities/masses
- `review.json`: reproducible input hash, blocking issues, warnings, human review gates

Supported design schema: `xunia.fabrication.design.v1`; units must be mm. Categories: workshop_fixture, vehicle_subassembly, mobile_robot, robotic_cell, mechatronics. Process types: fdm_print, stock, machined, purchased. Joining types: weld, bolt, press_fit, adhesive.

The engine checks declared printer-bounding-box fit, qualified print materials, metal compatibility review, coarse robot reach, assembly dependency cycles and missing details. It **never** emits G-code, weld current/voltage, actuator trajectories, physical control commands, or production authorization.

All geometry is representative envelopes only; FEA, CAD tolerances, real weld sizing, qualified WPS/PQR, fatigue, cutting parameters, inverse kinematics, collision analysis, machine safety and market compliance remain unverified. Qualified humans must review physical work.

The existing `scripts/doug-max mecha` synthetic robotics research subsystem remains separate and unchanged. To use this feature branch, fetch the branch named `feat/fabrication-brain-offline-20261013` and execute the commands above.
