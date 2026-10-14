import unittest

from scripts.sonoxo_fleet_upgrader import (
    classify_repository,
    detect_ecosystems,
    list_owner_repositories,
    render_markdown,
    scan_repositories,
)


class FakeAPI:
    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def get_json(self, path):
        self.calls.append(path)
        if path not in self.replies:
            raise AssertionError(f"Unexpected API route: {path}")
        value = self.replies[path]
        if isinstance(value, Exception):
            raise value
        return value


def repo(name, *, fork=False, archived=False, owner="sonoxo"):
    return {
        "full_name": f"{owner}/{name}",
        "name": name,
        "owner": {"login": owner},
        "default_branch": "main",
        "fork": fork,
        "archived": archived,
        "html_url": f"https://github.com/{owner}/{name}",
    }


def entries(*names):
    return [{"name": name} for name in names]


class FleetUpgraderTests(unittest.TestCase):
    def test_detects_root_manifests_and_ci(self):
        actual = detect_ecosystems(
            {"package.json", "pyproject.toml", "Dockerfile", ".github"},
            {"workflows"},
        )
        self.assertEqual(actual, ["npm", "pip", "docker", "github-actions"])

    def test_fork_requires_upstream_review_even_if_dependabot_missing(self):
        result = classify_repository(
            repo("upstream", fork=True),
            {"package.json", ".github"},
            {"workflows"},
        )
        self.assertEqual(result["recommendation"], "upstream-sync-first")
        self.assertEqual(result["ecosystems"], ["npm", "github-actions"])

    def test_archived_repo_is_skipped(self):
        result = classify_repository(repo("archived", archived=True), {"package.json"}, set())
        self.assertEqual(result["recommendation"], "archived-skip")

    def test_missing_dependabot_in_owned_code_is_identified(self):
        result = classify_repository(repo("app"), {"package.json", ".github"}, {"workflows"})
        self.assertFalse(result["dependabot"])
        self.assertEqual(result["recommendation"], "enable-dependabot")

    def test_existing_dependabot_needs_review_not_duplication(self):
        result = classify_repository(
            repo("app"), {"package.json", ".github"}, {"dependabot.yml", "workflows"}
        )
        self.assertEqual(result["recommendation"], "review-update-prs")
        self.assertTrue(result["dependabot"])

    def test_repo_without_manifests_is_not_guessed(self):
        result = classify_repository(repo("docs"), {"README.md"}, None)
        self.assertEqual(result["recommendation"], "manual-stack-review")
        self.assertEqual(result["ecosystems"], [])

    def test_scan_error_is_not_misclassified_as_no_manifests(self):
        result = classify_repository(repo("app"), set(), None, read_error="HTTP 403")
        self.assertEqual(result["recommendation"], "inspection-error")
        self.assertIn("HTTP 403", result["error"])

    def test_lists_all_pages_and_excludes_non_owner_results(self):
        first = [repo(f"project-{i}") for i in range(99)] + [repo("elsewhere", owner="other")]
        api = FakeAPI({
            "/users/sonoxo/repos?per_page=100&page=1&type=owner": first,
            "/users/sonoxo/repos?per_page=100&page=2&type=owner": [repo("last")],
        })
        result = list_owner_repositories(api, "sonoxo")
        self.assertEqual(len(result), 100)
        self.assertEqual(result[-1]["name"], "last")
        self.assertEqual(len(api.calls), 2)

    def test_scanner_handles_repository_without_github_directory(self):
        api = FakeAPI({
            "/repos/sonoxo/app/contents": entries("package.json", "README.md"),
        })
        result = scan_repositories(api, [repo("app")])
        self.assertEqual(result[0]["recommendation"], "enable-dependabot")
        self.assertEqual(api.calls, ["/repos/sonoxo/app/contents"])

    def test_scanner_handles_directory_error_per_repository(self):
        api = FakeAPI({
            "/repos/sonoxo/bad/contents": ValueError("HTTP 403"),
            "/repos/sonoxo/good/contents": entries("pyproject.toml"),
        })
        result = scan_repositories(api, [repo("bad"), repo("good")])
        self.assertEqual(result[0]["recommendation"], "inspection-error")
        self.assertEqual(result[1]["recommendation"], "enable-dependabot")

    def test_markdown_counts_unique_repos_and_never_claims_upgrades_applied(self):
        records = [
            classify_repository(repo("a"), {"package.json"}, None),
            classify_repository(repo("b", fork=True), {"Dockerfile"}, None),
        ]
        output = render_markdown(records, "sonoxo")
        self.assertIn("2 repositories inspected", output)
        self.assertIn("1 upstream-sync-first", output)
        self.assertIn("1 enable-dependabot", output)
        self.assertIn("read-only", output.lower())
        self.assertIn("https://github.com/sonoxo/a", output)


if __name__ == "__main__":
    unittest.main()
