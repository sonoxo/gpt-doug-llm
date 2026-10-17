# Sonoxo / XUNIA — four opportunity bid-readiness packets (2026-10-16)

**Status: INTERNAL PREPARATION ONLY. No bids, questions, applications, emails, or payment instructions have been sent.**

This folder converts the most recent four prospect leads into actionable procurement artifacts. It does **not** assert eligibility, customer references, licenses, UN vendor registration, operational product status, or paid contracts. Values in the tracker are genuinely unknown until documentary evidence is reviewed.

| ID | Buyer | Offer | Published date/time | Confidence | First hard blocker |
|---|---|---|---|---|---|
| ITC-UGA-2200347473 | ITC Uganda | Hub digital media RFQ | 4 Nov 2026, 00:00 (timezone unspecified in UNGM) | Official notice; all four annexes listed, downloads blocked | Annex A ToR and Annex B evaluation spreadsheet inaccessible |
| UNDP-SAU-00160 | UNDP Saudi Arabia | Creative, content and translation RFP | 1 Nov 2026, 10:00 GMT-4 | Official notice; negotiation documents not inspected | UNGM Basic + Quantum account + technical/commercial annexes |
| FAO-LKA-138380 | FAO Sri Lanka | Independent monitoring of grant beneficiaries | 28 Oct 2026, 16:00 GMT+5:30 | Official notice; generic bidders guide displayed only | Domain references, impartiality and exact ToR |
| SYMCA-097745-2026 | South Yorkshire Mayoral Combined Authority | E-bike service and software platform | 16 Nov 2026, noon UK (secondary record) | Public tender index only; official site inaccessible | Governing documents + production subscription/fleet capability |

## Source links

- ITC Uganda official notice: https://www.ungm.org/Public/Notice/318412 . Required attachments: RFQ cover letter; Annex A Terms of Reference; Annex B Technical Evaluation (.xlsx); Annex C Conditions of Contract. Attempted public annex downloads returned HTTP 403. Do **not** guess requirements or upload a quotation without reading them.
- UNDP Saudi official notice: https://www.ungm.org/Public/Notice/316534 . Bids must go through UNDP Quantum only; document language English; UNGM Basic registration; questions through portal. Pre-bid conference was rescheduled to October 11 (already past). The full tender annexes are linked from UNDP but were not inspected.
- FAO Sri Lanka official notice: https://www.ungm.org/Public/Notice/318068 . Only a generic bidder-instructions PDF was listed; no detailed technical ToR was visible in public notice.
- South Yorkshire primary notice (not retrievable in this review): https://www.find-tender.service.gov.uk/Notice/097745-2026 ; secondary record: https://tendertracker.co.uk/contracts/ocds-h6vhtk-07891b . Estimated GBP 300,000 is indicative **not guaranteed**.

## Documents

- [ITC Uganda response draft](ITC_UGANDA.md)
- [UNDP Saudi Arabia response draft](UNDP_SAUDI.md)
- [FAO Sri Lanka conditional monitoring approach](FAO_SRI_LANKA.md)
- [SYMCA platform compliance and build assessment](SYMCA_EBIKES.md)
- [Evidence and owner-action checklist](EVIDENCE_CHECKLIST.md)
- [Machine-readable requirements](requirements.json)

## Automated compliance gate

\`\`\`bash
python3 tools/sonoxo_bid_gate.py
python3 tools/sonoxo_bid_gate.py --id UNDP-SAU-00160
python3 -m unittest tests.test_sonoxo_bid_gate -v
\`\`\`

The gate prints *blocked_do_not_submit* until **every** blocking item has authoritative requirement confirmation and actual supplier evidence. A hypothetical "ready_for_manual_bid_review" means only that a human can inspect the packet; it does not mean procurement eligibility or buyer acceptance. An optional evidence overlay may point to LOCAL documents and should not be committed.

Example locally stored evidence overlay (not real evidence):

\`\`\`json
{
  "UNDP-SAU-00160": {
    "quantum-account": {
      "bidder_status": "verified",
      "evidence_ref": "local-private-vendor-registration-proof"
    }
  }
}
\`\`\`

Evidence from a genuine issuer or project must be inspected by an authorized person. Faked identifiers, self-issued client references, fabricated financials, forged accreditation and invented team qualifications are disallowed.

## Submission rules and money

- No automated emailing, portal clicking, donation solicitation, invoicing, bank-account edits or financial transfers.
- Cash App $Sonoxo is a requested **future recipient preference** only. It is not a replacement for buyer-designated bank-transfer and tax/KYC forms; never put it into a UN tender without a buyer-approved payout mechanism.
- This repository's [documented product states](../../docs/PRODUCTS.md) distinguish implemented software from proposed, experimental or tenant-dependent integrations. Repos and demos are **not** substitute evidence of delivered external client contracts.
- Do not commit personal IDs, business tax numbers, confidential bids, client references without permission, bank details, portal credentials, pricing negotiations, or unpublished tender documents.
- Save finalized buyer-issued annexes and legal evidence locally in a restricted working folder; all external communications require explicit review and authorization.

**Next gate:** Obtain inaccessible Annex A/B (ITC), negotiation documents (UNDP), detailed ToR (FAO), and the full primary tender (SYMCA), then fill the pricing schedules based on actual labor and partner quotes. The owner/authorized business officer must supply factual entity, staffing and project evidence before any of these can be considered submission-ready.
