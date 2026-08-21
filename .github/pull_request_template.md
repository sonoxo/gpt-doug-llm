## What changed?

Describe the change in concrete terms.

## Why?

What problem does this solve for ZYRA/GPT-DOUG-LLM?

## Validation

Check what you actually ran:

- [ ] `python zyra_agent.py --self-test`
- [ ] `python zyra_laser.py`
- [ ] Relevant pytest suite
- [ ] Ruff / lint checks
- [ ] Manual ZYRA terminal verification
- [ ] Not applicable (explain below)

Validation notes:

```text
paste concise sanitized results here
```

## Agentic-runtime impact

- [ ] No new autonomous capability
- [ ] Adds/changes an Agent Core capability
- [ ] Changes mission budgets or tool permissions
- [ ] Changes checkpoint/rollback behavior
- [ ] Changes LASER/policy behavior
- [ ] Changes external side-effect boundaries

If any capability boundary changes, explain exactly what becomes newly possible and how it is constrained.

## Security / privacy

- [ ] No secrets, tokens, credentials, private keys, or personal data are included.
- [ ] New external network behavior is documented.
- [ ] Failure behavior is bounded and reviewable.
- [ ] Autonomous writes remain reversible or the exception is explicitly documented.

## Rollback plan

How can this change be reverted if it causes a regression?

## Screenshots / logs

Optional. Sanitize all output before attaching it.
