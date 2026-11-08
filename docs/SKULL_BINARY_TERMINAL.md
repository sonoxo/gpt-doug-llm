# SKULL BINARY TERMINAL — GPT-DOUG-LLM

A pure Python/macOS terminal renderer of a **real CC0 human skull GLB mesh**, rendered into 0/1 glyphs with a software z-buffer and perspective projection.

- No browser, ZIP, Pillow, virtual environment, paid model, API key, or Docker.
- A skull asset must be downloaded once (8.9 MB, CC0 Khronos ScatteringSkull) or provided as a local `.glb` file.
- Terminal preview is **not** live hardware/neuronal activity; no physical CL1 connection.
- Supports Mac Terminal/zsh; Python 3.10 or newer.

## Install (one command, from `~`)

```bash
curl -fL --retry 2 \
  https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/scripts/skull_binary_terminal.py \
  -o "$HOME/skull_binary_terminal.py" && \
python3 "$HOME/skull_binary_terminal.py"
```

The first run fetches the CC0 real anatomical 3D GLB from the Khronos sample repository and caches it at `~/.cache/gpt-doug-skull/ScatteringSkull.glb`. Later runs work offline (`--offline`).

## Controls

`A / D` orbit • `W / S` tilt • `+ / -` zoom • `P` pause • `1 / 2 / 3` front / angled / profile • `B` toggle glyph mode • `C` color palette • `Q` exit.

Save one static frame:

```bash
python3 "$HOME/skull_binary_terminal.py" --once --width 110 --no-color > "$HOME/Desktop/SKULL-BINARY.txt"
```

Use an existing local GLB without network:

```bash
python3 "$HOME/skull_binary_terminal.py" --model "$HOME/Downloads/ScatteringSkull.glb" --offline
```

## Licensing and verification

GLB asset: [Khronos Group ScatteringSkull](https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/ScatteringSkull), © 2025 Vladimir Petkovic, public-domain **CC0 1.0**. Material properties and optical subsurface scattering are not reproduced; geometry is projected as terminal binary glyphs. The renderer is code tested using synthetic valid GLB fixtures; actual appearance with the 8.9 MB downloadable skull remains unverified in the container's limited network environment.