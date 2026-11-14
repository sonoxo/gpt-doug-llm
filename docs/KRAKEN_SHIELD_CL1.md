# KRAKEN SHIELD / CL1 — Integrated defensive architecture

**Status:** implementation PR, not a deployed universal firewall. Built atop the existing `GoldenShield`, `Zyra`, `ai_killswitch` and CL1 local inference policy. All runtime components are open source or local standard-library code.

## Runtime contract

```text
                       OPERATOR (Mac)
                             |
                       127.0.0.1:8787
                             |
                    KRAKEN SHIELD CL1
                    /       |        \
                STOP     CL1 POLICY   AUDIT
                 |           |          |
            AI halt       localhost   private JSONL
                             |
                    GOLDEN SHIELD -> ZYRA
                             |
                      approved text
                             |
                       LOCAL OLLAMA
                             |
                      existing streaming UI
```

- **Emergency stop**: denies inbound chat before invoking an AI model when the existing operator stop is latched.
- **Zero-billing**: only `none`/local `ollama` provider settings, a loopback Ollama endpoint, and non-`:cloud` model names pass the CL1 policy. The default Kraken Shield policy rejects other provider names instead of auto-routing.
- **Request inspection**: delegates to existing Golden Shield / Zyra. Denied and quarantined assessments are both blocked. No shell commands, git writes, provisioning, weapon control, or payment handling occur in this module.
- **Kraken Jutsu ontology**: a read-only local vulnerability/SSVC/CVE judgment method consumes **supplied JSON evidence only**; it never fetches data, patches software, or treats a provider label as independently verified. The resulting judgment is audit-linked.
- **Capability gate**: only `inspect`, `status`, `local_report`, and `ontology_read` are allowed; every other capability is denied pending an independently implemented, human-authorized action workflow.
- **Audit**: a private, hash-linked JSONL file under `~/.gpt-doug/kraken-shield/decisions.jsonl`. Only a SHA-256 request fingerprint, policy outcome, time and chain link are recorded by this module, **not raw prompt text**. Corruption, unsafe permissions, symlinks and failed appends refuse further requests. This is *not* cryptographic proof against deletion or an operator with write access.
- **Web integration**: the CL1 launcher enables `KRAKEN_SHIELD_ENFORCE=1`. Both the standard web chat and XUNIA streaming chat invoke Kraken inbound preflight when enabled. Other ports, service integrations and direct Python calls are **outside** this web gate.
- **Output limitation**: existing server streaming delivers tokens before the final Zyra audit. Kraken Shield does not yet provide pre-delivery outbound DLP for streamed tokens; do not describe it as full outbound enforcement.

## Mac CLI

From the checked-out Kraken Shield feature branch:

```bash
bash scripts/cl1-free-swarm.sh setup
bash scripts/cl1-free-swarm.sh doctor
python3 -m kraken_shield status
python3 -m kraken_shield verify
printf '%s' '{"cve":"CVE-2099-0001","oscal_controls":["RA-5"]}' | python3 -m kraken_shield judge
printf 'Build a local dashboard' | python3 -m kraken_shield inspect
python3 -m kraken_shield capability --capability deploy
bash scripts/cl1-free-swarm.sh run
```

If the repo has an active `.venv` but system Python lacks dependencies, use `.venv/bin/python -m kraken_shield ...`. A denied request exits 3; an unavailable audit or configuration exits 2.

The web server intentionally binds to `127.0.0.1:8787`. The CLI and its audit have no outbound API, billing, registration or secret requirements. Only `doctor` in the existing CL1 launcher makes a read-only request to the *local* Ollama API.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_kraken_shield.py' -v
bash -n scripts/cl1-free-swarm.sh
```

Check the automated `Kraken Shield CL1 Gate` job before merging. A passing gate proves the tests passed, not that the firewall protects unrelated software.

## Rollout boundary

The parent CL1 free-only work is still in PR #519. Kraken Shield uses a stacked PR against that branch. Merge #519 first, then the shield PR after CI review. For a local preview, check out the Kraken Shield feature branch in the dedicated `~/gpt-doug-cl1` checkout and run the launcher. Do not perform destructive resets or overwrite uncommitted local changes.
