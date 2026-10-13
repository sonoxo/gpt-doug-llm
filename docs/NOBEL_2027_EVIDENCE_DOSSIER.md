# GPT-Doug PeaceLab: 2027 Nobel Peace Prize evidence dossier

**Prepared:** October 13, 2026.  
**Status:** **INTERNAL RESEARCH AND HUMAN-REVIEW DRAFT ONLY**. Not a nomination, not an application, not an award, not an official Nobel affiliation. Do not misrepresent this document as a submission.

## 1. What the Nobel Peace Prize process actually requires

**Official nomination procedure**, rather than a made-up application:
1. **Candidate:** a *living individual* or an *active organization/institution* may be nominated. A code repository or software model, by itself, is not an identified eligible person or active organization.
2. **Nominator:** the submission must come from a person in a category expressly recognized by the Norwegian Nobel Institute. Examples include qualifying national legislators, university professors in designated fields, university rectors, directors of peace research/foreign policy institutes, Nobel Peace Prize laureates, and specified judicial/institutional members. Exact categories must be checked against the [official criteria](https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/criteria-for-nominators).
3. **Timing:** the next regular nomination deadline is **January 31, 2027**. The Institute normally opens next year's online form in mid-October. We have *not* verified that the current form is open or that a qualified nominator has used it.
4. **Decision:** the Norwegian Nobel Committee selects the awardee. A valid nomination is **not** a Nobel endorsement, and a personal application is not considered. The Institute keeps nominee and nominator details confidential for 50 years; do not imply official confirmation.
5. **2026 is closed:** the 2026 Peace Prize was awarded to **Navanethem “Navi” Pillay**, announced October 9, 2026.

**What is NOT an official eligibility requirement:** a public impact score, a 90-day pilot, a specific number of workshops, SHA-256 proofs or a required NGO structure. Those are *our proposed ethical evidence-readiness measures*; they are not invented Nobel statutes. We need credible peace work to make a persuasive case, not merely form-checking.

Official sources:
- https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/
- https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/criteria-for-nominators
- https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/the-nomination-process
- https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/confidentiality
- https://www.nobelpeaceprize.org/laureates/2026

## 2. Evidence verified in this repository

| Claim | What is actually documented | Independent real-world verification |
|---|---|---|
| Software exists | Public code in sonoxo/gpt-doug-llm; PeaceLab core, pilot, JSON-LD ontology and CI tests | Software presence can be inspected; no field effects follow automatically |
| Privacy and safety intent | Local deny-first ontology, human control gates and software privacy checks | No independent human safeguarding approval confirmed |
| PeaceLab human sessions | Synthetic 90-day protocol and dialogue facilitator kit | **None confirmed** |
| Eligible candidate | GPT-Doug is a software project; no specifically qualified living individual or active legal organization designated here | **Unknown** |
| Community partners | A proposal to solicit voluntary, legitimate community involvement | **None independently established** |
| Real participants | The test scenarios are synthetic | **0 verified by our records** |
| Reduced harm / peaceful resolution | No controlled or independent field evaluation | **No outcome established** |
| Qualified nominator | Category list documented; no independent nominator documented | **None confirmed** |
| Nobel nomination | No valid submission performed by this project/tool | **No submission evidence recorded** |
| Nobel award | Official 2026 laureate is Navi Pillay | **GPT-Doug not a laureate** |

**Important:** GitHub Actions can prove that test code passes. A certificate digest authenticates neither a recipient of aid nor a cause-and-effect peace benefit. No such inference is permitted.

## 3. Concrete, ethical way to establish real peace impact

### A. Establish legitimate authority
- Designate a living person or active organization, with verifiable legal identity and responsible human leadership.
- Ask a credible local peacebuilding or community-mediation partner **whether** such a low-risk education pilot is wanted, before attempting recruitment.
- Obtain independent conflict-sensitivity, safeguarding and privacy reviews, including safe withdrawal, retaliation risk and procedures to stop.

