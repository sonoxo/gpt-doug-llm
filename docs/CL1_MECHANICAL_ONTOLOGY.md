# BIOCHIP-CL1 // Skeleton Mechanical Ontology

**Applies to:** GPT-DOUG-LLM full-body `0/1` Terminal renderer. The canonical
visualization remains **exposed bones, bone-white binary glyphs**, with no
solid-body shell or medical scan.

## Interactive on-screen inspector

Update your copy of the standalone renderer and run it from any directory:

```bash
curl -fL --retry 2 \
  https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/scripts/cl1_body_terminal.py \
  -o "$HOME/Downloads/cl1_body_terminal.py" &&
python3 "$HOME/Downloads/cl1_body_terminal.py" --mode skeleton --color bone --no-spin
```

Press **O** to hide/show the mechanical ontology HUD and linked 3D joint
locator. Use **]** for the next skeletal entity and **[** for the previous
entity. All existing rendering controls (A/D, W/S, 1–4, H/T/F, B/C, P, Q)
remain available. No external dependencies, GLB file, browser or paid API.

The overlay shows the selected anatomical link, its parent in the mechanical
hierarchy, joint type, degrees of freedom, length, mass estimate, inertia,
virtual spring/damping coefficients and constrained ranges (degrees).

## Structured ontology export and mechanical evaluation

```bash
# Export 19 typed skeletal links and 18 parent-child relations as JSON.
python3 ~/Downloads/cl1_body_terminal.py --ontology-json > ~/Desktop/CL1-MECH-ONTOLOGY.json

# Query one virtual rigid-link and its joint limits.
python3 ~/Downloads/cl1_body_terminal.py --inspect left_forearm

# Demonstrate a bounded virtual spring-damper torque calculation at 65 degrees
# of elbow flexion and an angular speed of 15 degrees/second.
python3 ~/Downloads/cl1_body_terminal.py --inspect left_forearm \
  --joint-angle 65 --joint-speed 15

# Change the modeled nominal body mass (default: 70 kg); affects estimated
# skeletal mass and rod-axis inertia ONLY.
python3 ~/Downloads/cl1_body_terminal.py --ontology-json --body-mass 80
```

The document has JSON-LD-style `@context`, `components` and `relations` arrays
suitable for mapping into a GPT-DOUG/XUNIA ontology. It does **not** directly
create Palantir Foundry objects, update external databases or actuate motors.

## Mechanical model and limitations

| Field | Scope and units |
| --- | --- |
| Rigid link and parent | 19 procedural skeletal segments, parent-child graph |
| Joint types | Fixed, hinge, universal (two axes) and ball/socket (three axes) |
| Degrees of freedom | Number of configured rotational axes |
| Joint angular limits | Degrees; simulation clamps **nothing** and reports out-of-range instead |
| Estimated mass | kg, based on illustrative **15%** bone-system share of modeled body mass |
| Nominal length | Metres, using artistic scale `0.315 m/model unit` |
| Rod-axis inertia | kg·m²; simplified uniform slender rod, `I = mL²/12` |
| Virtual joint stiffness | N·m/rad, **invented simulation parameters** |
| Virtual damping | N·m·s/rad, **invented simulation parameters** |
| Virtual restoring torque | N·m, `−Kθ − Cω`, returned only for in-range angle |

**These are engineering *demonstration* parameters, not calibrated human
biomechanics, clinical measurements, biological CL1 neuron readings or real
robotic motor specifications.** The script does not animate joint flexion or
send an actuation command. The actual on-screen skeleton remains a procedural
3D model, not anatomy reconstructed from imaging.

Export, inspection and mechanical evaluation are offline and read-only; no
sensitive health information, external cloud APIs or hardware interaction.

## Validation

```bash
python3 -m unittest tests.test_cl1_body_terminal tests.test_cl1_mech_ontology -v
```

Tests cover graph structural integrity, mass-fraction accounting, valid joint
limits, bounded virtual spring/damping behavior, JSON export without geometry
or network, binary 3D locator state, and the existing full-body renderer.