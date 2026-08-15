"""Tests for all 10 hackathon agents. All use free resources only."""
import sys, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest

class TestCodeReviewer:
    def test_blocks_pr_with_secret(self):
        from hackathon.agents.code_reviewer import review_pr
        result = review_pr({"number":1,"title":"Add API","body":"hardcoded key","diff":"api_key=sk-test-1234567890abcdef","files":["api.py"],"author":"test"})
        assert result["recommendation"] in ("REQUEST_CHANGES","COMMENT")
        assert result["findings_count"] > 0
    def test_approves_clean_pr(self):
        from hackathon.agents.code_reviewer import review_pr
        result = review_pr({"number":2,"title":"Update docs","body":"Fix typo","diff":"fixed typo in documentation","files":["README.md"],"author":"test"})
        assert result["recommendation"] in ("APPROVE","COMMENT")
    def test_blocks_malicious_pr(self):
        from hackathon.agents.code_reviewer import review_pr
        result = review_pr({"number":3,"title":"Run rm -rf","body":"cleanup","diff":"run rm -rf /","files":["cleanup.sh"],"author":"attacker"})
        assert result["recommendation"] in ("REJECT","REQUEST_CHANGES")

class TestSentinelBot:
    def test_home_scan(self):
        from hackathon.agents.sentinel_bot import run_home_scan
        result = run_home_scan()
        assert "total_findings" in result
        assert "needs_alert" in result
    def test_format_alert_safe(self):
        from hackathon.agents.sentinel_bot import format_alert
        assert "secure" in format_alert({"needs_alert": False}).lower()
    def test_format_alert_threat(self):
        from hackathon.agents.sentinel_bot import format_alert
        assert "ALERT" in format_alert({"needs_alert":True,"alert_reasons":["CRITICAL: malware"],"total_findings":5,"critical_count":1})

class TestDocumentDrafter:
    def test_flags_risky(self):
        from hackathon.agents.document_drafter import review_contract
        result = review_contract("1. Party A shall indemnify Party B. 2. Non-compete for 5 years.")
        assert result["flagged_clauses"] > 0
        assert result["needs_lawyer"] is True
    def test_low_risk(self):
        from hackathon.agents.document_drafter import review_contract
        assert review_contract("1. Agreement between parties. 2. Be nice.")["recommendation"] == "LOW_RISK"

class TestInvoiceNinja:
    def test_generate(self):
        from hackathon.agents.invoice_ninja import generate_invoice
        inv = generate_invoice("Acme", 40, 75, "dev")
        assert inv["amount"] == 3000
    def test_overdue(self):
        from hackathon.agents.invoice_ninja import check_overdue_invoices
        from datetime import datetime, timedelta
        old = (datetime.now() - timedelta(days=15)).isoformat()
        assert check_overdue_invoices([{"client":"A","status":"sent","sent_date":old}])["needs_human"] is True

class TestMeetingSentinel:
    def test_conflict(self):
        from hackathon.agents.meeting_sentinel import check_conflict
        assert check_conflict({"title":"D","start":"2026-09-01T10:00:00","end":"2026-09-01T11:00:00"},[{"title":"S","start":"2026-09-01T10:30:00","end":"2026-09-01T11:00:00"}])["has_conflict"] is True
    def test_no_conflict(self):
        from hackathon.agents.meeting_sentinel import check_conflict
        assert check_conflict({"title":"D","start":"2026-09-01T10:00:00","end":"2026-09-01T11:00:00"},[{"title":"S","start":"2026-09-01T09:00:00","end":"2026-09-01T09:30:00"}])["has_conflict"] is False

class TestHealthTracker:
    def test_reminder(self):
        from hackathon.agents.health_tracker import check_schedule
        assert len(check_schedule([{"name":"Aspirin","next_dose":"2020-01-01T08:00:00"}])["reminders"]) > 0
    def test_no_reminder(self):
        from hackathon.agents.health_tracker import check_schedule
        assert len(check_schedule([{"name":"Aspirin","next_dose":"2030-01-01T08:00:00"}])["reminders"]) == 0

class TestNeighborHelp:
    def test_shortage(self):
        from hackathon.agents.neighbor_help import check_inventory
        r = check_inventory([{"name":"Rice","quantity":2,"threshold":10}])
        assert r["shortages"] == 1
    def test_healthy(self):
        from hackathon.agents.neighbor_help import check_inventory
        assert check_inventory([{"name":"Rice","quantity":100,"threshold":10}])["recommendation"] == "STOCK_HEALTHY"

class TestExpenseSentinel:
    def test_categorize(self):
        from hackathon.agents.expense_sentinel import categorize_expense
        assert categorize_expense("Amazon", 49.99)["category"] == "shopping"
    def test_budget(self):
        from hackathon.agents.expense_sentinel import check_budget
        assert check_budget([{"category":"food","amount":200}],{"food":150})["needs_human"] is True

class TestSchoolCoordinator:
    def test_match(self):
        from hackathon.agents.school_coordinator import match_volunteers
        r = match_volunteers([{"name":"Setup","required_skills":["lifting"]}],[{"name":"Alice","skills":["lifting"],"available":True}])
        assert r["filled"] == 1
    def test_unfilled(self):
        from hackathon.agents.school_coordinator import match_volunteers
        r = match_volunteers([{"name":"Setup","required_skills":["lifting"]}],[{"name":"Bob","skills":["music"],"available":True}])
        assert r["needs_human"] is True

class TestEmergencyMesh:
    def test_check_feeds(self):
        from hackathon.agents.emergency_mesh import check_emergency_feeds
        r = check_emergency_feeds()
        assert "threat_level" in r
    def test_register(self):
        from hackathon.agents.emergency_mesh import register_neighbor
        assert register_neighbor("Test","+15551234567",vulnerable=True)["status"] == "registered"
    def test_no_threats(self):
        from hackathon.agents.emergency_mesh import coordinate_response
        assert coordinate_response([],[])["needs_coordinator_decision"] is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
