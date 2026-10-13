# GPT-Doug PeaceLab — engineering & independent community review request

**Submission type:** GitHub engineering proposal and independent ethics-review preparation. **Not a Nobel nomination, humanitarian outcome assessment, deployed AI mediator or authorization for fieldwork.**

**Related work:** PR #356 and Issue #357 in sonoxo/gpt-doug-llm.

## Delivered for inspection

- Standard-library-only module in peace_impact/pilot.py, building a repeatable 90-day pilot model.
- Strict schema, eight documentary gates, five risks with stop triggers, separate external truth boundary, no automatic authority grants.
- Aggregate-only descriptive outcomes, automatic refusal of small disclosive cohorts, malformed evidence references and fabricated synthetic measurements.
- SHA-256 integrity/replay checks for a synthetic design snapshot. Integrity is not external attestation.
- Reviewer-ready Markdown brief plus static zero-JavaScript HTML preview; offline and cost-free to run.
- Human responsibilities and the full protocol in docs/PEACELAB_90_DAY_PILOT.md.
- CLI commands and independent Python 3.11/3.12 regression workflows.

## Decisions formally requested from human reviewers

| Decision | Required expertise | Current state |
|---|---|---|
| Merge code for a non-operational research tool? | Independent software/security maintainer | REQUESTED, NOT APPROVED |
| Does the community actually want and need this program? | Genuine accountable community leadership | UNKNOWN |
| Is a low-risk setting, safe consent, and incident response credible? | Qualified local safeguarding and privacy experts | NOT REVIEWED |
| Are the suggested indicators and evaluation design valid? | Independent peacebuilding evaluator | NOT REVIEWED |
| Authorize fieldwork after all local reviews? | Responsible legal program operator and any applicable oversight | **NOT AUTHORIZED** |
| Consider any future prize nomination? | Eligible independent nominator and the Nobel Committee | **NOT SUBMITTED** |

## Reviewer reproduction commands

~~~sh
python3 -m unittest discover -s tests -p 'test_peace*.py' -v
bash -n scripts/doug-max
bash scripts/doug-max peace-lab pilot-demo > /tmp/pilot-review.json
bash scripts/doug-max peace-lab pilot-verify /tmp/pilot-review.json
bash scripts/doug-max peace-lab pilot-brief /tmp/pilot-review.json
bash scripts/doug-max peace-lab pilot-preview /tmp/pilot-review.json > /tmp/pilot-review.html
~~~

## Explicit review objections to check

1. Does any output incorrectly equate self-reported documentary links with an actual authorized or independently approved community pilot?
2. Do any string or URL fields admit personal identities, secrets, unwanted location data or unsafe document links?
3. Does the tool falsely imply a causal peace benefit from pre-post participant ratings or remove negative outcomes?
4. Is there a realistic stop procedure if participation could trigger retaliation, coercion, threats or disclosure?
5. Are the phase gates independently operable and understandable to non-engineering reviewers?
6. Are all public-facing examples clearly synthetic, and is fieldwork restricted until real-world informed consent and appropriate reviews?
7. Are the repository-wide CI/security failures disclosed separately from the dedicated PeaceLab checks?

## Reality check

No verified real-world peace outcomes, executed pilot, humanitarian partner, approved independent evaluation, independent nominator or Nobel nomination. GitHub submission does not create any of these. Requests for community and ethics review must go to actual accountable partners only through separately authorized human outreach.
