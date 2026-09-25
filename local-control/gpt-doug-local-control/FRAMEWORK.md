# XUNIA-ZYRA GPT-Doug Local Control Framework

This package establishes five cooperating local frameworks:

1. **Authority framework** — `DISARMED` by default, explicit `ARMED` window capped at five minutes, and a persistent `PANIC` kill switch.
2. **Capability framework** — every action is classified as `read`, `control`, `write`, or `shell`; mutating classes fail closed unless armed.
3. **Transport framework** — the service listens only on `127.0.0.1:8765`, requires a random bearer token for POST actions, and accepts no public listener.
4. **Loop framework** — a two-second heartbeat records liveness and authority state. The loop never performs autonomous mutation.
5. **Audit framework** — actions are written to local JSONL evidence while typed text is omitted from logs.

## macOS authority boundary

Full Disk Access, Accessibility, and Screen Recording remain macOS TCC permissions. The framework can open the correct settings pane and detect failures, but it does not bypass or silently grant those permissions.

## Integration boundary

The Chrome gateway and this local control bridge are separate trust zones. A future bridge should remain loopback-only, authenticated, explicitly armed, and should preserve the same panic/disarm state machine.
