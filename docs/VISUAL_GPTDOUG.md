# Visual GPT-Doug // Canonical Local Foundation

GPT-Doug's visual shell is a **local terminal embodiment** layered over the repository's governed agentic runtime. The visual layer does not replace the core. It reads the same ontology, state, and control boundaries.

## Canonical architecture

```text
ONTOLOGY
   ↓
GENOME / PHENOTYPE
   ↓
EMBODIMENT
   ↓
HUD + MATRIX
   ↓
KNOWLEDGE + SKILLS + RESEARCH
   ↓
MAX CONTROL
   ↓
USER-AUTHORIZED ADMIN
```

The permanent local paths are:

```text
~/.config/gptdoug/
└── canonical/
    ├── ontology.json
    ├── runtime.py
    └── hud.py

~/.local/bin/
├── gptdoug
├── gptdougmax
├── gptdoug-max
├── dougctl
└── dougsec
```

## Permanent foundation launcher

This is the canonical launch pattern used by GPT-Doug:

```bash
export PATH="$HOME/.local/bin:$PATH"; export GPTDOUG_HOME="$HOME/.config/gptdoug"; export GPTDOUG_ONTOLOGY="$HOME/.config/gptdoug/canonical/ontology.json"; clear; [ -x "$HOME/.local/bin/gptdoug" ] && "$HOME/.local/bin/gptdoug" || python3 "$HOME/.config/gptdoug/canonical/runtime.py"
```

The master menu is:

```bash
export PATH="$HOME/.local/bin:$PATH"; clear; "$HOME/.local/bin/gptdougmax"
```

Recommended persistent aliases:

```text
gptmax   → master menu
doughud  → visual HUD / embodiment
dougcore → Matrix core
dougmax  → MAX execution broker
dougsec  → authorized security-lab mode
```

## Source artwork

The renderer can use a local source image without committing personal artwork into the repository. Preferred search order:

```text
~/Pictures/gptdoug-alive(4).png
~/Pictures/gptdoug-alive(3).png
~/Pictures/gptdoug-alive(2).png
~/Pictures/gptdoug-alive.png
~/Pictures/**/*gpt*doug*.png
```

A good source image has:
- black or near-black background;
- centered head-and-shoulders silhouette;
- strong cyan/red/magenta edge separation;
- visible eyes and facial structure;
- enough shadow detail to survive ASCII quantization.

## Visual behavior

The canonical embodiment is intended to expose the ontology rather than act as a disconnected screensaver.

```text
DREAMING    → low energy / deeper Matrix
OBSERVING   → stable gaze / lower glitch
THINKING    → stronger eyes / cognitive pulse
SPEAKING    → mouth animation / active response
LOCKED_IN   → high focus / narrow noise
ADMIN       → explicit control state
```

Expected controls:

```text
q  HUD / return routing
m  MAX menu
d  DREAMING
o  OBSERVING
t  THINKING
s  SPEAKING
a  ADMIN
g  glitch surge
r  regenerate phenotype
```

## Terminal requirements

The visual runtime is designed for a true-color terminal. For best results:
- use a dark terminal profile;
- enable 24-bit color;
- use a monospaced font;
- keep the terminal large enough for at least ~80 columns;
- install ImageMagick only when using image-to-ASCII conversion.

The visual layer should remain optional. Headless, CI, and server deployments should continue to use the core runtime without a TTY.

## Control rule

**Never let a HUD overwrite the core runtime.**

Keep these identities separate:

```text
gptdoug      → canonical runtime / embodiment
gptdoug-hud  → HUD only
gptdougmax   → master menu
gptdoug-max  → execution broker
```

This separation prevents a visual failure from destroying the canonical foundation.
