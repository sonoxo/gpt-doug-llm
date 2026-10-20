# GPT-Doug / XUNIA Museum — GitHub Cloud Library

## Scope

- Public source-code research library, not executable integration or a security endorsement.
- The pinned source list is `data/github-cloud-library-targets.json`: 85 clone operations across Global, AI/LLM, PQC, and Sonoxo; 82 unique repository names in the original verified run.
- Repositories are cloned only from HTTPS GitHub URLs into isolated GitHub-hosted runner storage.
- Third-party repositories are not installed, built, or executed, and are never automatically merged into GPT-Doug-LLM.
- The cloud job preserves the Git object databases, including tracked blobs and HEAD hashes, while omitting redundant working-tree copies.
- A separate fresh runner must restore each checkout **offline**, with network lazy fetching disabled. Only fully successful cloning, caching, and offline restore can publish the JSON catalog.

## Evidence

- [Pinned targets](../data/github-cloud-library-targets.json)
- [Cloud workflow](../.github/workflows/cloud-top-github-library.yml)
- [Cloner](../scripts/cloud_repo_cloner.py)
- [Fail-closed catalog builder](../scripts/cloud_repo_catalog.py)
- [Recovery regression tests](../tests/test_cloud_repo_cloner.py)
- [GitHub Actions history](https://github.com/sonoxo/gpt-doug-llm/actions/workflows/cloud-top-github-library.yml)
- After the catalog job succeeds: [Verified restoration catalog](../data/github-cloud-library-catalog.json).

## Storage and free-tier boundaries

GitHub-hosted standard Linux runners for public repositories are free. The repository's Actions cache is limited by GitHub policy to 10 GB by default. These cache entries are **temporary**: unused cache entries can be evicted after seven days or sooner due to capacity pressure. This design enforces a 1,700 MiB uncompressed threshold per cache shard, and never requests a paid runner or an increased storage quota.

The **permanent** artifact is the small catalog of repository URLs and pinned commit SHAs, committed to the GitHub branch. This is sufficient to reproduce shallow source checkouts from their original public hosts later, assuming the source commits are still available. The complete byte-for-byte Git cache is not guaranteed permanent.

## Validation contract

`python3 -m unittest discover -s tests -p test_cloud_repo_cloner.py -v`

A successful run must report all 85 clone operations, independent offline recovery of all 85, complete cache hits, and a committed catalog. Partial successes, unavailable blobs, unexpected SHAs, missing shards, or cache misses are failures and must not be declared complete.

## XUNIA integration

This entry is the Museum archive for the repository research library. It **does not** assert the inventory was deployed to xunia.org, that the cloned tools were integrated, or that Level 5 post-quantum operational readiness was certified. The separate local-only commit `964499d` remains a distinct recovery issue.
