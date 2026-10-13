"""Sonoxo public portfolio fleet: deterministic offline and fail-closed tests."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from sonoxo_fleet import core
from sonoxo_fleet.cli import PRS, SNAPSHOT, load_prs, load_snapshot, main


class PortfolioFleetTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_snapshot(SNAPSHOT)
        self.prs = load_prs(PRS)

    def test_verified_public_snapshot_and_privacy(self):
        assert self.snapshot["repository_count"] == 206
        assert len({x["full_name"].casefold() for x in self.snapshot["repositories"]}) == 206
        assert all(x["visibility"] == "public" for x in self.snapshot["repositories"])
        assert all(x["full_name"].startswith("sonoxo/") for x in self.snapshot["repositories"])
        assert self.snapshot["private_repositories_discovered"] is False
        assert self.snapshot["operations"]["auto_merge"] is False

    def test_public_pr_refs_are_filtered(self):
        assert len(self.prs) == 51
        public_repos = {r["full_name"].casefold() for r in self.snapshot["repositories"]}
        assert all("sonoxo/" + pr["url"].split("/")[4].casefold() in public_repos for pr in self.prs)

    def test_review_plan_has_206_entries_without_writes(self):
        result = core.plan_upgrade(self.snapshot, open_pull_requests=self.prs)
        assert result["repositories_indexed"] == 206
        assert result["observed_open_prs"] == 51
        assert result["core_repositories"] >= 9
        assert result["fork_unknown"] == 206
        assert result["default_policy"]["auto_merge"] is False
        assert len(result["repositories"]) == 206
        assert all(not r["force_push"] and not r["auto_merge"] for r in result["repositories"])

    def test_duplicate_repo_rejected(self):
        item = self.snapshot["repositories"][0]
        with self.assertRaisesRegex(core.AuditError, "duplicate"):
            core.snapshot_from_repos([item, item], observed_at="2026-10-13", source="test")

    def test_private_and_unrelated_owner_rejected(self):
        item = dict(self.snapshot["repositories"][0])
        item["visibility"] = "private"
        with self.assertRaises(core.AuditError):
            core.snapshot_from_repos([item], observed_at="2026-10-13", source="test")
        item["visibility"] = "public"
        item["full_name"] = "other-owner/a"
        with self.assertRaises(core.AuditError):
            core.snapshot_from_repos([item], observed_at="2026-10-13", source="test")

    def test_bad_snapshot_integrity_rejected(self):
        item = json.loads(json.dumps(self.snapshot))
        item["repositories"][0]["default_branch"] = "unexpected"
        with self.assertRaisesRegex(core.AuditError, "digest mismatch"):
            core.validate_snapshot(item)

    def test_invalid_pr_link_rejected(self):
        with self.assertRaisesRegex(core.AuditError, "invalid public GitHub PR"):
            core.plan_upgrade(self.snapshot, open_pull_requests=[
                {"url": "https://evil.example.com/pr/1", "title": "Injected"}
            ])

    def test_branch_names_preserved(self):
        result = core.plan_upgrade(self.snapshot, open_pull_requests=self.prs)
        assert "main" in result["branches"]
        assert "master" in result["branches"]
        assert "develop" in result["branches"]
        assert "Main" in result["branches"]

    def test_mock_live_public_inventory_uses_only_github_user_api(self):
        def fake_repo(i):
            return {
                "full_name": f"sonoxo/repo-{i}", "default_branch": "main",
                "owner": {"login": "sonoxo"}, "private": False,
                "archived": False, "fork": False, "size": 100,
            }
        called = []
        def fake_fetch(url):
            called.append(url)
            return [fake_repo(i) for i in range(100)] if "page=1" in url else [fake_repo(100)]
        snap = core.public_repo_inventory(fetch_json=fake_fetch)
        assert snap["repository_count"] == 101
        assert all(x.startswith("https://api.github.com/users/sonoxo/repos?") for x in called)
        assert len(called) == 2
        assert all(x["fork"] is False for x in snap["repositories"])

    def test_live_inventory_rejects_wrong_owner(self):
        def wrong(_):
            return [{"full_name": "other/repo", "default_branch": "main",
                     "owner": {"login": "other"}, "private": False}]
        with self.assertRaisesRegex(core.AuditError, "wrong owner"):
            core.public_repo_inventory(fetch_json=wrong)

    def test_dashboard_escapes_untrusted_pr_titles(self):
        from sonoxo_fleet.viewer import render_dashboard
        malicious = [{"url": "https://github.com/sonoxo/gpt-doug-llm/pull/1",
                      "title": "</script><img src=x onerror=alert(1)>"}]
        report = core.plan_upgrade(self.snapshot, open_pull_requests=malicious)
        html = render_dashboard(report)
        assert "</script><img" not in html
        assert "\\u003c/script\\u003e" in html
        assert "PUBLIC METADATA ONLY" in html

    def test_offline_cli_generates_real_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            result = main(["audit", "--output", td])
            assert result == 0
            folder = Path(td)
            assert (folder / "portfolio.html").is_file()
            assert (folder / "upgrade-plan.json").is_file()
            assert (folder / "summary.json").is_file()
            assert (folder / "snapshot.json").is_file()
            plan = json.loads((folder / "upgrade-plan.json").read_text())
            assert plan["repositories_indexed"] == 206
            assert plan["observed_open_prs"] == 51
            assert main(["audit", "--output", td]) == 2
            assert main(["audit", "--output", td, "--force"]) == 0

    def test_status_declares_no_mutation(self):
        from contextlib import redirect_stdout
        from io import StringIO
        stream = StringIO()
        with redirect_stdout(stream):
            assert main(["status"]) == 0
        obj = json.loads(stream.getvalue())
        assert obj["default_network_actions"] == 0
        assert obj["remote_repo_writes"] is False
        assert obj["automatic_merges"] is False
        assert obj["private_repositories_discovered"] is False


if __name__ == "__main__":
    unittest.main()
