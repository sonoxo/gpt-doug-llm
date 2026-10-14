# GPT-Doug MECHA (research-only, offline)

**Status:** local synthetic software, not an operational robot or military system. The
"mitochondrial" compute budget is an operation-count analogy. Quantum calculations
are classical statevector simulations. No biological chip, real quantum processor,
field vehicle, external network, or governmental credential is connected.

## Portable commands

From the GPT-Doug monorepo root:

```bash
PYTHONPATH=mecha python3 -m mecha.cli doctor
PYTHONPATH=mecha python3 -m mecha.cli demo --fixture mecha/examples/synthetic-inspection-rover.json --input-root mecha/examples
PYTHONPATH=mecha python3 -m mecha.cli watch --fixture mecha/examples/synthetic-inspection-rover.json --input-root mecha/examples --frames 3 --no-color
PYTHONPATH=mecha python3 -m mecha.cli quantum mecha/examples/bell-state.json --input-root mecha/examples --budget-units 200
```

All commands use local files inside an explicit input root. The synthetic rover
scenario is invented and cannot send actuator commands. The six displayed channels
are XYZ rendered-space plus time, memory/provenance and compute metadata, **not**
six physical spatial dimensions. A GitHub feature PR must pass review and CI before
merge. The root project license applies only to first-party code covered by it,
not to external patents, vendor hardware, branding or restricted data.
