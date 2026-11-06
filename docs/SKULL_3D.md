# SKULL-LLM // Live 3D Neural Command Center

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
