# GPT-Doug PeaceLab — open, evidence-first peace technology

**Status (2026-10-13):** engineering prototype, not an established humanitarian program. There are **zero independently verified peace outcomes, no identified qualified nominator, and no award or nomination**. The included report and activities are explicitly synthetic. An independent ethics review, active legal candidate and real-world outcomes are necessary before any nomination consideration.

## A concrete peace mission

Provide an accessible, no-cost human-facilitated conflict dialogue template and a transparent evaluation mechanism that distinguishes **work completed**, **self-reported metrics**, **links to primary evidence**, **independent evaluation documentation**, and **actual independently verified benefit**. The last item cannot be established by this software.

Potential programs: (1) voluntary dialogue workshops facilitated by qualified local practitioners, (2) neutral peace education, (3) privacy-respecting humanitarian coordination, (4) open-source safety tooling. These are **proposals** and should be designed with affected communities, not imposed on them.

No self-replicating swarms, autonomous conflict interventions, participant profiling, location tracking, message targeting, medical advice, biometric identification, military targeting, or unauthorized access. No donations or expenditure are initiated.

## Run offline; no API keys or packages

Python 3.9+ standard library. At the GPT-Doug repository root:

```sh
bash scripts/doug-max peace-lab demo > /tmp/gpt-doug-peace-demo.json
bash scripts/doug-max peace-lab verify /tmp/gpt-doug-peace-demo.json
bash scripts/doug-max peace-lab kit
bash scripts/doug-max peace-lab brief /tmp/gpt-doug-peace-demo.json
bash scripts/doug-max peace-lab init /tmp/gpt-doug-peace-snapshot.json
bash scripts/doug-max peace-lab assess /tmp/gpt-doug-peace-snapshot.json
python3 -m unittest discover -s tests -p 'test_peace_impact.py' -v
```

From a standalone bundle outside the repository, run `bash run-GPT-Doug-PeaceLab.command demo`. `init` never overwrites files. `verify` checks exact local replay, *not* external truth. For any real activity, replace the synthetic example only with documented, consented, anonymized/aggregated program data. No real outcomes are recorded here.

## Evidence categories and interpretation

| Field | Meaning | Caveat |
| --- | --- | --- |
| `completed_real_activities_self_reported` | Count of entered, marked-completed non-synthetic records | Not a verified impact; no independent observation |
| `evidence_linked` | Record includes a public HTTPS primary-source URL | URL content not crawled, validated, or trusted |
| `external_review_linked` | Record includes a public HTTPS purported external review | Reviewer identity, methods and independence **not verified** |
| `complete_evaluation_fields` | Baseline, followup, method and harm records are filled | Metadata completeness is not evidence that outcome was caused by project |
| `independently_verified_impact_by_software` | Always **0** | This tool cannot establish impact |
| `nobel.eligibility_status` | Missing-document review checklist | Even `DOCUMENTS_READY_FOR_HUMAN_REVIEW` is not eligibility, nomination or endorsement |

Records use deterministic SHA-256 digests to detect accidental/malicious changes to **the report**. A digest proves consistency only, **not scientific validity**. All program entries and linked documentation remain claims until they are independently confirmed.

## Safety design

- Do not collect names, addresses, contact details, raw personal narratives, exact geolocations, conflict-party identifying information, or beneficiary records. Whitelisted schema rejects unknown fields and common email/phone patterns but is **not a comprehensive de-identification guarantee**.
- Suppress cohorts of fewer than ten in this ledger (record participant count as `null`). Even large aggregates can be re-identifying; assess disclosure risks before publishing.
- Require documented consent, human oversight, and privacy safeguards for completed real activities. Record adverse incidents and unintended consequences in aggregate, never hide harm or infer safety from silence.
- Seek an independent evaluator to pre-register a hypothesis, define counterfactual or baseline, collect followup, and evaluate possible harms and confounding. This engine does not infer causal effects from pre/post numbers.
- Human-led, voluntary facilitation only; stop if retaliation, coercion, violence, or privacy exposure is possible. Risk controls should be reviewed by people with relevant local expertise.
- Do not interpret a Nobel nomination as institutional endorsement. Do not claim association with UNESCO, ICRC, UNDP or Nobel institutions.

### Authoritative references

- [Nobel Peace Prize nomination rules](https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/): nominations of people/active organizations via qualified third parties; personal applications rejected; 31 January regular deadline.
- [Eligible nominators](https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/criteria-for-nominators): e.g. qualifying university professors, legislators, prior Peace laureates.
- [UNESCO Recommendation on AI Ethics](https://www.unesco.org/en/artificial-intelligence/recommendation-ethics): human rights, peaceful societies, do no harm, oversight.
- [ICRC Handbook on Data Protection in Humanitarian Action](https://www.icrc.org/en/data-protection-humanitarian-action-handbook): protecting the dignity and personal data of affected people.
- [UNDP conflict sensitivity indicator guidance](https://www.undp.org/myanmar/publications/conflict-sensitivity-indicators-local-and-community-development-programming): monitoring both positive and harmful interactions.

These sources **inform** design but imply no endorsement or accreditation.

## Evidence-oriented operating plan (2026–2027)

1. **Design and community consultation:** identify a legitimate, legally recognized implementing organization; invite diverse affected communities and qualified peace workers to design a small, voluntary pilot. Verify inclusive access and safeguarding plans.
2. **Pilot and monitor:** train human facilitators, document consent, register suitable non-identifying aggregate indicators and adversities, and record published non-sensitive primary evidence. Do not declare success from running a workshop.
3. **Independent evaluation:** obtain independent assessment of methods, outcomes, adverse effects, and attribution with public documentation where safe; review the potential for harms in release of any data.
4. **Nomination preparation (only if warranted):** if substantial real-world peace impact is independently substantiated and an eligible candidate organization exists, assemble a factual dossier that an **eligible independent nominator** could consider. The next regular deadline is **January 31, 2027**, but a new and unvalidated project would not justify haste. An eligible nominator and the Norwegian Nobel Committee make their own decisions. A nomination is never guaranteed.

**Launch target:** safe, measurable peace work—not a prize claim. The award is entirely at the Committee's discretion.
