# ZYRA Command Reference

Commands below are entered at the interactive `ZYRA >` prompt unless noted otherwise.

## Runtime

| Command | Action |
|---|---|
| `/status` | Show full runtime dashboard |
| `/fleet` | Show agent and worker inventory |
| `/fast` | Low-latency local chat mode |
| `/balanced` | Larger-context local chat mode |
| `/clear` | Clear chat memory |
| `/quit` | Exit ZYRA |

## Self-Heal

| Command | Action |
|---|---|
| `/heal` | Run one bounded local runtime repair pass |
| `/heal-status` | Show latest self-heal state |

Shell entrypoint:

```bash
python3 dougctl.py heal
```

## Native LASER

| Command | Action |
|---|---|
| `/laser-test` | Run deterministic circuit-breaker self-test |
| `/laser-status` | Show strikes, lock state, incidents |
| `/laser-reset` | Clear LASER lock/strike state |

The self-test does not execute an attack payload or target an external system.

## Agent Core

| Command | Action |
|---|---|
| `/agent-test` | Run deterministic Agent Core native self-test |
| `/agent-status` | Show mission budgets and latest mission |
| `/plan <goal>` | Produce a bounded autonomous plan |
| `/do <goal>` | Execute a bounded repository mission |
| `/evolve <goal>` | Improve ZYRA-owned runtime/agent/test code within the same gates |
| `/mission-status` | Show latest mission result |
| `/undo` | Restore the latest agent checkpoint |

Examples:

```text
/plan add a structured JSON mission journal
/do add a structured JSON mission journal
/evolve improve mission error classification and test it
/mission-status
```

## Terminal autostart

| Command | Action |
|---|---|
| `/default-on` | Open ZYRA automatically in new interactive terminal windows |
| `/default-off` | Disable ZYRA terminal autostart |

## Recommended first-run sequence

```text
/status
/laser-test
/agent-test
/agent-status
```

Then start with a planning mission before a write mission:

```text
/plan <goal>
/do <goal>
```
