# GPT-Doug MECHA — Offline Warfighter Research Core

**Release status:** This capability exists only on the reviewed feature branch until
its pull request passes independent review and is merged. It is a synthetic,
local-first **software demonstrator**, not a military-certified exoskeleton or
physical robot. Agent10 is an unverified, private self-declared pseudonym.

## Commands

```bash
# Execute in a checkout that includes the MECHA feature branch
bash scripts/doug-max mecha doctor
bash scripts/doug-max mecha demo --fixture mecha/examples/synthetic-inspection-rover.json --input-root mecha/examples
bash scripts/doug-max mecha watch --fixture mecha/examples/synthetic-inspection-rover.json --input-root mecha/examples --frames 3 --no-color
bash scripts/doug-max mecha quantum mecha/examples/bell-state.json --input-root mecha/examples --budget-units 200

# Test the standalone portable package without any GPT-Doug dependencies
PYTHONPATH=mecha python3 -m mecha.cli doctor
```

The finite rover moves only **synthetic coordinates** and consumes **abstract
compute/power units**; it has no driver, credential, ROS/flight API, navigation
endpoint, person tracking, targeting, weapon, or autonomous motion command.
The six channel labels are X/Y/Z rendered-space plus simulation time,
provenance/memory, and compute-cost metadata; no physical extra dimensions.
The Bell example computes classical probabilities 0.5 for 00 and 11 from
H(0) and CNOT(0,1), costing 12 abstract operation units. No quantum hardware,
biological hardware, measured ATP, wet lab, live military/sensor connection,
or government endorsement is provided.

## Host integration

`integrations/mecha_bridge/adapters.py` is **optional**. It may read BioPINEAL
heartbeat and private local Agent10 callsign **only when explicitly selected**;
the standalone CLI never imports the bridge, and public snapshots omit callsigns,
filesystem paths, and private PINEAL notes. Missing optional integrations report
`ADAPTER_UNAVAILABLE`. The pre-existing GPT-Doug launcher guardrail preflight
remains active for all `mecha` commands. Any actual physical robot control or
hardware design requires a separate specification, device authorization, risk
assessment, independent safety validation, and relevant legal/IP review.

## Testing

```bash
PYTHONPATH=mecha:. python3 -m unittest discover -s mecha/tests -p 'test_*.py' -v
PYTHONPATH=mecha:. python3 -m unittest tests.test_mecha_bridge tests.test_mecha_guarded_entry -v
bash -n scripts/doug-max
```

The MIT software license (where applicable) does not confer rights to
third-party patents, device access, or vendor trade marks. Blender visualization
and the standalone `sonoxo/mecha` repository are later, separately reviewed work.
