# GPT-Doug PeaceLab — 90-day human-led pilot protocol

**Status (October 13, 2026): engineering design for review, not an active humanitarian field program.** No organization, community partner, independent evaluator, facilitator, real workshop, qualified nominator, or peace benefit is confirmed. **Not a Nobel Peace Prize submission.**

## Intended public benefit

Support a low-risk, voluntary, impartial and **human-facilitated** dialogue and peace-education pilot. Its purpose is to help people practice constructive listening and evaluate the safety and possible usefulness of such education. A qualified local community partner must decide whether the idea is appropriate in that setting. This is not AI-mediated peace negotiation, social targeting or behavioral manipulation.

**Excluded:** autonomous conflict intervention, military/political targeting, location or identity tracking, participant profiling, monitoring raw stories, recording personal disclosures, coercion, live conflict operations, and fabricated peace or Nobel outcomes.

## Conditional 90-day execution design

| Window | Human-led responsibility | Required exit evidence |
|---|---|---|
| Days 1–30 | Establish and independently verify an accountable organization; seek community-initiated advice on context, power imbalances, risks and local legitimacy | Independent community and safeguarding review or cancel |
| Days 31–60 | Draft accessible informed consent and safe withdrawal; assess privacy risks; appoint qualified facilitator; pre-register harm, outcome and comparison methods | Eight human-documentary safeguards externally assessed; **no software-issued field approval** |
| Days 61–75 | **Only if explicitly authorized outside the software:** conduct a small voluntary human-facilitated educational pilot, with a human stop procedure | Approved consent, human safety leadership and an independent adverse-event response |
| Days 76–90 | Independently review benefits, null outcomes, incidents, attrition and measurement biases; vet any aggregate public report | Community review and a credible external evaluation before any effectiveness claim |

No step self-executes. If approvals are absent or a credible harm occurs, field activity is blocked.

## Required human decision holders (currently unverified)

| Role | Decision to make |
|---|---|
| Accountable legal organization and director | Decide legitimate program governance and financial/operational authority |
| Community advisory representatives | Determine if a pilot is wanted and safe; may veto |
| Independent safeguarding reviewer | Assess potential coercion, retaliation, discrimination, and conflict escalation |
| Qualified independent facilitator | Run the session safely, not through an AI agent |
| Privacy reviewer | Approve minimization and public suppression rules |
| Independent evaluator | Pre-register an appropriate design, evidence standards and adverse-outcome reporting |

GitHub passing tests and documentary SHA-256 checks do not authenticate humans or authorize a pilot.

## Measurable outputs — draft instrument for independent review

Any questions must be adapted to the actual community, language, accessibility, safeguarding and privacy conditions by the independent evaluator. Suggested **aggregate-only** items:

1. Voluntary participation safety and real ability to stop or withdraw (0–5 scale, only if independently approved).
2. Self-reported comfort with hearing a differing viewpoint without escalation (0–5).
3. Repeat the approved items at immediate and delayed follow-up, publishing denominator/attrition only when disclosure-safe.
4. Incident indicator: unknown / no credible incident observed / an incident observed. Any reported serious safety concern triggers **STOP_AND_HUMAN_REVIEW**.
5. Safeguarding, inclusiveness, non-response and unforeseen-harm review by community representatives.

Do not store raw answers, political attitudes, contacts, locations, identity attributes or stories in the public software. Suppress aggregate cohort sizes below **10**; that rule alone does not make a record anonymous. A before/after score is **descriptive**, not a causal estimate of reduced violence, reconciliation, humanitarian benefit or a Nobel-qualifying achievement.

## Eight code-enforced documentary gates

Every gate begins **PENDING**. It can be marked **DOCUMENTED_UNVERIFIED** only with a dated public HTTPS link; the link is not fetched or authenticated. A gate may be **BLOCKED**, which triggers an explicit halt. Even if all eight are documented, the engine returns **NEVER_GRANTED_BY_SOFTWARE** for field authorization.

| Gate | Independent evidence to obtain |
|---|---|
| legal_partner | Verified legal identity, human director and authority |
| community_voice | Genuine and voluntary community-led advice and veto mechanism |
| conflict_sensitivity | Independent conflict-risk and do-no-harm analysis |
| consent_privacy | Informed consent, withdrawal, storage and publication protocols |
| human_facilitator | Qualified, impartial human facilitation and supervision |
| evaluation_protocol | Pre-registered independent evaluation, harm/attrition measures |
| incident_response | Human complaint, referral, stop and escalation mechanism |
| conflict_of_interest | Transparent funding, material interests and neutrality review |

Risk register: retaliation, power imbalances, inadvertent identity disclosure, escalation, and evaluation overclaim. Any blocked gate or adverse event results in **STOP_AND_HUMAN_REVIEW**.

## Repeatable offline engineering demonstration

Python 3.9+ with no paid APIs or outside network calls. In the repository:

~~~sh
bash scripts/doug-max peace-lab pilot-demo > /tmp/pilot-review.json
bash scripts/doug-max peace-lab pilot-verify /tmp/pilot-review.json
bash scripts/doug-max peace-lab pilot-brief /tmp/pilot-review.json > /tmp/pilot-review.md
bash scripts/doug-max peace-lab pilot-preview /tmp/pilot-review.json > /tmp/pilot-review.html
python3 -m unittest discover -s tests -p 'test_peace*.py' -v
~~~

For a private working copy, create an owner-only directory and run the **pilot-init** subcommand with an unused path there. It exclusively creates a synthetic template; it does not overwrite an existing snapshot. Do not commit field notes or private information.

The review report includes a local replay hash, but **a valid hash is not proof of truth, causal impact or third-party approval**.

## Independent reviewers: acceptance questions

- Is the proposed engagement safe and wanted by the intended community?
- Are consent and withdrawal authentic given all foreseeable power imbalances?
- Is the location/context inappropriate because of retaliation or escalation risk?
- Are the trained human facilitators, accountable organization and safeguarding personnel independent and competent?
- Has an evaluator pre-registered credible methods for both benefits and harm, with transparent limitations and attrition?
- Is publication subject to real partner/community approval and a privacy-risk evaluation?

**Separate review tracks:** GitHub technical/security review; community and independent ethics review (not yet submitted to any person); external evidence review (not yet conducted). Only a qualified, independent third party can consider a future Nobel nomination of an eligible person or active organization, and there is **no nomination** now.

## Public professional references — no affiliation implied

- UNESCO Recommendation on the Ethics of Artificial Intelligence — https://www.unesco.org/en/artificial-intelligence/recommendation-ethics
- ICRC Handbook on Data Protection in Humanitarian Action — https://www.icrc.org/en/data-protection-humanitarian-action-handbook
- UNDP Conflict Sensitivity Indicators for Local and Community Development Programming — https://www.undp.org/myanmar/publications/conflict-sensitivity-indicators-local-and-community-development-programming
- Norwegian Nobel Institute nomination guidance — https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/
