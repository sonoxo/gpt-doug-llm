# XUNIA Open Web Atlas — Free Local Public-Web Mirror

This is **not a copy of the entire Internet**. It is a bounded, authorization-gated text archive and link-graph viewer for publicly accessible sites you own or have explicit permission to crawl.

## Web visualization

Published route after Pages verification: https://xunia.org/open-web-atlas/

The browser can show a documentation-only XUNIA route map, import a local archive JSON, search captured text, draw captured internal links, inspect SHA-256 evidence, view outbound domain references, and export its archive. The browser does not crawl arbitrary sites. No API keys, paid models, or CDN libraries.

## Local collection

Requires only Python 3.10+ and the existing repository scripts.

```bash
python3 scripts/xunia_web_mirror.py --base-url https://xunia.org/ --allow-host xunia.org --authorized --max-pages 20 --max-depth 2 --delay 2 --out xunia-open-web-snapshot.json
```

Use `--authorized` **only** for a host you own or have permission to archive. The output is a text-only JSON archive, not executable HTML, scripts, media, private content, or a complete mirror of dynamic applications.

Then open xunia.org/open-web-atlas/ and choose **Import crawl snapshot** to select the JSON file. The app reads that file locally in your browser. It does not upload it.

## Controls and limitations

- Exact HTTPS host allowlist; same-host links only.
- Public IP DNS validation and restricted redirects reused from `xunia_authorized_crawl.py`.
- robots.txt gates (error or unavailable robots blocks except HTTP 404).
- No login, private/admin/account paths, binary assets, URL queries or fragments.
- Page limit up to 50, depth 0–3, minimum 1-second delay, 512 KB maximum per document, 12K extracted-text characters per page.
- Meta robots noindex prevents archiving; nofollow prevents discovering linked pages.
- The output includes text provenance hashes and bounded outside-domain references, but never fetches those outside domains.
- **Known limit**: DNS rebinding between validation and connection is not completely removed by the underlying crawler. Use only trusted approved domains in isolated environments.
- **Known limit**: HTTP X-Robots-Tag response headers are not inspected by the base crawler; do not archive sites where additional header-level restrictions or site terms prohibit copying.
- Pages may contain copyrighted material; distribution or republication requires rights. The local archive is not automatically published to GitHub.

## Verification

```bash
python3 -m unittest discover -s tests -p test_xunia_web_mirror.py -v
python3 -m unittest discover -s tests -p test_xunia_authorized_crawl.py -v
node --check docs/open-web-atlas/app.js
```

The application follows RFC 9309, with a more conservative fail-closed policy where uncertainty remains.