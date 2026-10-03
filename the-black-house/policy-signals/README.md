# Black House Policy Signals

This directory stores dated, provenance-aware public policy signals for RVIA and GPT-DOUG-LLM. A policy signal is evidence about a stated position or an enacted authority; those categories must remain distinct.

## Signal classes

Use `PUBLIC_STATEMENT` for speeches, posts, interviews, campaign or administration messaging, and other statements that express a position. Use `EXECUTIVE_ORDER`, `LAW`, or `REGULATION` only when the underlying authoritative primary source has been independently verified. Other binding authorities should use a similarly explicit type and preserve their primary-source provenance.

## Authority boundary

A `PUBLIC_STATEMENT` does not change Black House execution authority, does not waive ZYRA approval or security requirements, and does not create external authorization. Political rhetoric, policy preference, enacted policy, legal authority, and ecosystem operating controls must remain separately typed.

## Provenance contract

Every signal should record source type, observation date, verification state, and the distinction between what the source directly says and what an analyst infers. Speaker claims are stored as claims unless independently verified. Any conclusion about legal, regulatory, contractual, clearance, credential, or operational effect requires separate authoritative evidence.

## RVIA use

RVIA may use policy signals to answer questions about public positions, compare stated policy with enacted policy, and provide historical context. It must surface uncertainty and provenance and must not convert a public statement into a permission, credential, or execution grant.
