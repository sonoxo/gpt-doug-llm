# GPT-DOUG Clawbot Mode

GPT-DOUG can operate as a local computer agent by attaching `ComputerToolbox` to the existing Wakeup3lm runtime. The design follows the repository's existing contract: **the model proposes; explicit tools execute; side effects are approval-gated; results are recorded in the ontology.**

## Capabilities

- **Shell:** run commands inside the configured workspace; read-only inspection commands can run immediately, while side-effecting commands require `approve=True`.
- **Managed browser:** open HTTP(S) pages, read page text, click, type, and take screenshots through Playwright. Click/type are approval-gated.
- **Desktop:** screenshots plus coordinate click, typing, and hotkeys through PyAutoGUI. Input actions are approval-gated.
- **Filesystem:** continue using Wakeup3lm's existing workspace-scoped file tools.
- **Audit:** `attach_computer_tools()` registers the capabilities in the existing Wakeup3lm tool registry and ontology.

## Install optional computer-control dependencies

```bash
python3 -m pip install playwright pyautogui
python3 -m playwright install chromium
```

The shell capability has no third-party dependency.

## Run it directly

```bash
python3 -m wakeup3lm.computer_agent --workspace . status
python3 -m wakeup3lm.computer_agent --workspace . shell pwd
python3 -m wakeup3lm.computer_agent --workspace . shell --approve touch clawbot-mode-ok.txt
python3 -m wakeup3lm.computer_agent --workspace . browser-open https://example.com
```

## Attach it to GPT-DOUG / Wakeup3lm

```python
from wakeup3lm import Wakeup3LM
from wakeup3lm.computer_agent import attach_computer_tools

runtime = Wakeup3LM(".")
toolbox = attach_computer_tools(runtime)

print(runtime.tool_schema)
print(runtime.execute({"action": "computer_status", "arguments": {}}).output)
```

The model can then propose tool calls such as `run_shell`, `browser_open`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_screenshot`, `desktop_screenshot`, `desktop_click`, `desktop_type`, and `desktop_hotkey`.

## Safety boundary

Clawbot Mode is powerful by design, but it is not a hidden remote-access mechanism. It stays bound to the selected local workspace, browser URLs are restricted to HTTP(S), interactive browser/desktop actions require an explicit approval flag, and common catastrophic host-level shell commands are blocked. macOS may separately require Accessibility and Screen Recording permission before PyAutoGUI can control the desktop.
