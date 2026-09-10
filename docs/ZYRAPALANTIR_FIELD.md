# ZYRAPALANTIR Field Operations Console

`zyra-field` is a human-controlled, decision-support terminal for authorized field awareness. It summarizes ZYRAPALANTIR LIVE state and optional explicitly authorized local JSON inputs.

## One-command boot

```sh
zyra-field-mega
```

The mega boot ensures the governed defensive profile is active, starts ZYRAPALANTIR LIVE if needed, validates the field ontology, and renders the full field dashboard.

## Commands

```sh
zyra-field status
zyra-field assets
zyra-field comms
zyra-field intel
zyra-field cyber
zyra-field incidents
zyra-field readiness
zyra-field all
zyra-field simulate
```

## Authorized data import

By default the console uses local ZYRAPALANTIR state only. To summarize an additional local JSON file, the operator must explicitly acknowledge authorization:

```sh
export ZYRAPALANTIR_AUTHORIZED_SCOPE_ACK=YES
zyra-field intel --data /path/to/authorized-field-data.json
```

The optional JSON may contain arrays named `assets`, `comms`, `reports`, and `incidents`.

## Safety boundary

The field console is for situational awareness, cyber defense, communications health, readiness, asset status, intelligence correlation, incident tracking, and training simulation. It does not select targets, release fires, control weapons, steer vehicles, disrupt critical infrastructure, or perform automatic external remediation. Consequential external actions remain behind human authorization.

This is an engineering capability and does not imply military certification, accreditation, or an Authorization to Operate (ATO).
