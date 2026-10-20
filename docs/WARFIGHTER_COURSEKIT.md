# GPT-Doug Warfighter CourseKit — synthetic offline training (v1)

**Authority:** `RESEARCH_ONLY`. The CourseKit is an educational assessment component layered on the existing `WARFIGHTER_RESEARCH_V1` repository. It is not a DoD system, accredited readiness system, threat-intelligence system, operational command-and-control system, or certification. No military approval, field effectiveness, cryptographic source authentication, or external source rights are implied.

## What runs

- Strict JSON course-pack and response validation (explicit `SYNTHETIC` classification only).
- Deterministic scoring with a per-domain breakdown, content SHA-256 checksum, and an explicit `operational_ready: false` result.
- Bounded local file intake with no network, no symlinks, no directory traversal, no duplicate JSON object keys, no nonfinite literals, and a 64 KiB cap.
- A fully standalone mobile-friendly HTML training console at `research_lab/warfighter/web/coursekit.html`. It ships with the same synthetic 10-question course pack and allows a user-selected **local JSON course pack**. No CDN, tokens, cookies, analytics, geolocation, network requests, or remote service calls are used by the app.
- Two **source placeholders** for a future authorized review of course material. Neither Google Drive folder is fetched, and no private folder URL or source contents are committed to the public repository.

The geometric dashboard is an intentionally **non-geographical illustrative schematic**, not a military operations picture. It has no troop positions, target data, sensor feeds, weapon commands, live communications, or autonomous actions.

## Use

From the repository root:

```sh
# Existing Warfighter CLI (added course subcommand)
python3 -m research_lab.warfighter.cli course sources
python3 -m research_lab.warfighter.cli course validate \
  --pack research_lab/warfighter/examples/synthetic_coursekit_v1.json \
  --input-root research_lab/warfighter/examples
python3 -m research_lab.warfighter.cli course grade \
  --pack research_lab/warfighter/examples/synthetic_coursekit_v1.json \
  --responses research_lab/warfighter/examples/synthetic_responses_demo.json \
  --input-root research_lab/warfighter/examples

# Can also run CourseKit standalone
python3 -m research_lab.warfighter.coursekit sources
python3 -m research_lab.warfighter.coursekit validate \
  --pack research_lab/warfighter/examples/synthetic_coursekit_v1.json \
  --input-root research_lab/warfighter/examples

# Test gates
python3 -m unittest research_lab.warfighter.tests.test_coursekit -v
python3 -m unittest discover -s research_lab/warfighter/tests -p 'test_*.py' -v
```

Open `research_lab/warfighter/web/coursekit.html` in a browser to take the local exercise. A local file can be imported with **Import Local Course Pack**. HTML import performs client-side structural checks; the Python validator is authoritative for local file-integrity checks and rejects duplicate JSON keys and unsafe paths. Browser result export is deliberately unsigned and unauthenticated; it cannot attest to an operator identity or verified learning outcome.

## Example output

`course validate` returns `VALID_SYNTHETIC_COURSE`, pack SHA-256, question count, and `RESEARCH_ONLY`. `course grade` returns `SYNTHETIC_ASSESSMENT` with question feedback, `score_pct`, per-domain scores, and explicit negative operational-readiness fields. Demonstration answer choices yield **9/10 correct (90%)**; this is a toy example, not evidence of actual human performance.

## Intake of private course materials

1. Keep the linked Drive folders private until access, ownership, licensing, security labels, and sharing permissions are checked by an authorized person.
2. Do not paste, clone or commit CUI, classified, export-controlled, personal, or otherwise restricted material into this public project. Do not treat a course folder title as proof of its contents.
3. After explicit permission, create **new, original synthetic questions** based only on cleared concepts. Use the local JSON schema and `course validate` before delivery; retain source mapping separately in a secured, access-controlled system. Do not mark source provenance "verified" unless independently verified.
4. Any future authenticated Drive or TAK integration requires a separate security review and consent. This build has no such interface.

## Verification and limitations

The local CourseKit unittest suite exercises deterministic scoring, forbidden classification labels, malformed questions, unknown answers, JSON duplicate keys, symlink/path/size bounds, and a socket-network guard. The browser smoke exercise verifies desktop and mobile presentation, a perfect-score walkthrough, local import, reset, and rejection of a non-synthetic pack.

Repository-wide CI, merge, real course import, independent security review, professional training validation, and website deployment must each be reported separately. Passing tests verifies only the specified synthetic behavior, not physical, operational, or governmental readiness.

**Governance:** Do not modify the existing `ZYRA_MSS_V1` ontology, XQE dispatcher, PINEAL federation, review gates, or publication state machine as part of this feature.
