# Sonoxo AI: zero-upfront-cost service-business launch kit

This is a static, dependency-free service site. No hosting fees are required for local preview. Public deployment using a free static hosting provider depends on its eligibility and terms.

## Preview
```bash
python3 -m http.server 8080 --directory sonoxo-agency
```
Open http://localhost:8080.

## Before publishing
1. Establish who legally owns and operates the business; comply with registration, license, tax and consumer-protection requirements relevant to your jurisdiction. Zero software cost is not a guarantee of zero business compliance costs.
2. Set a verified business inquiry address by replacing the empty `recipient` value in `index.html`. Until then, the form only offers to copy the inquiry locally; no lead is transmitted.
3. Confirm that Cash App $Sonoxo is owned by the authorized legal recipient, and that the account type and payment use comply with Cash App policies.
4. Finalize scope, contracts, privacy/data-processing terms, quotes, and payment acceptance processes. Never request payment on an unsupported promise.
5. Publish the static site on an authorized domain or eligible free hosting provider. Publishing is not done automatically by this PR.
6. For actual prospects, use the existing workers/revenue_swarm.py with verified prospect data; all outreach stays draft-only and review-gated.
7. For actual contracted clients, use workers/sonoxo_cashapp_billing.py on the corresponding branch/after merge to create invoices, and independently verify receipts.

## $100k target (illustrative, not guaranteed)
20 completed $5,000 engagements = $100,000 gross invoiced. No clients, balances or contracts are represented by this calculation. The business should earn payments through authorized commercial services. No automated access to payment balances or transfer initiation is provided.
