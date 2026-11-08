# BIOCHIP-CL1 // FULL BODY TERMINAL

An offline **full-body 3D** binary renderer for GPT-DOUG-LLM. It extends the
existing [real-mesh skull terminal](SKULL_BINARY_TERMINAL.md) with an
anatomy-*inspired* articulated whole figure: cranium, jaw, vertebrae, paired
ribs, sternum, clavicles, pelvis, arms, hands, individual digits, femurs,
kneecaps, lower legs, ankles and feet. A separate simulated neural network
runs from the cranium through an abdominal hub to the limbs.

**Truth boundary:** the full-body geometry is generated algorithmically, not
scanned anatomy or a clinical 3D medical model. The CL1-inspired computational
and neural layers are **software simulations only**, with no biological CL1
neurons or hardware attached. The offline 3D rotation is real geometry,
perspective projection and a CPU depth buffer, drawn as terminal glyphs.

## Mac terminal: one command, no ZIP or Python packages

If you are currently running the skull, press **Q** first. Paste this in
your existing terminal from **any directory**:

\`\`\`bash
curl -fL --retry 2 \
  https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/scripts/cl1_body_terminal.py \
  -o "$HOME/cl1_body_terminal.py" &&
python3 "$HOME/cl1_body_terminal.py"
\`\`\`

While this file is in an open PR and not yet merged, use the feature branch
raw URL instead of \`main\`. After merge, the command above works unchanged.

No external GLB, photo, package manager or network access is required after
the initial script download. You can also run an existing local copy
offline with \`python3 ~/cl1_body_terminal.py\`.

## Controls

| Key | Effect |
|---|---|
| A / D | Orbit 3D figure |
| W / S | Tilt |
| + / - | Zoom |
| 1 | Fusion: skeletal structure + simulated CL1/neural layer |
| 2 | Skeleton: ribs, skull, spine, hands, legs, pelvis |
| 3 | Neural simulation |
| 4 | Body/surface contours |
| H | Zoom to head |
| T | Zoom to torso |
| F | Restore entire full-body camera |
| B | Switch 0/1 binary / depth-shaded glyph mode |
| C | Cycle cyan, bone, amber, green |
| P | Pause or resume |
| Q | Exit and restore terminal |

## Diagnostics / no-TTY output

\`\`\`bash
python3 ~/cl1_body_terminal.py --once --no-color --width 110 --height 56
python3 ~/cl1_body_terminal.py --once --mode skeleton --no-color
python3 ~/cl1_body_terminal.py --frames 24 --fps 10 --detail light
\`\`\`

The \`--detail light\` mode reduces model sampling to keep frame rates responsive
on modest CPUs. Default mode generates roughly 80k 3D surface samples.
No secrets, credentials or model prompts are read, stored or transmitted.

Validation is performed with:

\`\`\`bash
python3 -m unittest tests.test_cl1_body_terminal -v
\`\`\`

The test suite verifies full-body bounds, paired limbs, all geometry layers,
binary-only output, animation view changes and one-frame offline operation.
