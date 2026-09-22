# GPT-Doug Local Chaotic Good Control

A local macOS control bridge for XUNIA / ZYRA / GPT-Doug workflows.

## Established frameworks

- **Authority:** `DISARMED` -> temporary `ARMED` -> `PANIC`
- **Capability:** read / control / write / shell classification
- **Transport:** loopback-only `127.0.0.1:8765` with bearer authentication
- **Loop:** 2-second health/authority heartbeat; no autonomous mutation
- **Audit:** local JSONL evidence with typed text excluded

See `FRAMEWORK.md` and `framework.json`.

## Security model

- binds **only** to `127.0.0.1:8765`
- validates the loopback Host header
- random local bearer token stored in `runtime/token.txt` with mode `0600`
- starts **read-only / DISARMED**
- UI/control/write/shell actions require an explicit **5-minute arm**
- one-command **PANIC STOP**
- audit log does not record typed text
- sensitive credential/keychain locations are blocked by policy
- shell execution accepts an `argv` array only; no `shell=True`
- no remote command server, cloud callback, or public listener

## macOS permissions

macOS TCC permissions cannot be silently granted by code. You must approve the app/Terminal/Python process yourself in **System Settings > Privacy & Security**.

For the capabilities below, grant permission to the terminal/app that launches `server.py`:

- **Full Disk Access** — broad filesystem visibility
- **Accessibility** — mouse/keyboard automation
- **Screen & System Audio Recording** — screenshots/screen inspection

Run `open-permissions.command` to open the relevant settings pane.

## Start

1. Double-click `open-permissions.command` and approve the permissions you actually want.
2. Double-click `start.command`.
3. Open `http://127.0.0.1:8765`.
4. Read operations work immediately. Click **ARM 5 MIN** before click/type/write/shell operations.

## Loop

A heartbeat thread writes `runtime/heartbeat.json` every ~2 seconds with the current authority state. It performs no autonomous click/type/write/shell actions. The HTTP service stays running until you close its terminal window or press Ctrl-C. A background LaunchAgent is intentionally not auto-installed.

## Examples

Read home directory:

```json
{"type":"list_dir","path":"~"}
```

Open Chrome after arming:

```json
{"type":"open_app","app":"Google Chrome"}
```

Screenshot:

```json
{"type":"screenshot"}
```

Run a local command after arming:

```json
{"type":"run_command","argv":["git","status"],"timeout":60}
```

## Kill switch

```bash
./ctl.py panic
```

Clear it manually with:

```bash
./ctl.py clear-panic
```
