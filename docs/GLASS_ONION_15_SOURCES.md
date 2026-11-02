# GLASS ONION — fifteen source slots

**Source:** https://www.youtube.com/watch?v=rmkXyB6JBX8&t=166s

The user-provided transcript names fifteen cybersecurity tools. This branch records **15 reference-only slots and 16 public repositories** (Empire and Starkiller share position 1). It does not clone, run, install, or merge exploit/credential-theft/post-exploitation code. An upstream code merge is **not** implied by an inventory record.

**Free and open-source rule:** Rank 10 replaces closed-source Burp Suite with OWASP ZAP; rank 2 replaces commercial Cobalt Strike with Atomic Red Team. These substitutes are not functionality-equivalent. Wireshark's GitHub is a read-only mirror; Exploit Database's historical GitHub repository is archived, and GitLab hosts the official current repo.

**Evidence rule:** The video narrator's assertions about FBI monitoring, prosecutions and specific breaches remain **unverified claims**, not findings. Repo existence and canonical locations were separately checked.

## Integration architecture

SHADOW GLASS (default-deny) → GLASS ONION (source evidence) → THE BLACK HOUSE (explainable findings) → GPT-DOUG / ZYRA / XUNIA (governed consumers).

Every selected source includes: original video rank, canonical URL, category, human-review requirement, license-review requirement, denied execution, denied automatic clone, denied credential collection, denied target scanning and denied payload deployment. There are no paid APIs, paid services or runtime external dependencies.

## Run locally

```bash
python3 scripts/glass_onion_15_catalog.py --validate --report
python3 scripts/glass_onion_15_catalog.py --ontology-out /tmp/glass-onion-15-ontology.json
python3 -m unittest discover -s tests -p test_glass_onion_15_catalog.py -v
```

An optional `--probe` reads **public repository metadata only** via free rate-limited GitHub/GitLab endpoints; it never clones or executes upstream code. Open `safety-shield/glass-onion/source-dashboard.html` locally in a browser for a no-server visual catalog.

**Licenses and revisions are intentionally unpinned until inspected.** Any future import must pin an immutable commit, verify license obligations, analyze provenance and dependencies, and obtain explicit human approval.

## Verification sources

- https://portswigger.net/support/burp-suite-software-faqs
- https://github.com/zaproxy/zaproxy
- https://github.com/redcanaryco/atomic-red-team
- https://www.wireshark.org/develop
- https://github.com/offensive-security/exploitdb
- https://gitlab.com/exploit-database/exploitdb
