# ZYRA Federation | SHAGGOTH-KRAKEN | Terminal Cortex

## Scope
This module is a local observation and memory boundary for public open-science metrics, authorized social/business metadata, licensed or public trade/market aggregates, local system health, and *synthetic-only* defensive SI exercises. Company names label future connector templates. There are **zero** connections to Meta, Tesla, X, Snapchat, LinkedIn, exchanges, medical devices or military systems in this release.

```
 User-supplied approved values        Explicit synthetic exercise values
               |                                  |
               +----------------+-----------------+
                                |
                   [ Validation policy gate ]
                    (public / synthetic only)
                                |
                    [ PINEAL external memory ]
                       local SQLite + audit
                                |
                 [ Authenticated loopback API ]
                                |
                 [ ZYRA Terminal Cortex (read) ]
                                |
                  [ Human operator + review ]

  KRAKEN simulated thermal/power controller - advisory only
  Third-party accounts / weapons / brain interfaces - unconnected
```

## Provider templates

| Node | Allowed locally entered information | Current connection |
| --- | --- | --- |
| ZYRA | Operator-controlled local governance aggregates | Local-only |
| Meta, X, Snapchat | Aggregate counts from licensed/public sources | Not connected |
| Tesla | Aggregated public mobility/energy/computing metrics | Not connected |
| LinkedIn | Public or operator-licensed professional aggregates | Not connected |
| Global Trade | Public or licensed macro trade statistics | Not connected |
| Global Markets | Public or licensed delayed aggregate financial market data | Not connected |
| Biotech | Publication counts, nonpersonal study metadata, clearly simulated EEG metrics | Not connected |
| Warfighter Defensive SI | Synthetic aggregate readiness / sensor health / patch compliance | Not connected |

All entries carry `node`, `metric`, `value`, `unit`, `source`, `kind` (`local-manual` or `synthetic`), `classification`, `stamp`, and sequence ID. A hash-chained audit entry accompanies each insert.

## Mac terminal usage

Install the package after pulling the GitHub integration branch, or install directly from its `subdirectory` URL.

```
pineal federation
pineal dashboard --demo --watch --interval 1
pineal dashboard --no-color
pineal observe global-trade shipping_index 108.3 --unit index --source operator-owned-export
pineal observe biotech publications 145 --unit count --source open-literature-manual
pineal observe warfighter-defense-si patch_compliance_pct 93 --unit % --source simulation-lab --synthetic
```

- `dashboard` without `--demo` displays only stored local records and no invented signals.
- `--demo` shows deterministic animation that is **synthetic**, NOT a feed from providers, markets, research centers, command networks or sensors. It never stores simulated demo readings; the CLI may initialize the empty local database.
- `--watch` redraws on a TTY until Ctrl+C, or prints frames without clearing in a non-TTY pipeline. Use `--frames 3` to bound a watch run.
- Only the existing token-authenticated loopback API exposes `/v1/federation`; the added route is read-only, with no HTTP importer in this phase.
- Every remote adapter requires documented API permission, a named accountable operator, scoped credentials in a secret store, user/data rights, network egress allowlists, rate limits, attribution, and a separate security review. Merely enabling a node name does not establish a connection.

## Security constraints and limitations

This project is NOT an accredited federal SI platform, a defense C2 network, a medical or human brain interface, a live trading engine, or a working integration with the listed companies. It makes no claims of access, affiliation, certifications, authorizations, defensive coverage or real-time data. Inputs are aggregate numeric values only. Classifications other than PUBLIC or SYNTHETIC are rejected. Do not input personal health information, export-controlled material, classified data, CUI, sensitive geolocation, actual defense readiness data, proprietary API tokens or secrets. Warfighter Defense SI uses allowlisted synthetic exercise metrics only; no weapon-targeting, mission execution, or real system actuation.

Future work: separately reviewed official API adapters with user authorization; signed ingest manifests; granular roles and scoped consent; retention/export controls; source freshness; stronger audit anchoring; dedicated multi-user service; threat modeling; and terminal accessibility checks. Until then, ZYRA's policy is an application-level gate, not a substitute for external security accreditation.
