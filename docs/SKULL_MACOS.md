# SKULL OS — native macOS desktop application

**SKULL OS** is a native **SwiftUI + WKWebView** desktop shell for the local
SKULL-LLM 3D cockpit. It is an application, **not a replacement macOS operating
system, kernel or hypervisor**. It works with the real SKULL-LLM repository and
the local Ollama inference engine. CL1 neural graphics are a simulation.

## Build once on an Apple Silicon or Intel Mac

Requires macOS 13 or newer, Xcode Command Line Tools (`xcode-select --install`
if needed), a local Python virtual environment, and the SKULL feature branch.
No paid Apple Developer Program membership is required for a locally built app.

```bash
cd ~/gpt-doug-skull
git pull --ff-only origin feature/skull-llm-neural-core-20261105
# Reuse the existing .venv; it won't modify Homebrew's system Python.
.venv/bin/python -m pip install -e .
bash macos/build-app.sh --open
```

The build script produces **`dist/SKULL OS.app`** and launches it as a real
macOS window. You can later double-click the `.app` in Finder or run:

```bash
open "$HOME/gpt-doug-skull/dist/SKULL OS.app"
```

The app is ad-hoc signed for the local machine, **not Apple notarized** or
suitable for public distribution without additional signing and review.
Do not bypass macOS security prompts or Gatekeeper; if a security restriction
appears, use your normal macOS trust process for software you built yourself.

The app references the existing checkout's **absolute** `.venv/bin/python`
location. If you move or rename the repository, rebuild the `.app`. A previous
app build is preserved with a timestamp on rebuild.

## Native macOS functionality

- Resizable native window, macOS title bar, toolbar, sidebar, and menu items.
- Live interactive WebGL 3D cockpit (with existing software-rendered fallback),
  3D modes, orbital motion, zoom, real local LLM conversation, and phase events.
- Shortcuts: **Cmd+1/2/3** (Fusion, Anatomy, X-Ray), **Cmd+K** (focus the LLM
  prompt), **Cmd+0** (recenter), **Cmd+R** (refresh model readiness),
  **Cmd+Shift+S** (export window PNG).
- Native diagnostics, Ollama status, model name, emergency-stop indication,
  and one-click copy of the existing terminal launcher command.
- Automatically starts the existing Python loopback web service at port 7861
  if none is running. If the service is already running, the app reuses it and
  **does not terminate your service on exit**. If the app starts the service,
  it stops only its own child process on normal app termination.

The service is HTTP on **127.0.0.1 only**, never remotely exposed. The WKWebView
allows navigation only to this local endpoint, uses a nonpersistent web data
store, and disallows new browser windows. The bundled `Info.plist` grants
local-network loads rather than the insecure global arbitrary-load exception.
No cloud account, hosted API, remote script or external website is needed.

## Troubleshoot

```bash
cd ~/gpt-doug-skull
.venv/bin/skull-llm doctor
OLLAMA_MODEL=qwen2.5-coder:7b .venv/bin/skull-llm serve --port 7861
```

A `READY` model requires a running Ollama installation and locally installed
model. A disconnected model does **not** disable 3D graphics. If a different
program occupies port 7861, stop that program **only if it is yours** or
change the app port in the local builder and service configuration deliberately.
The app refuses to treat an unrelated service as SKULL-LLM.

## Validation

```bash
bash -n macos/build-app.sh
swift build --package-path macos/SkullOS -c release
python3 -m unittest tests.test_skull_macos_packaging -v
```

The SwiftUI app itself must be compiled and exercised on macOS; Linux cannot
execute AppKit, SwiftUI or WKWebView. The browser fallback and local HTTP
interface remain separately tested.
