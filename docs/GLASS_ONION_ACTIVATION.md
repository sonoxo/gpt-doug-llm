# GLASS ONION / CL1 — Local Activation

This activation is for the *cooperating GPT-DOUG, Kraken Shield and ZYRA Jukebox code paths*. It does **not** grant access to, monitor, control, or secure any third-party music or bank account. The Glass Onion **private vault remains sealed**, requiring its existing passphrase, authenticator, device factor and encrypted private artifacts separately.

## Single-command activation after local checkout

From the dedicated checkout (do **not** overwrite the original `~/gpt-doug-cl1` folder):

```bash
bash scripts/cl1-free-swarm.sh setup
bash scripts/glass-onion-activate.sh activate
```

The launcher:
- Forces Ollama and all inference to localhost and disables paid-service mode.
- Runs the existing CL1 model doctor and Kraken Shield audit/emergency-stop check.
- Tests an approved public music link and confirms a bank transfer action is **BLOCKED**, without contacting music/banking services.
- Confirms the Jukebox music checks are loaded and invoked by its cooperating playback files.
- Fails before launching if ports 8787 or 8844 are already occupied; **does not kill existing servers or reset Git changes**.
- Starts the static Jukebox at `http://127.0.0.1:8844/` and CL1/XUNIA at `http://127.0.0.1:8787/`, both bound to 127.0.0.1.
- Keeps running in the foreground. Ctrl+C stops the Jukebox child it started and allows the CL1 server to stop; it does not touch other processes.

For a diagnostic check without launching either service:

```bash
bash scripts/glass-onion-activate.sh doctor
bash scripts/glass-onion-activate.sh status
```

`status` reports policy and whether the ports accept TCP connections; TCP response is not proof of application identity.

## Guarded scope and guarantees

- Music: policy checks for public links, known service domains, radio streams, saved playback and user-selected local files are wired into the Jukebox. The browser-side checks cannot police redirects or every browser/network process.
- Banking: NO bank adapter exists here, so read/write account actions are blocked by the service policy. This is not protection of bank provider accounts or devices.
- Audit: append-only local hash-linked decision log; corruption prevents activation. The log is not anchored outside the Mac, so truncation or deletion cannot be ruled out cryptographically.
- Privacy: no bank credentials or raw music URLs are written by the new service decision log.
- Private vault: remains **SEALED**. `revealio` and Keychain factors are deliberately not used by the activator.
- Zero-billing: no commercial inference API, hosted compute service, Stripe payments, or subscriptions are started by this launcher. Local hardware, power and internet may still cost money.

## Mac deployment without branch conflicts

```bash
cd "$HOME"
git clone --depth 1 --single-branch \
  --branch feat/glass-onion-local-activation-20261114 \
  https://github.com/sonoxo/gpt-doug-llm.git \
  "$HOME/gpt-doug-glass-onion"
cd "$HOME/gpt-doug-glass-onion"
bash scripts/cl1-free-swarm.sh setup
bash scripts/glass-onion-activate.sh activate
```

Before activating, make sure Ollama is running with the locally installed `qwen2.5-coder:3b` model. If either port is in use, investigate first rather than terminating the process blindly.

## GitHub validation

The `Glass Onion Local Activation Gate` verifies shell syntax, Python banking default-deny policy, local audit behavior, Jukebox link protection, and absence of private-vault unlock calls. A passing CI job does **not** mean the process has started on the operator's Mac. Operator verification is required.
