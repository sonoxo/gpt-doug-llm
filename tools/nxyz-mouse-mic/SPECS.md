# NXYZ Mouse Mic — Shipping Specification

**Release:** 1.0.2  
**Package type:** Chrome/Chromium browser extension  
**Manifest:** Manifest V3  
**Primary category:** Accessibility  
**Source:** `tools/nxyz-mouse-mic`

## Product purpose

NXYZ Mouse Mic provides local click guidance for authorized Palantir Foundry pages. It scans visible interactive DOM controls, labels or highlights targets, accepts typed commands, can use browser speech recognition when available, speaks guidance through browser speech synthesis, and requires confirmation before clicking controls that appear high-impact.

## Runtime scope

| Item | Shipping value |
| --- | --- |
| Supported browser | Google Chrome / Chromium browsers with Manifest V3 support |
| Allowed site scope | `https://*.palantirfoundry.com/*` |
| Generic web access | Not requested |
| Background service worker | Not required |
| External backend | Not required |
| Paid API key | Not required |
| Remote code | Not used by the extension package |
| Persistent user-data storage | Not requested |

## Permissions

The production manifest requests only:

- `activeTab` — access to the currently active supported page when the user invokes the extension.
- `scripting` — inject the packaged NXYZ Mouse Mic content script/CSS when necessary.
- Host permission `https://*.palantirfoundry.com/*` — restricts operation to Palantir Foundry tenant pages.

The extension does **not** request `<all_urls>` or the Chrome `storage` permission.

## Core capabilities

- Visible interactive-element discovery.
- Numbered target overlays with `show targets`.
- Fuzzy label matching for controls.
- Typed command entry from the extension popup.
- Browser-provided speech recognition when available.
- Browser speech synthesis for spoken guidance.
- `where is <label>` / `find <label>` guidance.
- `click <label>` and `click number <n>` interaction.
- Smooth page scrolling commands.
- High-impact click confirmation gate.
- Plain speech defaults to guidance rather than automatic clicking.

## Safety behavior

Controls whose accessible text indicates potentially significant actions are not immediately clicked. Current guarded terms include actions such as delete, remove, destroy, terminate, revoke, grant, permission, submit, purchase, pay, deploy, publish, approve, merge, send, invite, create account, and reset.

A guarded target is highlighted and held as pending until the user explicitly says `confirm click`; `cancel`, `never mind`, or `stop` clears the pending action.

This extension does not bypass Palantir authentication, authorization, approvals, or tenant policy.

## Privacy and data handling

- DOM analysis and target matching execute in the browser page context.
- No developer-operated NXYZ backend is required for normal operation.
- No API key is collected by the extension.
- No Chrome `storage` permission is requested.
- No analytics SDK is included in the shipping source.
- Typed commands are handled locally by the extension.
- Voice recognition relies on the browser Web Speech implementation when available; the browser/vendor may process speech according to its own implementation and policies.

See [`PRIVACY.md`](./PRIVACY.md) for the public privacy policy.

## Icon specification

The shipping package includes PNG extension icons under [`icons/`](./icons/):

| File | Dimensions | Manifest use |
| --- | ---: | --- |
| `icons/icon16.png` | 16×16 | Toolbar/small UI |
| `icons/icon48.png` | 48×48 | Extension management UI |
| `icons/icon128.png` | 128×128 | Chrome extension/store icon source |

All icon paths are declared in `manifest.json` for both the extension icon set and action icon set.

## Package contents required for upload

The Chrome Web Store ZIP must place these files/directories at the ZIP root:

```text
manifest.json
content.js
overlay.css
popup.html
popup.js
icons/
  icon16.png
  icon48.png
  icon128.png
```

Documentation files may be excluded from the production upload ZIP as long as the runtime files above remain intact.

## Store metadata source-of-truth

- Store listing: [`STORE-LISTING.md`](./STORE-LISTING.md)
- Privacy policy: [`PRIVACY.md`](./PRIVACY.md)
- Publish procedure: [`PUBLISH-CHECKLIST.md`](./PUBLISH-CHECKLIST.md)
- Icon inventory: [`icons/README.md`](./icons/README.md)

## Release acceptance criteria

A release is ship-ready when all of the following are true:

1. `manifest.json` parses as valid Manifest V3 JSON.
2. Manifest version matches the release version.
3. All manifest-referenced runtime files exist in the upload ZIP.
4. 16×16, 48×48, and 128×128 PNG icons exist and load correctly.
5. `content.js` and `popup.js` parse without JavaScript syntax errors.
6. Extension activates only on the declared Foundry host scope.
7. `show targets` labels visible interactive controls.
8. `where is <control>` highlights a matching control without clicking it.
9. A normal `click <control>` action functions on an authorized Foundry page.
10. A guarded/high-impact target requires `confirm click`.
11. The extension does not run on unrelated sites or `chrome://` pages.
12. Chrome Web Store listing, privacy declarations, artwork, and reviewer instructions are completed in the publisher dashboard.

## Release status

**Repository package target: READY FOR CHROME WEB STORE SUBMISSION after publisher-dashboard upload and review.**
