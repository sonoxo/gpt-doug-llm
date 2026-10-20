# XUNIA Watchtower — Public Museum

`index.html` is a free, responsive **synthetic** oversight console. It operates locally in the visitor's browser and does **not** contain model-provider credentials or control remote AI infrastructure.

The associated `universal_watchdog` Python package is a separate loopback-only operator service. It authenticates each registered model with its own ingest token, gates actions by capability and scope, requires independent review for high-impact self-modifications, and maintains an HMAC audit chain without saving prompt plaintext.

To connect to actual operator data on the same machine, launch `python3 -m universal_watchdog serve` from the repository and open the URL printed by the CLI. **Do not** enter operator credentials into the public xunia.org website. The static museum page never connects to arbitrary model APIs.

Source: https://github.com/sonoxo/gpt-doug-llm/tree/main/universal_watchdog

This is a training/development prototype. Enterprise use requires reviewed operator-only credentials, authenticated TLS deployment, external logs, additional isolation, independent red teaming, and evidence of integration with every intended model or agent.