### B. Co-design an intervention that can help
- Human-led voluntary listening and peaceful disagreement education; never AI-governed negotiation in dangerous active disputes.
- Consent in an appropriate language, independent facilitators, accessible participation, no targeting, biometrics or private raw disclosures.
- Gather only appropriate, privacy-preserving *aggregate* evidence. Small counts can re-identify people even if they are not named.

### C. Independent assessment
- Collaborate with an evaluator to preregister measures, baseline and follow-up, sample selection, comparators where ethical, adverse event reporting and causal limitations.
- Publish positive, null **and negative** findings only with privacy and community approval.
- Get independent evidence of any benefit, not a count of how many lines of code ran.

### D. Independent nomination, only after merit exists
- Identify a qualified **willing** independent nominator; verify the person is in an official category **as of submission**. Do not list private names in public repository issues.
- A genuine nominator decides independently whether there is enough evidence of meritorious peace work; they must submit through the official process.
- The Nobel Committee decides whether an award is warranted. **No engineering or lobbying process can guarantee a Nobel Peace Prize**.

**Timing:** The January 31, 2027 cycle is the next procedural window, but building credible and safe independent field evidence may legitimately take much longer. Do not invent evidence or sacrifice safety to meet it.

## 4. Fact-checked, reusable candidate narrative (DRAFT ONLY)

> GPT-Doug PeaceLab is an open-source *prototype* designed to support nonviolent, human-facilitated dialogue and to organize evidence without exposing participant identities. Its demonstrated accomplishment is software and safety-control implementation—not verified peacebuilding outcomes. It proposes a community-governed education pilot requiring independent safeguards and evaluation. At the time of this dossier, no eligible individual or active organization has been designated as a candidate; no qualified nominator, actual field intervention, independent peace impact, or Nobel nomination is confirmed.

This is **not** a finished nominator's motivation statement. A qualified third party must evaluate genuine later achievements and decide independently what to write.

## 5. Reviewer gates / honest completion criteria

| Evidence task | Status October 13, 2026 | Required independent sign-off |
|---|---|---|
| Identify eligible candidate | **Missing** | Proof of living person / active organization |
| Document responsible organization | **Missing** | Independently checked registration or responsibility |
| Community partner and consent | **Missing** | Genuine community consent and ability to veto |
| Independent do-no-harm review | **Missing** | Qualified safeguarding/privacy review |
| Authorized, safely completed pilot | **Missing** | Human facilitators + program director |
| Independent impact evaluation | **Missing** | Unaffiliated evaluation with harms and limitations |
| Nomination from eligible party | **Not submitted by project** | Qualified nominator, by official deadline |
| Committee selection | **Outside anyone's control** | Sole discretion of Norwegian Nobel Committee |

The [90-day pilot protocol](PEACELAB_90_DAY_PILOT.md) and [independent engineering review questions](PEACELAB_ENGINEERING_REVIEW_REQUEST.md) are planning resources only.

## 6. Terminal proof (free and offline)

Run from the repository root:

~~~bash
bash scripts/doug-max peace-lab nobel-demo > /tmp/gpt-doug-nobel-2027.json
bash scripts/doug-max peace-lab nobel-check /tmp/gpt-doug-nobel-2027.json
bash scripts/doug-max peace-lab nobel-brief /tmp/gpt-doug-nobel-2027.json
bash scripts/doug-max peace-lab nobel-html /tmp/gpt-doug-nobel-2027.json > /tmp/gpt-doug-nobel-2027.html
~~~

On macOS, open the HTML with \`open /tmp/gpt-doug-nobel-2027.html\`. To record new evidence *privately*, use \`peace-lab nobel-init\` with an unused file path **outside Git**. Mark any new URL as supplied but unchecked, and never commit a nominator's private details or beneficiary records.

The output is a **replayable internal readiness checklist**, not a certification or valid Nobel nomination.
