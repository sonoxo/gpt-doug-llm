# GPT-Doug Monero Neural Layer

The Monero neural layer is an off-chain neural provenance and verification layer
with optional Monero settlement references.

## Design

```text
neural job
  -> GPT-Doug / workers
  -> GPT-Chaos critic
  -> verifier
  -> neural receipt
  -> human-authorized settlement proposal
  -> external signer
  -> Monero tx reference
```

Monero remains the monetary settlement network. Neural inputs, prompts, model
weights, and outputs are **not** written to Monero. The local neural ledger
stores hashes and compact provenance metadata only.

## Safety and custody boundary

- No private spend key is accepted or persisted.
- No transfer/broadcast method exists in the neural layer.
- Settlement proposals require explicit human authorization.
- A transaction ID can only be attached after authorization.
- The default development RPC endpoints target local stagenet-style ports.
- Use a view-only wallet RPC for observation whenever spending is unnecessary.

## Environment

```bash
export GPT_DOUG_XMR_NEURAL_STATE_DIR="$HOME/.gpt-doug/monero-neural"
export MONERO_DAEMON_RPC="http://127.0.0.1:38081/json_rpc"
export MONERO_WALLET_RPC="http://127.0.0.1:38088/json_rpc"
```

Optional HTTP basic-auth variables:

```bash
MONERO_DAEMON_RPC_USER
MONERO_DAEMON_RPC_PASSWORD
MONERO_WALLET_RPC_USER
MONERO_WALLET_RPC_PASSWORD
```

## CLI

```bash
gpt-doug-xmr-neural status
gpt-doug-xmr-neural verify-ledger
gpt-doug-xmr-neural daemon-info
gpt-doug-xmr-neural wallet-balance
```

## Python

```python
import hashlib

from monero_neural import MoneroNeuralChain
from universal_hive import UniversalHiveRuntime

hive = UniversalHiveRuntime()
chain = MoneroNeuralChain("~/.gpt-doug/monero-neural", hive=hive)

model_hash = hashlib.sha256(b"model-v1").hexdigest()
ontology_hash = hive.ontology_hash

job = chain.create_job(
    {"task": "research"},
    model_hash=model_hash,
    ontology_hash=ontology_hash,
    purpose="produce a verified neural result",
    request_id="example-1",
)

chain.record_result(
    job["job_id"],
    worker_id="doug-worker-1",
    output_payload={"candidate": "A"},
    confidence=0.8,
)
chain.record_result(
    job["job_id"],
    worker_id="gpt-chaos-1",
    output_payload={"challenge": "test assumption A"},
    confidence=0.7,
    role="critic",
)
chain.record_result(
    job["job_id"],
    worker_id="verifier-1",
    output_payload={"verified": True},
    confidence=1.0,
    role="verifier",
)

receipt = chain.reconcile(job["job_id"], final_output={"result": "A"})
```

The resulting receipt contains hashes of the model, ontology, input and output,
plus worker/critic/verifier provenance. It can then be linked to a human-approved
Monero settlement handled by a separate signer.


## End-to-end macOS/Linux bootstrap

Use the repository bootstrap instead of installing into Homebrew's system Python.
It creates an isolated virtual environment, installs the package there, writes a
stable launcher to `~/.local/bin/gpt-doug-xmr-neural`, and keeps Monero RPC
configuration in `~/.config/gptdoug/xmr-neural.env`.

```bash
curl -fsSLo /tmp/install-xmr-neural \
  https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/scripts/install-xmr-neural
bash /tmp/install-xmr-neural
```

The installer deliberately does **not** use `--break-system-packages` and does
not modify `~/.zshrc`. If `~/.local/bin` is not already on your PATH, either
invoke the launcher directly:

```bash
~/.local/bin/gpt-doug-xmr-neural doctor
```

or add it to PATH after repairing any existing shell-config parse errors:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

The bootstrap synchronizes its installation checkout from the public HTTPS Git
URL, so a missing GitHub SSH key does not block read/install access.

### Doctor states

```text
READY_LOCAL
  package + isolated Python + ledger are healthy; RPC checks skipped

READY_LOCAL_RPC_OFFLINE
  GPT-Doug is installed correctly; Monero daemon and/or wallet RPC is offline

READY_END_TO_END
  package + ledger + daemon RPC + wallet RPC are all reachable

LOCAL_INSTALL_INCOMPLETE
  the Python environment or local ledger failed validation
```

Run:

```bash
gpt-doug-xmr-neural doctor
gpt-doug-xmr-neural doctor --strict-rpc
```

`--strict-rpc` is useful for automation because it exits non-zero until both
configured RPC endpoints are reachable.


## Start the local Monero stagenet runtime

Official Monero stagenet uses daemon JSON-RPC on port `38081` and wallet RPC on
port `38088`. Port `38082` is the stagenet ZMQ RPC port and should not be
used for `monero-wallet-rpc`.

On macOS with Homebrew:

```bash
brew install monero
bash scripts/start-xmr-stagenet
```

Or allow the helper to install the Homebrew formula when it is missing:

```bash
bash scripts/start-xmr-stagenet --install
```

The helper:

- starts a pruned local `monerod --stagenet` bound to `127.0.0.1:38081`
- starts `monero-wallet-rpc --stagenet` bound to `127.0.0.1:38088`
- protects wallet RPC with generated local RPC credentials
- creates only a wallet directory; it does not create or open a wallet
- does not load or persist a private spend key
- keeps the neural settlement layer external-signer-only

After startup:

```bash
~/.local/bin/gpt-doug-xmr-neural doctor
```

A healthy runtime reports `READY_END_TO_END`. The daemon may still be syncing
the stagenet blockchain; `daemon-info` exposes the current height while it
catches up.


## RPC authentication

When `monero-wallet-rpc` is started with `--rpc-login user:password`, GPT-Doug
uses Monero-compatible HTTP Digest authentication. A 401 from an otherwise
reachable wallet RPC usually means the client and server disagree on the RPC
authentication method or credentials.

The local stagenet helper uses the same generated credentials for the wallet RPC
process, the environment file, the readiness probe, and the Python doctor.


## Repairing a stale wallet-RPC credential process

If the daemon is reachable but the doctor reports wallet RPC HTTP 401, the
wallet-RPC process may have been started with credentials that no longer match
`~/.config/gptdoug/xmr-neural.env`.

Re-run the stagenet helper:

```bash
bash scripts/start-xmr-stagenet
```

The helper now distinguishes `ready`, `unauthorized`, and `offline`. For an
unauthorized wallet RPC that it previously started, it validates the recorded
PID and command line, sends SIGTERM only to that managed
`monero-wallet-rpc --rpc-bind-port 38088` process, and restarts it with the
current saved credentials. If the process is not managed by the helper, it
fails closed instead of killing an unknown process.
