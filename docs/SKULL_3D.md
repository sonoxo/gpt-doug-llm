# SKULL-LLM // Terminal-first 3D Neural Command Center

**Primary entrypoint:** `biochip-cl1-skull-gpt-skull`. The terminal-based 3D
experience runs locally without a browser, WebGL, paid token, or cloud account.
The browser console remains available as an optional alternate view.

## V2 unlocked: real terminal command center

**Your Mac screenshot confirmed** the previous standalone cockpit rendering with
the local model showing READY. The V2 launcher keeps the same command and adds:

- **Adaptive HUD:** a widescreen status rail, or compact terminal fallback.
- **Perspective camera:** \`+\`/\`-\` zoom; \`1\` front, \`2\` three-quarter, \`3\` profile.
- **Real reasoning events:** the \`i\` command prints actual retrieve/draft/critique/
  revise phases. With \`ask --trace\`, phases are sent to stderr; generated
  answer stays on stdout. No simulated model tokens or fabricated token rates.
- **Status refresh:** \`g\` rechecks local Ollama readiness and the killswitch.
- **Safe snapshot:** \`v\` creates a new \`skull-snapshot-*.txt\` in the current
  directory, mode 0600, without overwriting existing files. An explicit
  \`snapshot --out FILE\` command also works.
- **Diagnostics:** display model, inference state, camera angle and measured
  rendering time (milliseconds) without claiming CL1 hardware data.

\`\`\`bash
# Update existing local feature-branch checkout:
cd ~/gpt-doug-skull && git pull --ff-only origin feature/skull-llm-neural-core-20261105
.venv/bin/python -m pip install -e .

# Run the upgraded cockpit:
OLLAMA_MODEL=qwen2.5-coder:7b .venv/bin/biochip-cl1-skull-gpt-skull

# Observe actual reasoning phases:
OLLAMA_MODEL=qwen2.5-coder:7b .venv/bin/biochip-cl1-skull-gpt-skull ask \
  "Describe the neural ontology" --trace

# Save ASCII visualization only (not prompts or conversations):
.venv/bin/biochip-cl1-skull-gpt-skull snapshot --out ./skull-view.txt
\`\`\`

The dedicated CLI is the preferred interface; \`skull-llm live\` also uses V2.
If the script is running from \`~\` in a different project, first \`cd\` into
your \`gpt-doug-skull\` checkout. Do not recreate the virtual environment if
it is already installed.

No physical CL1 hardware connection exists; the visible signals remain a
synthetic visual effect. Use hardware-specific interfaces only after separate
documented integration and verification.

## Terminal first: BIOCHIP-CL1-SKULL-GPT-SKULL

From the checked-out SKULL-LLM feature branch:

```bash
python3 -m pip install -e .
biochip-cl1-skull-gpt-skull                 # interactive rotating 3D ASCII skull
biochip-cl1-skull-gpt-skull --once          # one static 3D snapshot, no TTY required
biochip-cl1-skull-gpt-skull --frames 24     # 24 real rotated frames, then exit
biochip-cl1-skull-gpt-skull status          # observed Ollama readiness; no fabricated CL1 readings
skull-llm live --once                      # same interactive renderer via existing CLI
```

In the live cockpit: **a/d** rotate, **w/s** tilt, **n** toggle the synthetic
neural overlay, **p** pause/resume, **r** reset view, **i** enter a local LLM
prompt, **q** quit. Terminal settings are restored on exit. Redirected output
or a non-TTY defaults to a single static frame. The renderer uses an actual
yaw/pitch perspective transformation and depth buffer over thousands of
procedurally sampled 3D bone points; it is not a pre-rendered ASCII image.

Local inference (requires Ollama running and the configured model installed):

```bash
ollama pull qwen2.5-coder:7b
OLLAMA_MODEL=qwen2.5-coder:7b biochip-cl1-skull-gpt-skull ask "Design the neural ontology"
```

`--depth 1|2|3` controls bounded inference passes. Memory is not written
unless `--remember` is explicitly used with the `ask` command.

**CL1 truth boundary:** this command implements a simulated *biochip-inspired*
visualization. It has no API link to a physical CL1 device, does not measure
neuronal action potentials, and never labels generated activity as live
hardware telemetry. The actual Ollama model readiness is independently
reported as READY/OFFLINE/STOPPED. No invasive or laboratory operation is
performed.

## Optional browser experience

An original, interactive **3D skull and neural-network interface** integrated with the existing SKULL-LLM local inference engine in `sonoxo/gpt-doug-llm`. Free, self-hosted, and intended to run on the owner's Mac. No API tokens, paid APIs, CDN scripts, proprietary model cloning, or unrestricted external actions.

## Launch

In a checkout of the `feature/skull-llm-neural-core-20261105` branch:

```bash
python3 -m pip install -e .
ollama pull qwen2.5-coder:7b
OLLAMA_MODEL=qwen2.5-coder:7b skull-llm serve --port 7861
```

Open **http://127.0.0.1:7861/** on the same computer. Ollama must be running (start the Ollama app or `ollama serve` first). If the configured model is missing/offline, 3D visuals still run, but live chat reports offline status and fails visibly.

A source checkout without an installed console script can run `python3 -m skull_llm serve --port 7861`.

## Interface

- **Real-time 3D:** WebGL2 procedural mesh, animated cranium, hollow eye-socket look, jaw and teeth, layered cortex, orbital rings, point/line synaptic graph. No downloaded 3D asset or remote rendering service.
- **Anatomy / Neural fusion / X-ray:** interactive state toggles alter the rendered geometry's appearance.
- **Orbit and zoom:** drag to rotate, scroll to zoom, double-click or use Reset View. Reduced-motion preference disables automatic orbit initially.
- **CPU 3D fallback:** canvas-based perspective point-cloud scene if a browser or administrator disables WebGL2; remains interactive but with lower visual fidelity/performance.
- **Real phase events:** local model's `retrieve`, `draft`, `critique`, `revise`, `complete` phases are delivered over newline-delimited JSON and visibly animate the neural sculpture. These reflect real execution stages, not artificial token counts.
- **Local chat:** uses the bounded `SkullEngine` and existing ontology/memory. Browser displays the actual answer after completion. Depth 1/2/3 configures actual inference passes.
- **Memory:** Save locally is unchecked by default; opt in per request. Nothing is persisted by the browser. The backend's existing memory secret checks still apply.

**Realism note:** the procedural model is a stylized anatomy-inspired visualization, not an anatomically exact CT reconstruction. It is an interactive 3D mesh, not a static image or video. Inference is local but the 3D render and movement are frontend graphics—not a new pretrained brain or proof of intelligence.

## Security

- HTTP server binds to **127.0.0.1 only** by default; non-loopback bind is rejected.
- Explicit allowlist for static assets and API routes. No directory traversal/file uploads.
- `Host` and `Origin` are validated for loopback/same-port access; strict content-security policy blocks external scripts.
- Request size is limited to 16 KiB; prompt to 8,000 characters; depth to 1/2/3. Server does not log prompt/response bodies.
- Model inference still honors the main GPT-Doug emergency stop and local Ollama endpoint validation.
- The browser has no external script, font, telemetry, or CDN dependencies.

## Validate

```bash
python3 -m unittest tests.test_skull_3d -v
python3 -m unittest tests.test_skull_llm -v
node --check skull_llm/static/skull.js
node --check skull_llm/static/fallback.js
```

A CPU/Pillow/Skull model is not necessary for the browser UI tests. To test live inference, install Ollama, pull a compatible model, and verify `skull-llm doctor` reports ready. This web server does not deploy a public site or bypass Palantir/Foundry access controls.
