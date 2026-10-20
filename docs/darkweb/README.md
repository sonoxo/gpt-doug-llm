# XUNIA GLASS ONION — Cyber Intelligence Research Lab

**Public launch path, after merge and Pages success:** https://xunia.org/darkweb/

An **original**, no-account XUNIA interface with all **21 tool references** shown in the source graphic. Product names identify outside services and are not copies of private code, proprietary data, search indexes, Tor Browser, leak stores, Telegram bots, or vendor trademarks. XUNIA does not claim those backends are connected.

## Working in-browser modules
- Searchable, categorized 21-reference catalog, with honest native/integration/reference/restricted labels.
- Ahmia and OCCRP Aleph public-search launchers, redirecting to the real providers.
- Free HIBP Pwned Passwords range API; SHA-1 computed locally and only the first five hexadecimal hash characters sent over HTTPS. Do not check production passwords on this or other unfamiliar sites.
- Free, source-attributed CISA Known Exploited Vulnerabilities catalog. Fetch failures are explicit.
- Browser-only notes/evidence vault: add, search, import JSON/CSV and export JSON; 500-record cap. Browser localStorage is **not encrypted** and must not be used for restricted information or secrets.
- OpenPGP browser station with ECC key generation, encryption, decryption, cleartext signing and signature verification using pinned OpenPGP.js version 5.11.3 from unpkg. Third-party library availability is necessary; an audited installed client is safer for high-value secrets.
- Verified official-source directory and privacy guidance.

## CLI: bounded authorized crawler
Requires Python 3.10+ and **written authorization or ownership** of the exact HTTPS host.

```sh
python3 scripts/xunia_authorized_crawl.py --base-url https://example.org --allow-host example.org --max-pages 10 --authorized > research.jsonl
```

The crawler is designed to fail closed on localhost/internal/hidden services, IP-literal hosts, non-global DNS, redirects off the exact hostname, oversized responses, and missing or unreadable robots.txt (HTTP 404 is interpreted as no robot rules). Same-origin HTML links only; default 2-second delay; maximum 50 pages. It is a bounded audit prototype, not a Tor crawler. **DNS rebinding at socket-connect time is not completely eliminated by pre-request DNS checks; use only trusted approved hosts and isolated environments.**

## Tests
```sh
node --test tests/xunia_glass_onion.test.mjs
python3 -m py_compile scripts/xunia_authorized_crawl.py
```

GitHub Actions workflow `.github/workflows/glass-onion.yml` executes these on push and pull requests.

## Truth boundary
GitHub Pages hosts static files; it does not operate a Tor relay, search engine, breach-data subscription, onion mirror, or secure evidence server. No credentials, private records, or arbitrary websites should be automatically collected. No external commercial service is portrayed as installed. Feature branch builds are not publicly deployed until merged and the Pages job passes. This exhibit follows XUNIA Museum inclusion and provenance guidelines.
