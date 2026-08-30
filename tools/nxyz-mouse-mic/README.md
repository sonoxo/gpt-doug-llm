# NXYZ Mouse Mic

Free browser click-guidance for Palantir Foundry.

NXYZ Mouse Mic scans the currently visible page for clickable controls, labels them, highlights the best match for a spoken or typed request, describes where the control is on screen, and can click it when requested.

## Cost

**No paid API is required. No API key is required. No subscription is required by this extension.**

- DOM scanning, fuzzy target matching, highlighting, click selection, safety checks, and typed commands run inside the browser extension.
- Speech synthesis uses the browser's built-in speech support.
- Voice recognition uses the browser Web Speech implementation when available. Chrome may implement recognition with a browser/cloud speech service; the extension does not call a paid API itself.
- If you do not want voice recognition, use the popup text box. Typed mode does not need speech recognition.

## Install in Chrome

1. Clone or download `sonoxo/gpt-doug-llm`.
2. Open `chrome://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select this folder:

   `tools/nxyz-mouse-mic`

6. Open your authorized Palantir Foundry enrollment.
7. A purple microphone button appears in the bottom-right corner.
8. Click it and allow microphone access if Chrome asks.

## Commands

- `show targets` — number all visible clickable controls.
- `where is Python Compute module` — highlight it and speak its screen location.
- `click Python Compute module` — click the best matching control.
- `click number 12` — click a numbered target after `show targets`.
- `scroll down`
- `scroll up`
- `clear labels`
- `help`
- `cancel`

Plain speech defaults to **guidance**, not automatic clicking. Example: saying `Python Compute module` highlights and describes the target instead of clicking it.

## High-impact click protection

Controls containing words such as `delete`, `deploy`, `publish`, `approve`, `submit`, `permission`, `pay`, or `revoke` are never immediately clicked. NXYZ highlights the target and asks for `confirm click` first.

This does not replace Palantir authorization or approval controls.

## Foundry workflow example

On the Foundry **Developer Tools → Code Templates** page:

1. Say `where is Python Compute module`.
2. NXYZ highlights the Python Compute module template and tells you where it is.
3. Say `click Python Compute module`.
4. Continue with the Foundry setup wizard.

## Files

- `manifest.json` — Chrome extension manifest.
- `content.js` — target discovery, fuzzy matching, voice commands, safety confirmation.
- `overlay.css` — microphone, status panel, target numbers, highlights.
- `popup.html` / `popup.js` — typed-command fallback and microphone trigger.

## Scope

The manifest currently activates only on:

`https://*.palantirfoundry.com/*`

No generic `<all_urls>` permission is requested.

## License

This project is part of `gpt-doug-llm` and follows the repository license.
