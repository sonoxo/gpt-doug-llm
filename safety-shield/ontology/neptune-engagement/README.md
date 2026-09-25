# GPT-DOUG Xunia Neptune SHIELD engagement ontology

Version 1.0.0 | Snapshot date: September 16, 2026

This portable ontology connects the user's organizations, development projects, ecosystem relationships, events, procurement opportunities and evidence. It is a repository-backed design package, not a deployed Foundry ontology. No portal changes, event registrations, messages or submissions have been made.

## What is recorded

- Douglas Brown's displayed Xunia CEO profile is supported by the supplied portal export.
- Neptune SHIELD membership is recorded as `joined_user_reported`, based on the user's explicit statement. The organization subject is provisionally Xunia because that is the displayed profile; confirm whether membership is personal or organizational. No legal relationship between Xunia and 24k-Media Productions is inferred.
- CFIC portal access is recorded as a document-supported assertion. The export does not explicitly establish membership status.
- Four events are preserved as listed, with dates but no inferred times, locations, registration or attendance. Neptune's event label establishes where the event is listed, not an assertion of legal sponsorship.
- Zyra, Xunia, GPT-DOUG, THEGREENHOUSE, the proposed ICAM service and an optional Foundry adapter are connected through proposed integration relationships. Capabilities are marked proposed, not tested.
- The ICAM opportunity is a solicitation and its response remains a draft. No contract award or formal partnership records are seeded.

## Files

| File | Purpose |
|---|---|
| ontology.json | Object definitions, typed relationships, enums and invariants |
| objects.json / links.json | Seed graph with stable identifiers and evidence references |
| objects.csv / links.csv | Portable staging tables; nested fields remain JSON strings |
| actions.json | Proposed reviewed actions and audit requirements; not executable enforcement |
| foundry_mapping.json | Suggested backing datasets and primary-key mappings; not an API request |
| source_portal_export.md | Exact user-supplied export supporting profile and event records |
| validate.py | Standard-library structural validator and negative test fixtures |
| validation_report.json | Results from validating the delivered package |

## Main relationships

Organization -> Project -> Capability describes the development portfolio. Project -> Project records proposed integrations. Membership -> Organization and Membership -> Ecosystem capture participation without implying a contract. Event -> Ecosystem identifies the listing context. Submission -> Opportunity and Submission -> Organization distinguish a draft response from an awarded Agreement. Every seeded non-evidence object and every link cites an Evidence record.

Agreement exists as a separate object type so signed teaming documents, partnership agreements and actual awards can be represented later. Do not turn a Membership or solicitation identifier into an award number. A relationship involving a government-linked ecosystem does not grant government affiliation, access, endorsement or clearance.

## Upcoming event snapshot

| Event | Listed date | Ecosystem |
|---|---|---|
| Transatlantic Partnerships Business Roundtable | September 29, 2026 | Neptune SHIELD |
| FATHOMWERX SUMMIT 2026 | October 14, 2026 | Ratio Marketplace |
| CMMC Roundtable and Panel Discussion | October 20, 2026 | Cyber Bytes Foundation |
| Office of Small Business Programs Networking Event 2026 | November 5, 2026 | SOFWERX |

Dates come from the uploaded snapshot; they were not independently checked against live event pages. Event URLs are copied from title links. The export sometimes has different image and title links, so title links were used. This package creates no reminders or scheduled jobs.

## Run validation

Extract the ZIP, open a terminal in its folder, and run:

```bash
python3 validate.py
```

No dependencies or network access are required. The validator checks identifier uniqueness, required properties, enums, relationship endpoint types, evidence references, unsupported status promotions and the source export hash. Negative tests verify rejection of missing evidence and broken links. Structural validation cannot prove the truth of evidence. The JSON definitions are an application ontology, not an OWL reasoner or a complete JSON Schema implementation.

## Foundry implementation handoff

1. Select the authorized project and ontology in the target Foundry environment. No resource IDs or credentials are included.
2. Stage the seed files. Create a backing dataset per object type and flatten `properties` into appropriately typed columns. Preserve `source_ids` as evidence references. Cast date-only event dates as dates, not invented midnight timestamps.
3. Create object types with `id` as primary key and configure links using the endpoint pairs in `ontology.json`. Keep the membership object so role, dates, subject and verification status remain explicit.
4. Implement the specified actions with platform-enforced roles, evidence review, append-only audit records and before/after values. The validator does not provide access control and must not be treated as a security boundary.
5. Limit raw exports and contact information to authorized users. Separate personal profile evidence from public capability summaries. Do not ingest classified content into this package.
6. Run validation, review counts and duplicate keys, then verify each staged relationship in the target environment before activating actions.

This handoff deliberately does not invent Foundry SDK calls, dataset RIDs or deployment success. Live implementation requires the actual authorized environment and supported APIs.

## Suggested next records

Capture the Neptune confirmation and confirm the member entity; verify roundtable details and any registration requirement; attach current demonstration artifacts to capability records; record actual submission receipts when available. The seed graph contains open planning tasks for the first two activities and introduction preparation, assigned provisionally to Douglas. No due dates or external commitments are fabricated.

## Existing repository integration

This module sits beside [the public vendor graph](../neptune-shield-vendor-ecosystem.json) and complements [the Neptune ecosystem reader](../../../agents/neptune_shield_ecosystem.py). It does not replace that graph or alter its execution policy. Cross-repository context: [ZYRA](https://github.com/sonoxo/zyra).

Run from the repository root:

```bash
python3 safety-shield/ontology/neptune-engagement/validate.py
```

### Identity conflict requiring review

The earlier vendor graph attributes UEI STXJUM7D6FK1 to Neptune Shield; supplied portal text attributes it to 24k-Media Productions. This module records it only as a reported value with a conflict flag. No entity merge, ownership inference or verified credential is created. Confirm the appropriate entity using authoritative registration evidence before using this identifier in a submission.
