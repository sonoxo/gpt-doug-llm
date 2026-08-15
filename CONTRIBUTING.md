# Contributing to GPT Doug LLM

## Quick Start

```bash
git clone https://github.com/sonoxo/gpt-doug-llm.git
cd gpt-doug-llm
python3 -m pytest tests/ -v
```

All 105 tests must pass before submitting a PR.

## Code Style

- Python 3.9+ (3.11/3.12 preferred)
- No external dependencies for core modules (stdlib only)
- Type hints encouraged
- Every security-relevant change must include or update a test
- No secrets, credentials, or personal paths in code

## Security Contributions

Security improvements are welcome. When adding or modifying Zyra patterns:

1. Add the attack vector to `tests/test_zyra_guard.py` or `tests/test_golden_shield.py`
2. Verify the test fails without your fix
3. Verify the test passes with your fix
4. Verify no existing tests break
5. Add legitimate (non-attacking) test cases to check for false positives

## Adding Knowledge Base Entries

Add JSONL files to `workers/knowledge/`. Each entry must have:

```json
{
  "id": "unique-id",
  "topic": "category",
  "attribution": "source",
  "summary": "factual summary (not verbatim source material)",
  "keywords": ["searchable", "terms"]
}
```

All knowledge must be from public sources, properly attributed, and not classified or sensitive information.

## Pull Request Process

1. Fork the repo
2. Create a branch: `git checkout -b fix/my-improvement`
3. Run tests: `python3 -m pytest tests/ -v`
4. Commit with clear message
5. Open a PR describing what changed and why

## License

By contributing, you agree your contributions are licensed under MIT.
