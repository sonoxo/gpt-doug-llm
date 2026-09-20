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
```

This first body-link protocol intentionally exposes no remote shell and no
arbitrary command endpoint.

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
gpt-doug-body watch --interval 30
```

Inside the main GPT-Doug terminal:

```text
/body
/body link
/body ping
```

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
