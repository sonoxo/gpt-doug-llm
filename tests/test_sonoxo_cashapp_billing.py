"""Local-only verification: no Cash App or network calls."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "workers" / "sonoxo_cashapp_billing.py"
SPEC = importlib.util.spec_from_file_location("sonoxo_cashapp_billing", PATH)
billing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(billing)


def test_issue_pending_and_report(tmp_path):
    with billing.connect(tmp_path / "invoices.sqlite") as db:
        result = billing.issue(db, "Real client", "Completed work", "499.00")
        assert result["status"] == "pending"
        assert result["amount_usd"] == "499.00"
        assert result["payment_tag"] == "$Sonoxo"
        assert result["payment_url"] == "https://cash.app/$Sonoxo"
        assert billing.report(db)["pending"]["amount_usd"] == "499.00"


def test_requires_manual_verified_receipt(tmp_path):
    with billing.connect(tmp_path / "invoices.sqlite") as db:
        result = billing.issue(db, "Client", "Work", "100")
        with pytest.raises(ValueError):
            billing.verify_receipt(db, result["invoice_id"], "receipt123", False)
        assert billing.invoice(db, result["invoice_id"])["status"] == "pending"
        verified = billing.verify_receipt(db, result["invoice_id"], "receipt123", True)
        assert verified["status"] == "paid"
        assert billing.report(db)["paid"]["amount_usd"] == "100.00"
        with pytest.raises(ValueError):
            billing.verify_receipt(db, result["invoice_id"], "another123", True)


@pytest.mark.parametrize("amount", ["-1", "0", "NaN", "Infinity", "1.001", "hello"])
def test_rejects_bad_amounts(amount):
    with pytest.raises(ValueError):
        billing.amount_to_cents(amount)


def test_duplicate_reference_denied(tmp_path):
    with billing.connect(tmp_path / "invoices.sqlite") as db:
        first = billing.issue(db, "A", "Work", "10")
        second = billing.issue(db, "B", "Work", "20")
        billing.verify_receipt(db, first["invoice_id"], "unique-reference", True)
        with pytest.raises(ValueError):
            billing.verify_receipt(db, second["invoice_id"], "unique-reference", True)
        assert billing.invoice(db, second["invoice_id"])["status"] == "pending"
