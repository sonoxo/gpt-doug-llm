# STOP THE KRAKEN / Fleet Safety Evidence Layer

This module collects **offline, time-bounded, signed acknowledgments** from explicitly
registered GPT-Doug/ZYRA hosts. It **does not** activate a stop on other machines,
operate a cloud account, kill external AI, inspect a network, or rearm models.

A receipt means only that cooperating Python code on a registered host reported
seeing its **local operator latch** (`operator_stop_latched`) or host-enforced stop
(`host_enforced_stop`) at the receipt time. A signature does **not** attest host
integrity or prove that all AI on that machine actually stopped. Third-party AI is
outside this protocol. In production use host firewalls, operator-owned credentials,
process supervisors, and independent hardware interlocks for physical devices.

## Prepare an explicit inventory (operator)

Create `fleet.json` with only systems you own and manage:

```json
{
  "schema_version": 1,
  "fleet_id": "example-owned-fleet",
  "nodes": [
    {"id": "doug-core-01", "label": "GPT-Doug core host"},
    {"id": "zyra-agent-01", "label": "ZYRA agent host"}
  ]
}
```

No hosts, IP addresses, APIs, credentials, or services are discovered automatically.
Every registered node must have a unique **32-byte private HMAC key** created by
an operator and securely provisioned to that node. The verifier retains a secured
copy for *each* node. Never commit keys, reports containing sensitive metadata, or
any operator credential to GitHub. Keep key files mode `0600`, with restricted
host identity and protected storage. A compromised node/key can forge a receipt;
this is **not** remote attestation. Rotate a compromised key immediately.

## Local workflow (does not stop any AI unless you run the E-stop)

From the project root (or after `pip install -e .`):

```bash
mkdir -p operator-keys operator-receipts
chmod 700 operator-keys operator-receipts
python3 -m kraken_fleet keygen --output operator-keys/doug-core-01.key
python3 -m kraken_fleet keygen --output operator-keys/zyra-agent-01.key
python3 -m kraken_fleet campaign --inventory fleet.json --output campaign.json
```

The `campaign` command creates only a random incident identifier. It **does not**
request or activate any shutdown. For an actual emergency, an authorized operator
must first activate `gpt-doug-llm stop the kraken` on **each managed host**, or
activate the independently managed host stop and confirm `gpt-doug-llm status`.
Remote activation, central propagation, and provider revocation are **not** part of
this feature. Use approved operator tools to distribute the inventory/campaign and
retrieve each node's receipt over trusted channels.

On each host, with its unique private key and a copy of the inventory/campaign:

```bash
python3 -m kraken_fleet ack --inventory fleet.json \
  --campaign campaign.json --node doug-core-01 \
  --key operator-keys/doug-core-01.key \
  --output operator-receipts/doug-core-01.json
```

`ack` refuses to sign unless the **local** `ai_killswitch.status()` reports a
confirmed operator/host stop. An unreadable/invalid stop configuration may block
local AI, but **does not** qualify as positive stop confirmation. Repeat an ack to
refresh it if STOP remains engaged. Supply only signed receipts from nodes you
control, stored in a distinct operator review directory.

On the operator's verification host, after collecting the signed receipts:

```bash
python3 -m kraken_fleet verify --inventory fleet.json \
  --campaign campaign.json --receipts operator-receipts \
  --keys operator-keys --max-age 300 > fleet-report.json
```

Return codes: `0` = every registered node returned a valid, matching, recent
receipt and there are no unregistered receipt files; `3` = incomplete or stale
coverage; `2` = invalid operator configuration. No exit code claims external or
physical shutdown. Timestamp skew over 60 seconds is rejected. A receipt from a
previous campaign is rejected. Reports expire after 300 seconds by default, with
an allowed maximum of 3600 seconds. Missing or unreadable receipts **must never be
reported as confirmed**.

For a visual snapshot, open `agency_cloud/static/kraken-fleet.html` in a browser
and import `fleet-report.json`. The dashboard is offline-only, accepts user-selected
files, and cannot independently verify receipt HMAC signatures. Verify in the CLI
first; the browser renders the supplied report as a snapshot, not live telemetry.

## Governance and limitations

- A campaign only identifies an incident; it is **not** a signed remote stop order.
- The local E-stop lives in `ai_killswitch.py`; this layer audits declarations
  observed at cooperative hosts. It is never allowed to clear a STOP latch.
- Do not treat missing, stale, or unknown nodes as stopped. Registration is manual:
  omissions from inventory are out of scope and cannot be inferred to be covered.
- HMAC confirms possession of a shared secret, **not** independently verified
  host identity, runtime policy integrity, liveness or physical safety.
- Client and verifier clocks must be reasonably synchronized; reports are transient.
- No transport or cross-machine authentication is built into the file-based CLI;
  arrange trusted receipt transport and protect the verifier's key material.
- Unlike network enforcement, a cooperative Python check cannot control unrelated
  processes or independent third-party AI providers.
- Use independent human emergency controls for robots, vehicles, industrial
  machinery and life-safety systems.

## Verification

```bash
python3 -m unittest tests.test_kraken_fleet -v
python3 -m kraken_fleet --help
```

The tests simulate all STOPs inside temporary directories, never a real host.
