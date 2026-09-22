# GPT-NEDU / Novice EDU

GPT-Doug's beginner education division, within the shared ZYRA / XUNIA ecosystem.
Aliases: **Novice GPT**, **GPT Novice**, **Novice EDU**. This is an implemented
learning module, not a claim that a new language model has been trained.

## Open

Browser: [GPT-NEDU](https://xunia.org/learn/nedu/) after this change is merged and
the existing Pages deployment succeeds. The Resource Hub catalogs this page.
The page also works offline by opening `docs/learn/nedu/index.html` directly.

From the repository root:

```bash
bash scripts/doug-max nedu
```

Inside ZYRA chat: `/nedu`. After installing the Python package: `gpt-nedu`.
Menu: **1** learn, **2** demo, **3** references, **q** return; Ctrl+C exits NEDU.
For scripts: `python3 -m gpt_nedu lesson` or `python3 -m gpt_nedu demo`.

## Ecosystem contract

- GPT-Doug owns orchestration; NEDU translates technical ideas into novice lessons.
- ZYRA retains governed execution; NEDU does not delegate executable source text.
- XUNIA provides the shared registry and browser Resource Hub.
- `ecosystem/registry.v4.json` registers NEDU as an internal division and routes
  `novice_education` to it. Existing control roots and runtime visuals are preserved.
- No background agent, model provider, paid API, or cross-repository service is required.

## First learning loop

Observe the comic -> trace where data becomes instructions -> rebuild a small
example -> verify the boundary. The CLI demonstrates real SQLite parameter
binding using only a disposable in-memory database. The browser shows query
construction and a deterministic AI-grader simulation; it does not execute SQL
or call a model. Its grader uses an answer key independent of the name field;
that narrow design is not a general solution to LLM prompt injection.

## Sources and credit

- [Randall Munroe, xkcd #327, Exploits of a Mom](https://xkcd.com/327/): original
  comic reference. Linked, not copied or relicensed as repository artwork.
- The user-supplied AI remix footer credits Philippe Schrettenbrunner;
  [matching repost](https://programmerhumor.io/programming-memes/littlebillyignoreinstructions/).
  Its first publication has not been verified.
- [OWASP SQL injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html):
  parameterized queries keep values separate from SQL syntax.
- [OWASP prompt injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html):
  use layered boundaries, constrained capabilities, validation, and human review.

New explanatory text and code follow the repository license. Source material
retains its own license and authorship. No affiliation with xkcd is implied.
