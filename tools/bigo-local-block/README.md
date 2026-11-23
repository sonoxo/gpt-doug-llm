# Glass Onion — BIGO Local Block

A minimal, free, opt-in **Chrome/Chromium Manifest V3 extension** that blocks
`bigo.tv` and its subdomains through Chrome’s local
`declarativeNetRequest` ruleset. It does not contact or disrupt BIGO's
servers, collect user data, or read browsing history.

## Install on your Mac (Chrome)

1. Download or clone `sonoxo/gpt-doug-llm`.
2. Open `chrome://extensions` in Chrome.
3. Switch **Developer mode** on.
4. Select **Load unpacked** and choose the folder
   `tools/bigo-local-block` (the folder containing `manifest.json`).
5. The block starts **enabled**. In the toolbar, open **Glass Onion — BIGO
   Local Block** to disable or re-enable it. Refresh any already-open BIGO tabs
   to apply the change.

## Verified scope

- Blocks Chrome requests whose domain is `bigo.tv` or one of its subdomains,
  for the resource types listed in `rules.json`.
- Does **not** block the BIGO iOS/Android app, other domains, unrelated CDN
  hosts, or other users' devices.
- No file access, clipboard access, network sending, host permissions, or
  user tracking is requested. It requires the `declarativeNetRequest`
  permission only.
- Chrome extension uninstall or disabling its ruleset immediately reverses
  the change. No operating-system files are modified.

You can add other **verified** domains you own/control blocking on with
separate local rules, but do not infer subdomains or block shared CDN
infrastructure without verification.

## Validate

```bash
node --test tests/bigo_local_block.test.mjs
node --check tools/bigo-local-block/popup.js
```
