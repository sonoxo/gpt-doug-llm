# Sonoxo revenue workflow — Cash App billing

This module extends the existing draft-only revenue swarm with **local invoicing**, not autonomous movement of money. The only configured payment destination is the requested **$Sonoxo** Cash App tag. Verify the tag belongs to the intended recipient before sharing requests.

## Start free

Run the existing swarm on grounded, authorized prospect records:

```bash
python3 workers/revenue_swarm.py --input prospects.json --workers 2
```

Review the proposal and outreach drafts, contact prospective buyers only through permitted and appropriate channels, negotiate an actual service agreement, then issue a legitimate invoice for agreed work.

```bash
python3 workers/sonoxo_cashapp_billing.py issue --client "Client Name" --description "Agreed automation service" --amount 499.00
python3 workers/sonoxo_cashapp_billing.py report
```

The invoice record includes the destination link `https://cash.app/$Sonoxo` and an invoice ID. The payer approves the transfer in their own Cash App interface. **Nothing here charges customers, sends requests, accesses Cash App, or redirects deposits.** No deposit is guaranteed.

After independently confirming funds landed in the recipient's own Cash App activity, manually reconcile:

```bash
python3 workers/sonoxo_cashapp_billing.py verify-paid SX-REPLACE_ME --reference REAL_VERIFIED_TRANSACTION_ID --confirmed-in-cashapp
```

Only use a reference obtained from a real transaction; the flag is an operator attestation, not technical verification. Never claim a receipt is verified purely because an agent or buyer said so. Local SQLite records are sensitive accounting data; restrict filesystem access, back up appropriately, and do not commit the database to Git. Confirm tax, invoice, Cash App account-type, processor terms, transaction limits, and identity obligations before operating commercially. Do not treat a personal Cash App tag as a universal merchant processor.

## Controls

- Exact payment destination: `$Sonoxo`, no dynamic payee overrides.
- No credentials, Cash App API scraping, trading, or autonomous disbursements.
- Draft-only lead generation and approval-gated outreach remain unchanged.
- Explicit reconciliation plus unique reference required before marking an invoice paid.
- No false revenue metrics from unverified prospective sales.
- No background process or continuous job is launched by these scripts.

Tests:

```bash
pytest -q tests/test_sonoxo_cashapp_billing.py tests/test_revenue_swarm.py
```
