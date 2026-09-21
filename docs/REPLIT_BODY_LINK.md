# GPT-Doug Replit Body Link

Workspace identity:

`https://replit.com/@24kmediaproduct/GPT-Doug-AI-Hub`

The workspace URL is provenance only. GPT-Doug must connect to the app's deployed
HTTPS endpoint, normally a `*.replit.app` URL or a custom domain.

## Network model

```text
GPT-DOUG LOCAL / UNIVERSAL HIVE
        |
        | HTTPS + HMAC-SHA256
        | timestamp + nonce + challenge
        v
REPLIT DEPLOYMENT
GPT-Doug-AI-Hub
        |
        +-- /health
        +-- /v1/handshake
        +-- /v1/heartbeat
        +-- /v1/state      (signed POST, safe GET snapshot)
        +-- /v1/stream     (same-origin SSE for the browser avatar)
```

The body-link protocol intentionally exposes no remote shell and no arbitrary
command endpoint. Body-Link V2 adds a sanitized live state plane while preserving
`gptdoug-body-link-v1` wire compatibility for handshake and HMAC signatures.

## Replit side

Put the `body_link/` package in the Replit project, set the Replit Secret
`GPT_DOUG_BODY_LINK_KEY` to the same strong random value used by the local
controller, then run:

```bash
python -m body_link.server
```

The server binds to `0.0.0.0` and honors Replit's `PORT` environment variable.

For a persistent API/body node, publish the project as a Replit Deployment.
Autoscale is suitable when wake-on-request latency is acceptable. A Reserved VM
is the stronger fit when a continuously warm node is required.

## GPT-Doug controller side

Configure the deployed HTTPS endpoint and the same secret:

```bash
export GPT_DOUG_BODY_URL="https://YOUR-DEPLOYED-NODE.replit.app"
export GPT_DOUG_BODY_LINK_KEY="<same-secret-as-replit>"
```

Then:

```bash
gpt-doug-body link
gpt-doug-body ping
gpt-doug-body status
gpt-doug-body state LEARN --detail "archive + critic review"
gpt-doug-body demo --interval 2
gpt-doug-body watch --interval 30
```

Inside the main GPT-Doug terminal:

```text
/body
/body link
/body ping
```


## Body-Link V2 live state

The controller converts GPT-Doug runtime transitions into a sanitized body-state
packet. Canonical states are:

`IDLE LISTEN THINK TALK ACT LEARN POWER ERROR SLEEP`

`POST /v1/state` is HMAC-authenticated and accepts only the whitelisted animation
schema. Unknown fields such as credentials, passwords, or private keys are dropped
by the sanitizer. The server keeps only the latest sanitized animation state.

The browser does **not** receive the HMAC key. It reads the same-origin stream:

```js
const stream = new EventSource('/v1/stream');

stream.addEventListener('body_state', (event) => {
  const packet = JSON.parse(event.data);
  const body = packet.body_state;

  // Feed these values into the existing Three.js animation/state store.
  // body.state is one of:
  // IDLE LISTEN THINK TALK ACT LEARN POWER ERROR SLEEP
  applyGptDougBodyState(body);
});
```

The current snapshot is also available at:

```text
GET /v1/state
```

The MAX shell uses a latest-state-only background relay, so animation network
latency never blocks the command shell. State changes such as `THINK`, `TALK`,
`LISTEN`, `ACT`, `POWER`, and `ERROR` are forwarded automatically whenever
the remote body is configured.

### LEARN packet

```json
{
  "schema": "gptdoug/body-state-v1",
  "state": "LEARN",
  "emotion": "curious",
  "intensity": 0.8,
  "eyes": {"focus": 0.9, "blinkRate": 0.18},
  "mouth": {"active": false, "viseme": "rest", "amplitude": 0.0},
  "head": {"yaw": 0.0, "pitch": -0.03, "roll": 0.0},
  "voice": {"active": false},
  "microphone": {"active": false},
  "speaker": {"active": false},
  "learning": {"active": true, "pulse": 0.8}
}
```

Recommended Three.js mapping for `LEARN`: focused eyes, subtle head micro-motion,
continued breathing, cyan/magenta neural pulse, and an active ontology/memory HUD.
The controller supplies state; the Replit renderer owns interpolation and visual
presentation.

## Authentication protocol

Every mutating body-link request includes:

- Unix timestamp
- unique random nonce
- SHA-256 hash of canonical JSON body
- HMAC-SHA256 signature over protocol, method, path, timestamp, nonce, and body hash

The node rejects stale signatures and replayed nonces. The handshake includes an
independent challenge which must be echoed by the node. Responses are signed too,
so the controller authenticates the node before persisting link state.

## Secret handling

Never commit `GPT_DOUG_BODY_LINK_KEY` to either repository. Store it in Replit
Secrets on the body side and in the local secret/environment manager on the
controller side. Persistent state contains the endpoint, node identity, heartbeat
timestamps, capabilities, Hive ID, and ontology hash - not the secret.

## Current authority boundary

The body link provides identity, presence, heartbeat, and Hive provenance. It is
not a remote shell, arbitrary-code executor, autonomous escape mechanism, or
unbounded actuation channel. Future capabilities should be separately allowlisted,
authenticated, authorized, audited, and reversible.
