# NXYZ Mouse Mic — Chrome Web Store Listing

## Product name

NXYZ Mouse Mic

## Category

Accessibility

## Summary

Voice and keyboard click guidance for Palantir Foundry with local targeting and confirmation for high-impact actions.

## Single purpose

NXYZ Mouse Mic helps users locate, highlight, describe, and activate visible controls on Palantir Foundry pages they are already authorized to access.

## Detailed description

NXYZ Mouse Mic adds voice and keyboard-driven click guidance to Palantir Foundry.

Use it to:

- label visible clickable controls with numbers;
- find a control by its visible name;
- highlight a matching control and hear its approximate screen location;
- click a named or numbered control;
- scroll the current page;
- use typed commands when speech recognition is unavailable;
- require a second confirmation before selected high-impact controls are activated.

Example commands:

- `show targets`
- `where is Python Compute module`
- `click Python Compute module`
- `click number 12`
- `scroll down`
- `clear labels`
- `confirm click`
- `cancel`

NXYZ Mouse Mic uses local DOM targeting in the browser. It does not require an NXYZ API key or a developer-operated backend service.

Optional voice recognition uses the speech-recognition capability exposed by the user's browser. Typed mode can be used without voice recognition.

NXYZ Mouse Mic does not bypass Palantir permissions, authentication, confirmation dialogs, or authorization controls.

Independent software. Not affiliated with, sponsored by, or endorsed by Palantir Technologies Inc.

## Permission justifications

### activeTab

Used only when the user invokes NXYZ Mouse Mic so it can communicate with the active supported Foundry tab and perform the requested navigation guidance.

### scripting

Used to connect the Mouse Mic content script and stylesheet to the active supported Foundry page if the page was opened before the extension was installed or reloaded.

### Host permission: https://*.palantirfoundry.com/*

The extension is intentionally limited to Palantir Foundry enrollment domains. It does not request `<all_urls>` access.

## Data-use declaration notes

The extension processes visible webpage control labels and user commands to provide its single-purpose click-guidance functionality. Processing occurs in the browser. No developer-operated server receives page content, command history, browsing history, or microphone recordings.

Optional voice recognition may use a speech-recognition service supplied by the user's browser/browser vendor. The extension itself does not send speech to a developer-operated backend.

No advertising, analytics, sale of user data, or unrelated profiling is included.

## Privacy policy URL

https://github.com/sonoxo/gpt-doug-llm/blob/main/tools/nxyz-mouse-mic/PRIVACY.md

## Support URL

https://github.com/sonoxo/gpt-doug-llm/issues

## Homepage / source

https://github.com/sonoxo/gpt-doug-llm/tree/main/tools/nxyz-mouse-mic

## Reviewer test instructions

1. Install the extension package.
2. Open an authorized `https://*.palantirfoundry.com/*` page.
3. Click the NXYZ Mouse Mic toolbar icon.
4. Enter `show targets` and click **Run command**. Visible controls should receive numbered overlays.
5. Enter `where is` followed by the visible name of a control. The matching control should be highlighted and described.
6. Enter `click` followed by the visible name of a normal control to activate it.
7. For a control whose label includes a high-impact term such as `deploy`, `publish`, `approve`, `submit`, or `delete`, NXYZ Mouse Mic should highlight it and request `confirm click` rather than immediately activating it.
8. The extension should not run on `chrome://` pages or unrelated websites.

The extension does not provide Palantir credentials and does not bypass sign-in. Testing on a Foundry page requires access authorized independently by Palantir/the relevant Foundry enrollment administrator.

## Suggested launch visibility

Unlisted first, then Public after confirming the Chrome Web Store build installs correctly.
